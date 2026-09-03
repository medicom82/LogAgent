"""Database module for LogAgent"""

import os
import mysql.connector
from mysql.connector import Error
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Singleton database connection manager"""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self._connection = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                user=os.getenv('MYSQL_USER', 'logagent'),
                password=os.getenv('MYSQL_PASSWORD', 'logagent_password'),
                database=os.getenv('MYSQL_DATABASE', 'logagent'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                autocommit=False
            )
            logger.info("Database connection established")
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise
    
    def get_connection(self):
        """Get active database connection"""
        if self._connection is None or not self._connection.is_connected():
            self._connect()
        return self._connection
    
    def close(self):
        """Close database connection"""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            logger.info("Database connection closed")
    
    def __del__(self):
        self.close()


def get_db_connection():
    """Helper function to get database connection"""
    return DatabaseConnection().get_connection()


def execute_query(query, params=None, fetch=False):
    """Execute a database query
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or list)
        fetch: Whether to fetch results
        
    Returns:
        Query results if fetch=True, else None
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            connection.commit()
            return cursor.rowcount
    
    except Error as e:
        connection.rollback()
        logger.error(f"Database query error: {e}")
        raise
    
    finally:
        cursor.close()


def init_db():
    """Initialize database schema"""
    import time
    
    connection = None
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_ROOT_PASSWORD', 'root_password'),
                database=os.getenv('MYSQL_DATABASE', 'logagent'),
                port=int(os.getenv('MYSQL_PORT', 3306))
            )
            break
        except Error as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Failed to connect to database after retries")
                raise
    
    if not connection or not connection.is_connected():
        raise Error("Failed to establish database connection")
    
    cursor = connection.cursor()
    
    try:
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Execute each statement separately
        for statement in schema_sql.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        connection.commit()
        logger.info("Database schema initialized successfully")
        
        # Read and execute initial data
        init_path = os.path.join(os.path.dirname(__file__), 'init.sql')
        with open(init_path, 'r', encoding='utf-8') as f:
            init_sql = f.read()
        
        for statement in init_sql.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        connection.commit()
        logger.info("Database initial data loaded successfully")
        
    except Error as e:
        connection.rollback()
        logger.error(f"Error initializing database: {e}")
        raise
    
    finally:
        cursor.close()
        connection.close()
