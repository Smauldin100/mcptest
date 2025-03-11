# Local Database Chatbot Setup Guide

This repository contains instructions and code examples for setting up a chatbot that interacts with your local database.

## Overview

A local database chatbot allows users to query and interact with your database using natural language. This setup combines:
- A conversational AI interface
- Database connectivity
- Natural language processing to convert queries to database operations

## Prerequisites

- Python 3.8+
- A local database (MySQL, PostgreSQL, SQLite, etc.)
- Basic knowledge of SQL and Python

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Smauldin100/mcptest.git
cd mcptest
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Database Configuration

1. Create a `.env` file in the project root with your database credentials:
```
DB_TYPE=mysql  # or postgresql, sqlite, etc.
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

2. For SQLite, you can simply specify the path:
```
DB_TYPE=sqlite
DB_PATH=/path/to/your/database.db
```

## Chatbot Setup

### Option 1: Using a Pre-trained Model

1. Install a conversational AI library like Rasa or ChatterBot:
```bash
pip install rasa  # or pip install chatterbot
```

2. Train the model with your database-specific intents and entities.

3. Connect the model to your database using a custom action server.

### Option 2: Using an API-based Solution

1. Set up integration with OpenAI, Google Dialogflow, or similar services.

2. Create a middleware that translates natural language queries to SQL.

3. Implement database connection handlers.

## Sample Implementation

```python
# app.py
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from database import DatabaseConnector
from chatbot import ChatbotProcessor

# Load environment variables
load_dotenv()

app = Flask(__name__)
db = DatabaseConnector(
    db_type=os.getenv("DB_TYPE"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
chatbot = ChatbotProcessor(db)

@app.route('/query', methods=['POST'])
def process_query():
    user_message = request.json.get('message', '')
    response = chatbot.process(user_message)
    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True)
```

## Security Considerations

- Implement proper input validation to prevent SQL injection
- Use parameterized queries
- Limit database permissions for the chatbot user
- Implement rate limiting
- Consider data privacy regulations

## Advanced Features

- Context awareness for multi-turn conversations
- User authentication and personalization
- Query history and analytics
- Export functionality for query results

## Troubleshooting

- Check database connection parameters
- Verify database user permissions
- Review chatbot training data for coverage of common queries
- Monitor logs for error patterns

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.