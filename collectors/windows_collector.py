"""Windows Log Collector Module"""

import os
import logging
from datetime import datetime
from typing import Dict, List
import json
from kafka import KafkaProducer

logger = logging.getLogger(__name__)


class WindowsLogCollector:
    """Collector for Windows system logs (IIS, Event Logs, Application Logs)"""
    
    def __init__(self, server_id: str, hostname: str, username: str = None, password: str = None):
        """
        Initialize Windows log collector
        
        Args:
            server_id: Unique server identifier
            hostname: Windows server hostname/IP
            username: Windows username (optional for local collection)
            password: Windows password (optional for local collection)
        """
        self.server_id = server_id
        self.hostname = hostname
        self.username = username
        self.password = password
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Try to import Windows-specific modules
        try:
            import win32evtlog
            import win32con
            import wmi
            self.win32evtlog = win32evtlog
            self.win32con = win32con
            self.wmi = wmi
            self.windows_available = True
        except ImportError:
            logger.warning("Windows modules not available - running on non-Windows system")
            self.windows_available = False
    
    def collect_iis_logs(self, iis_log_paths: List[str] = None) -> int:
        """
        Collect IIS (Internet Information Services) logs
        
        Args:
            iis_log_paths: List of IIS log file paths
            
        Returns:
            Number of logs collected
        """
        if not iis_log_paths:
            iis_log_paths = [
                "C:\\inetpub\\logs\\LogFiles\\W3SVC1\\",
                "C:\\inetpub\\logs\\LogFiles\\W3SVC2\\"
            ]
        
        logs_collected = 0
        
        try:
            for log_dir in iis_log_paths:
                if os.path.exists(log_dir):
                    # Get latest log file
                    log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')], reverse=True)
                    
                    for log_file in log_files[:5]:  # Process last 5 log files
                        log_path = os.path.join(log_dir, log_file)
                        try:
                            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()
                                
                                for line in lines[-1000:]:  # Last 1000 lines
                                    log_entry = self._parse_iis_log(line.strip())
                                    if log_entry:
                                        self.producer.send('log-stream', log_entry)
                                        logs_collected += 1
                        
                        except Exception as e:
                            logger.error(f"Error reading IIS log {log_path}: {e}")
            
            logger.info(f"Collected {logs_collected} IIS logs")
        
        except Exception as e:
            logger.error(f"Error collecting IIS logs: {e}")
        
        return logs_collected
    
    def collect_event_logs(self, event_log_names: List[str] = None) -> int:
        """
        Collect Windows Event Logs (Security, System, Application)
        
        Args:
            event_log_names: List of event log names to collect
            
        Returns:
            Number of logs collected
        """
        if not self.windows_available:
            logger.warning("Windows Event Log collection requires Windows platform")
            return 0
        
        if not event_log_names:
            event_log_names = ['Security', 'System', 'Application']
        
        logs_collected = 0
        
        try:
            for log_name in event_log_names:
                try:
                    # Open the event log
                    handle = self.win32evtlog.OpenEventLog(self.hostname, log_name)
                    
                    # Read events (get last 500)
                    flags = self.win32evtlog.EVENTLOG_BACKWARDS_READ | self.win32evtlog.EVENTLOG_SEQUENTIAL_READ
                    events = self.win32evtlog.ReadEventLog(handle, flags, 0)
                    
                    for event in events[:500]:
                        log_entry = self._parse_event_log(event, log_name)
                        if log_entry:
                            self.producer.send('log-stream', log_entry)
                            logs_collected += 1
                    
                    self.win32evtlog.CloseEventLog(handle)
                    logger.info(f"Collected {logs_collected} events from {log_name} log")
                
                except Exception as e:
                    logger.error(f"Error reading {log_name} event log: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting event logs: {e}")
        
        return logs_collected
    
    def collect_security_logs(self) -> int:
        """
        Collect Windows Security Event logs (authentication, access control)
        
        Returns:
            Number of logs collected
        """
        if not self.windows_available:
            logger.warning("Windows Security Log collection requires Windows platform")
            return 0
        
        logs_collected = 0
        
        try:
            handle = self.win32evtlog.OpenEventLog(self.hostname, 'Security')
            flags = self.win32evtlog.EVENTLOG_BACKWARDS_READ | self.win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = self.win32evtlog.ReadEventLog(handle, flags, 0)
            
            for event in events[:500]:
                # Focus on security-relevant events
                event_id = event[6]  # EventID
                
                # Interesting event IDs: 4624 (login), 4625 (failed login), 4634 (logout), etc.
                if event_id in [4624, 4625, 4634, 4663, 4688, 4720, 4722]:
                    log_entry = self._parse_event_log(event, 'Security')
                    if log_entry:
                        log_entry['security_relevant'] = True
                        self.producer.send('log-stream', log_entry)
                        logs_collected += 1
            
            self.win32evtlog.CloseEventLog(handle)
            logger.info(f"Collected {logs_collected} security-relevant events")
        
        except Exception as e:
            logger.error(f"Error collecting security logs: {e}")
        
        return logs_collected
    
    def collect_application_logs(self) -> int:
        """
        Collect Windows Application Event logs
        
        Returns:
            Number of logs collected
        """
        if not self.windows_available:
            logger.warning("Windows Application Log collection requires Windows platform")
            return 0
        
        logs_collected = 0
        
        try:
            handle = self.win32evtlog.OpenEventLog(self.hostname, 'Application')
            flags = self.win32evtlog.EVENTLOG_BACKWARDS_READ | self.win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = self.win32evtlog.ReadEventLog(handle, flags, 0)
            
            for event in events[:500]:
                log_entry = self._parse_event_log(event, 'Application')
                if log_entry:
                    self.producer.send('log-stream', log_entry)
                    logs_collected += 1
            
            self.win32evtlog.CloseEventLog(handle)
            logger.info(f"Collected {logs_collected} application logs")
        
        except Exception as e:
            logger.error(f"Error collecting application logs: {e}")
        
        return logs_collected
    
    def collect_performance_logs(self) -> int:
        """
        Collect Windows Performance data
        
        Returns:
            Number of logs collected
        """
        if not self.windows_available:
            logger.warning("Windows Performance collection requires Windows platform")
            return 0
        
        logs_collected = 0
        
        try:
            c = self.wmi.WMI()
            
            # Collect CPU usage
            for proc in c.Win32_PerfFormattedData_PerfProc_Process(name="*"):
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'server_id': self.server_id,
                    'log_type': 'windows_performance',
                    'metric_type': 'cpu',
                    'process_name': proc.Name,
                    'cpu_percent': proc.PercentProcessorTime,
                    'raw_log_line': str(proc)
                }
                self.producer.send('log-stream', log_entry)
                logs_collected += 1
            
            # Collect memory usage
            for mem in c.Win32_PerfFormattedData_PerfOS_Memory():
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'server_id': self.server_id,
                    'log_type': 'windows_performance',
                    'metric_type': 'memory',
                    'available_mbytes': mem.AvailableMBytes,
                    'pages_per_sec': mem.PagesPerSec,
                    'raw_log_line': str(mem)
                }
                self.producer.send('log-stream', log_entry)
                logs_collected += 1
            
            logger.info(f"Collected {logs_collected} performance metrics")
        
        except Exception as e:
            logger.error(f"Error collecting performance logs: {e}")
        
        return logs_collected
    
    def _parse_iis_log(self, line: str) -> Dict:
        """Parse IIS log line"""
        try:
            # Skip comment lines and empty lines
            if line.startswith('#') or not line.strip():
                return None
            
            # IIS log format (typically CSV)
            fields = line.split()
            if len(fields) >= 15:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'server_id': self.server_id,
                    'log_type': 'windows_iis',
                    'date': fields[0],
                    'time': fields[1],
                    'server_ip': fields[2] if len(fields) > 2 else None,
                    'method': fields[3] if len(fields) > 3 else None,
                    'path': fields[4] if len(fields) > 4 else None,
                    'query_string': fields[5] if len(fields) > 5 else None,
                    'source_ip': fields[8] if len(fields) > 8 else None,
                    'user_agent': fields[9] if len(fields) > 9 else None,
                    'status_code': int(fields[10]) if len(fields) > 10 and fields[10].isdigit() else None,
                    'bytes_sent': int(fields[11]) if len(fields) > 11 and fields[11].isdigit() else 0,
                    'raw_log_line': line
                }
        except Exception as e:
            logger.debug(f"Error parsing IIS log: {e}")
        
        return None
    
    def _parse_event_log(self, event, log_name: str) -> Dict:
        """Parse Windows Event Log entry"""
        try:
            event_id = event[6]
            time_generated = event[12]
            source = event[10]
            event_type = event[7]
            
            # Map event types
            type_map = {
                1: 'ERROR',
                2: 'WARNING',
                3: 'INFORMATION',
                4: 'AUDIT_SUCCESS',
                5: 'AUDIT_FAILURE'
            }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'server_id': self.server_id,
                'log_type': 'windows_event',
                'event_log_name': log_name,
                'event_id': event_id,
                'event_type': type_map.get(event_type, str(event_type)),
                'source': source,
                'time_generated': str(time_generated),
                'raw_log_line': str(event)
            }
        except Exception as e:
            logger.debug(f"Error parsing event log: {e}")
        
        return None
    
    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")


def create_windows_collector(server_id: str, hostname: str, 
                           username: str = None, password: str = None) -> WindowsLogCollector:
    """Factory function to create Windows log collector"""
    return WindowsLogCollector(server_id, hostname, username, password)
