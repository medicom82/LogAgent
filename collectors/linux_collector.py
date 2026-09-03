"""Linux Log Collector Module"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, List
import paramiko
from kafka import KafkaProducer
import json

logger = logging.getLogger(__name__)


class LinuxLogCollector:
    """Collector for Linux system logs (Apache, MySQL, Audit, ISPConfig)"""
    
    def __init__(self, server_id: str, hostname: str, username: str, 
                 private_key_path: str = None, password: str = None):
        """
        Initialize Linux log collector
        
        Args:
            server_id: Unique server identifier
            hostname: Server hostname/IP
            username: SSH username
            private_key_path: Path to SSH private key
            password: SSH password (if key not available)
        """
        self.server_id = server_id
        self.hostname = hostname
        self.username = username
        self.private_key_path = private_key_path
        self.password = password
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # SSH client
        self.ssh = None
        self._connect_ssh()
    
    def _connect_ssh(self):
        """Establish SSH connection to server"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.private_key_path:
                self.ssh.connect(
                    self.hostname,
                    username=self.username,
                    key_filename=self.private_key_path,
                    timeout=30
                )
            else:
                self.ssh.connect(
                    self.hostname,
                    username=self.username,
                    password=self.password,
                    timeout=30
                )
            
            logger.info(f"SSH connection established to {self.hostname}")
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.hostname}: {e}")
            raise
    
    def collect_apache_logs(self, log_paths: List[str] = None) -> int:
        """
        Collect Apache access and error logs
        
        Args:
            log_paths: List of Apache log paths to collect
            
        Returns:
            Number of logs collected
        """
        if not log_paths:
            log_paths = [
                '/var/log/apache2/access.log',
                '/var/log/apache2/error.log',
                '/var/log/httpd/access_log',
                '/var/log/httpd/error_log'
            ]
        
        logs_collected = 0
        
        for log_path in log_paths:
            try:
                # Get last 1000 lines
                cmd = f"tail -1000 {log_path} 2>/dev/null"
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
                lines = stdout.readlines()
                
                for line in lines:
                    log_entry = self._parse_apache_log(line.strip())
                    if log_entry:
                        self.producer.send('log-stream', log_entry)
                        logs_collected += 1
                
                logger.info(f"Collected {logs_collected} Apache logs from {log_path}")
                
            except Exception as e:
                logger.error(f"Error collecting Apache logs from {log_path}: {e}")
        
        return logs_collected
    
    def collect_mysql_logs(self, log_paths: List[str] = None) -> int:
        """
        Collect MySQL logs (General Query Log, Error Log, Slow Query Log)
        
        Args:
            log_paths: List of MySQL log paths
            
        Returns:
            Number of logs collected
        """
        if not log_paths:
            log_paths = [
                '/var/log/mysql/mysql.log',
                '/var/log/mysql/error.log',
                '/var/log/mysql/slow.log',
                '/var/log/mariadb/mariadb.log'
            ]
        
        logs_collected = 0
        
        for log_path in log_paths:
            try:
                cmd = f"tail -500 {log_path} 2>/dev/null"
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
                lines = stdout.readlines()
                
                for line in lines:
                    log_entry = self._parse_mysql_log(line.strip())
                    if log_entry:
                        self.producer.send('log-stream', log_entry)
                        logs_collected += 1
                
                logger.info(f"Collected {logs_collected} MySQL logs from {log_path}")
                
            except Exception as e:
                logger.error(f"Error collecting MySQL logs from {log_path}: {e}")
        
        return logs_collected
    
    def collect_audit_logs(self) -> int:
        """
        Collect Linux audit logs
        
        Returns:
            Number of logs collected
        """
        logs_collected = 0
        
        try:
            # Using auditctl to get recent audit logs
            cmd = "tail -500 /var/log/audit/audit.log 2>/dev/null"
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            lines = stdout.readlines()
            
            for line in lines:
                log_entry = self._parse_audit_log(line.strip())
                if log_entry:
                    self.producer.send('log-stream', log_entry)
                    logs_collected += 1
            
            logger.info(f"Collected {logs_collected} audit logs")
            
        except Exception as e:
            logger.error(f"Error collecting audit logs: {e}")
        
        return logs_collected
    
    def collect_ispconfig_logs(self) -> int:
        """
        Collect ISPConfig virtual host logs
        
        Returns:
            Number of logs collected
        """
        logs_collected = 0
        
        try:
            # Get list of ISPConfig virtual hosts
            cmd = "ls /var/log/ispconfig/ 2>/dev/null | grep -E '.*access.log'"
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            vhosts = stdout.readlines()
            
            for vhost_log in vhosts:
                vhost_log = vhost_log.strip()
                if not vhost_log:
                    continue
                
                log_path = f"/var/log/ispconfig/{vhost_log}"
                cmd = f"tail -500 {log_path} 2>/dev/null"
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
                lines = stdout.readlines()
                
                for line in lines:
                    log_entry = self._parse_apache_log(line.strip())
                    if log_entry:
                        log_entry['ispconfig_vhost'] = vhost_log.replace('_access.log', '')
                        self.producer.send('log-stream', log_entry)
                        logs_collected += 1
            
            logger.info(f"Collected {logs_collected} ISPConfig virtual host logs")
            
        except Exception as e:
            logger.error(f"Error collecting ISPConfig logs: {e}")
        
        return logs_collected
    
    def collect_system_logs(self) -> int:
        """
        Collect system logs (syslog, auth.log)
        
        Returns:
            Number of logs collected
        """
        logs_collected = 0
        
        try:
            for log_path in ['/var/log/syslog', '/var/log/auth.log']:
                cmd = f"tail -500 {log_path} 2>/dev/null"
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
                lines = stdout.readlines()
                
                log_type = 'syslog' if 'syslog' in log_path else 'auth'
                
                for line in lines:
                    log_entry = self._parse_system_log(line.strip(), log_type)
                    if log_entry:
                        self.producer.send('log-stream', log_entry)
                        logs_collected += 1
            
            logger.info(f"Collected {logs_collected} system logs")
            
        except Exception as e:
            logger.error(f"Error collecting system logs: {e}")
        
        return logs_collected
    
    def _parse_apache_log(self, line: str) -> Dict:
        """Parse Apache access log line"""
        try:
            # Apache Combined Log Format
            pattern = r'(\S+) \S+ (\S+) \[([^\]]+)\] "(\S+) (\S+) (\S+)" (\d+) (\S+) "([^"]*)" "([^"]*)"'
            match = re.match(pattern, line)
            
            if match:
                source_ip, user, timestamp, method, path, protocol, status_code, bytes_sent, referer, user_agent = match.groups()
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'server_id': self.server_id,
                    'log_type': 'apache',
                    'source_ip': source_ip,
                    'user': user if user != '-' else None,
                    'method': method,
                    'path': path,
                    'status_code': int(status_code),
                    'bytes_sent': int(bytes_sent) if bytes_sent != '-' else 0,
                    'referer': referer if referer != '-' else None,
                    'user_agent': user_agent,
                    'raw_log_line': line
                }
        except Exception as e:
            logger.debug(f"Error parsing Apache log: {e}")
        
        return None
    
    def _parse_mysql_log(self, line: str) -> Dict:
        """Parse MySQL log line"""
        try:
            # MySQL general query log format
            pattern = r'(\d+)-(\d+)-(\d+)\s+(\d+):(\d+):(\d+)\s+(\d+)\s+Query\s+(.+)'
            match = re.match(pattern, line)
            
            if match:
                year, month, day, hour, minute, second, thread_id, query = match.groups()
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'server_id': self.server_id,
                    'log_type': 'mysql',
                    'query': query,
                    'thread_id': int(thread_id),
                    'raw_log_line': line
                }
        except Exception as e:
            logger.debug(f"Error parsing MySQL log: {e}")
        
        return None
    
    def _parse_audit_log(self, line: str) -> Dict:
        """Parse Linux audit log line"""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'server_id': self.server_id,
                'log_type': 'audit',
                'raw_log_line': line
            }
        except Exception as e:
            logger.debug(f"Error parsing audit log: {e}")
        
        return None
    
    def _parse_system_log(self, line: str, log_type: str) -> Dict:
        """Parse system log line (syslog, auth.log)"""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'server_id': self.server_id,
                'log_type': log_type,
                'raw_log_line': line
            }
        except Exception as e:
            logger.debug(f"Error parsing system log: {e}")
        
        return None
    
    def close(self):
        """Close SSH connection and Kafka producer"""
        if self.ssh:
            self.ssh.close()
            logger.info("SSH connection closed")
        
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")


def create_linux_collector(server_id: str, hostname: str, username: str,
                          private_key_path: str = None, password: str = None) -> LinuxLogCollector:
    """Factory function to create Linux log collector"""
    return LinuxLogCollector(server_id, hostname, username, private_key_path, password)
