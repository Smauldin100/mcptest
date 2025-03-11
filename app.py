"""
Main application file for the database chatbot.
This module provides a Flask web server for interacting with the chatbot.
"""

import os
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from database import DatabaseConnector
from chatbot import ChatbotProcessor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize database connector
db = None
try:
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    if db_type.lower() == "sqlite":
        db_path = os.getenv("DB_PATH", "database.db")
        db = DatabaseConnector(db_type=db_type, db_path=db_path)
    else:
        db = DatabaseConnector(
            db_type=db_type,
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "3306"),
            dbname=os.getenv("DB_NAME", ""),
            user=os.getenv("DB_USER", ""),
            password=os.getenv("DB_PASSWORD", "")
        )
    
    # Test connection
    if not db.test_connection():
        logger.error("Database connection test failed")
        db = None
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    db = None

# Initialize chatbot processor if database connection is successful
chatbot = None
if db:
    try:
        use_transformer = os.getenv("USE_TRANSFORMER", "true").lower() == "true"
        chatbot = ChatbotProcessor(db, use_transformer=use_transformer)
        logger.info("Chatbot processor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize chatbot: {str(e)}")

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def process_query():
    """
    Process a natural language query.
    
    Request body:
    {
        "message": "Show me all users"
    }
    
    Response:
    {
        "response": {
            "answer": "Here are the results from the users table:",
            "data": [...],
            "sql_query": "SELECT * FROM users"
        }
    }
    """
    if not db or not chatbot:
        return jsonify({
            "error": "Database or chatbot not initialized properly. Check server logs."
        }), 500
    
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({
                "error": "No message provided"
            }), 400
        
        # Process the message
        response = chatbot.process(user_message)
        
        return jsonify({
            "response": response
        })
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({
            "error": f"Error processing query: {str(e)}"
        }), 500

@app.route('/api/tables', methods=['GET'])
def get_tables():
    """
    Get a list of all tables in the database.
    
    Response:
    {
        "tables": ["users", "products", "orders"]
    }
    """
    if not db:
        return jsonify({
            "error": "Database not initialized properly. Check server logs."
        }), 500
    
    try:
        tables = db.get_all_tables()
        return jsonify({
            "tables": tables
        })
    
    except Exception as e:
        logger.error(f"Error getting tables: {str(e)}")
        return jsonify({
            "error": f"Error getting tables: {str(e)}"
        }), 500

@app.route('/api/schema/<table_name>', methods=['GET'])
def get_table_schema(table_name):
    """
    Get the schema of a specific table.
    
    Response:
    {
        "schema": [...]
    }
    """
    if not db:
        return jsonify({
            "error": "Database not initialized properly. Check server logs."
        }), 500
    
    try:
        schema = db.get_table_schema(table_name)
        return jsonify({
            "schema": schema
        })
    
    except Exception as e:
        logger.error(f"Error getting schema: {str(e)}")
        return jsonify({
            "error": f"Error getting schema: {str(e)}"
        }), 500

@app.route('/api/execute', methods=['POST'])
def execute_sql():
    """
    Execute a raw SQL query.
    
    Request body:
    {
        "query": "SELECT * FROM users WHERE id = 1",
        "params": {"id": 1}  // Optional
    }
    
    Response:
    {
        "results": [...]
    }
    """
    if not db:
        return jsonify({
            "error": "Database not initialized properly. Check server logs."
        }), 500
    
    try:
        data = request.json
        query = data.get('query', '')
        params = data.get('params', None)
        
        if not query:
            return jsonify({
                "error": "No query provided"
            }), 400
        
        # Execute the query
        results = db.execute_query(query, params)
        
        return jsonify({
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return jsonify({
            "error": f"Error executing query: {str(e)}"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Check the health of the application.
    
    Response:
    {
        "status": "ok",
        "database": true,
        "chatbot": true
    }
    """
    database_ok = db is not None and db.test_connection()
    chatbot_ok = chatbot is not None
    
    status = "ok" if database_ok and chatbot_ok else "degraded"
    
    return jsonify({
        "status": status,
        "database": database_ok,
        "chatbot": chatbot_ok
    })

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "false").lower() == "true")