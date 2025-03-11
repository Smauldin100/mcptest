"""
Database connector for the chatbot application.
This module handles all database interactions.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseConnector:
    """
    A class to handle database connections and queries.
    Supports MySQL, PostgreSQL, and SQLite.
    """
    
    def __init__(self, db_type=None, host=None, port=None, dbname=None, user=None, password=None, db_path=None):
        """
        Initialize the database connector with connection parameters.
        
        Args:
            db_type (str): Type of database ('mysql', 'postgresql', 'sqlite')
            host (str): Database host address
            port (str): Database port
            dbname (str): Database name
            user (str): Database username
            password (str): Database password
            db_path (str): Path to SQLite database file (for SQLite only)
        """
        self.db_type = db_type
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.db_path = db_path
        self.engine = None
        
        self._connect()
    
    def _connect(self):
        """Establish connection to the database."""
        try:
            if self.db_type == 'mysql':
                connection_string = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
            elif self.db_type == 'postgresql':
                connection_string = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
            elif self.db_type == 'sqlite':
                connection_string = f"sqlite:///{self.db_path}"
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
            
            self.engine = create_engine(connection_string)
            logger.info(f"Successfully connected to {self.db_type} database")
            
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def execute_query(self, query, params=None):
        """
        Execute a SQL query and return the results.
        
        Args:
            query (str): SQL query to execute
            params (dict, optional): Parameters for the query
            
        Returns:
            list: List of dictionaries containing the query results
        """
        if not self.engine:
            raise ConnectionError("Database connection not established")
        
        try:
            with self.engine.connect() as connection:
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))
                
                # Convert result to list of dictionaries
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
                
        except SQLAlchemyError as e:
            logger.error(f"Query execution error: {str(e)}")
            raise
    
    def get_table_schema(self, table_name):
        """
        Get the schema of a specific table.
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            list: List of dictionaries containing column information
        """
        if self.db_type == 'mysql':
            query = f"DESCRIBE {table_name}"
        elif self.db_type == 'postgresql':
            query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """
        elif self.db_type == 'sqlite':
            query = f"PRAGMA table_info({table_name})"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        
        return self.execute_query(query)
    
    def get_all_tables(self):
        """
        Get a list of all tables in the database.
        
        Returns:
            list: List of table names
        """
        if self.db_type == 'mysql':
            query = "SHOW TABLES"
        elif self.db_type == 'postgresql':
            query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """
        elif self.db_type == 'sqlite':
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        
        result = self.execute_query(query)
        
        # Extract table names from result
        if self.db_type == 'mysql':
            return [list(row.values())[0] for row in result]
        elif self.db_type == 'postgresql':
            return [row['table_name'] for row in result]
        elif self.db_type == 'sqlite':
            return [row['name'] for row in result]
    
    def test_connection(self):
        """
        Test the database connection.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            if self.db_type == 'mysql' or self.db_type == 'postgresql':
                self.execute_query("SELECT 1")
            elif self.db_type == 'sqlite':
                self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False