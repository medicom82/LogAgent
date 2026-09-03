"""Kafka Producer and Consumer for LogAgent"""

import os
import json
import logging
from typing import Dict, Callable, Optional
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class LogAgentProducer:
    """Kafka Producer for sending logs"""
    
    def __init__(self, bootstrap_servers: str = None):
        """
        Initialize Kafka Producer
        
        Args:
            bootstrap_servers: Kafka bootstrap servers (comma-separated)
        """
        self.bootstrap_servers = bootstrap_servers or os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.producer = None
        self._init_producer()
    
    def _init_producer(self):
        """Initialize Kafka producer connection"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                batch_size=32768,
                linger_ms=10,
                compression_type='snappy'
            )
            logger.info(f"Kafka Producer initialized: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            raise
    
    def send_log(self, topic: str, log_entry: Dict) -> bool:
        """
        Send a single log entry to Kafka
        
        Args:
            topic: Kafka topic name
            log_entry: Log data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            future = self.producer.send(topic, value=log_entry)
            record_metadata = future.get(timeout=10)
            
            logger.debug(f"Log sent to topic '{topic}' partition {record_metadata.partition} offset {record_metadata.offset}")
            return True
            
        except KafkaError as e:
            logger.error(f"Error sending log to Kafka: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    def send_batch(self, topic: str, log_entries: list) -> int:
        """
        Send multiple log entries to Kafka
        
        Args:
            topic: Kafka topic name
            log_entries: List of log dictionaries
            
        Returns:
            Number of successfully sent logs
        """
        sent_count = 0
        
        for log_entry in log_entries:
            try:
                self.producer.send(topic, value=log_entry)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending batch log: {e}")
        
        # Ensure all messages are sent
        self.producer.flush(timeout=30)
        logger.info(f"Sent {sent_count}/{len(log_entries)} logs to topic '{topic}'")
        
        return sent_count
    
    def close(self):
        """Close producer connection"""
        if self.producer:
            self.producer.close(timeout=30)
            logger.info("Kafka Producer closed")


class LogAgentConsumer:
    """Kafka Consumer for processing logs"""
    
    def __init__(self, topic: str, group_id: str = None, bootstrap_servers: str = None):
        """
        Initialize Kafka Consumer
        
        Args:
            topic: Kafka topic name to consume from
            group_id: Consumer group ID
            bootstrap_servers: Kafka bootstrap servers
        """
        self.topic = topic
        self.group_id = group_id or f"logagent-{topic}"
        self.bootstrap_servers = bootstrap_servers or os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.consumer = None
        self._init_consumer()
    
    def _init_consumer(self):
        """Initialize Kafka consumer connection"""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers.split(','),
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                max_poll_records=500,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            logger.info(f"Kafka Consumer initialized for topic '{self.topic}' with group '{self.group_id}'")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Consumer: {e}")
            raise
    
    def consume_batch(self, timeout_ms: int = 1000, max_records: int = None) -> list:
        """
        Consume a batch of messages
        
        Args:
            timeout_ms: Timeout in milliseconds
            max_records: Maximum records to fetch
            
        Returns:
            List of consumed log entries
        """
        try:
            messages = self.consumer.poll(timeout_ms=timeout_ms, max_records=max_records)
            
            logs = []
            for topic_partition, records in messages.items():
                for record in records:
                    logs.append(record.value)
            
            if logs:
                logger.debug(f"Consumed {len(logs)} messages from '{self.topic}'")
            
            return logs
            
        except Exception as e:
            logger.error(f"Error consuming from Kafka: {e}")
            return []
    
    def process_stream(self, callback: Callable, batch_size: int = 100):
        """
        Process log stream with callback function
        
        Args:
            callback: Function to process each log entry
            batch_size: Batch size for processing
        """
        batch = []
        
        try:
            logger.info(f"Starting to process stream from topic '{self.topic}'")
            
            for message in self.consumer:
                log_entry = message.value
                batch.append(log_entry)
                
                if len(batch) >= batch_size:
                    try:
                        callback(batch)
                    except Exception as e:
                        logger.error(f"Error in callback processing: {e}")
                    
                    batch = []
            
            # Process remaining batch
            if batch:
                try:
                    callback(batch)
                except Exception as e:
                    logger.error(f"Error processing final batch: {e}")
        
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
    
    def close(self):
        """Close consumer connection"""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka Consumer closed")


class KafkaTopicsManager:
    """Manage Kafka topics"""
    
    def __init__(self, bootstrap_servers: str = None):
        """
        Initialize Topics Manager
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        self.bootstrap_servers = bootstrap_servers or os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    def create_topics(self) -> bool:
        """
        Create default topics for LogAgent
        
        Returns:
            True if successful
        """
        from kafka.admin import KafkaAdminClient, NewTopic
        
        topics_config = [
            NewTopic(name='log-stream', num_partitions=3, replication_factor=1),
            NewTopic(name='anomalies', num_partitions=2, replication_factor=1),
            NewTopic(name='events', num_partitions=3, replication_factor=1),
            NewTopic(name='alerts', num_partitions=1, replication_factor=1)
        ]
        
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers.split(','),
                client_id='logagent-admin'
            )
            
            fs = admin_client.create_topics(new_topics=topics_config, validate_only=False)
            
            for topic, f in fs.items():
                try:
                    f.result(timeout=30)
                    logger.info(f"Topic '{topic}' created successfully")
                except Exception as e:
                    logger.warning(f"Topic '{topic}' creation result: {e}")
            
            admin_client.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating topics: {e}")
            return False


def create_producer(bootstrap_servers: str = None) -> LogAgentProducer:
    """Factory function to create producer"""
    return LogAgentProducer(bootstrap_servers)


def create_consumer(topic: str, group_id: str = None, bootstrap_servers: str = None) -> LogAgentConsumer:
    """Factory function to create consumer"""
    return LogAgentConsumer(topic, group_id, bootstrap_servers)


def create_topics_manager(bootstrap_servers: str = None) -> KafkaTopicsManager:
    """Factory function to create topics manager"""
    return KafkaTopicsManager(bootstrap_servers)
