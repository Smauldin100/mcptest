"""
Chatbot processor for database interactions.
This module handles natural language processing and query generation.
"""

import re
import logging
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import spacy
from transformers import pipeline
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Download NLTK resources if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

class ChatbotProcessor:
    """
    A class to process natural language queries and convert them to database operations.
    """
    
    def __init__(self, db_connector, use_transformer=True):
        """
        Initialize the chatbot processor.
        
        Args:
            db_connector: DatabaseConnector instance
            use_transformer (bool): Whether to use transformer models for NLP
        """
        self.db = db_connector
        self.use_transformer = use_transformer
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Load NLP models
        if self.use_transformer:
            try:
                self.nlp_pipeline = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
                self.qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
                logger.info("Transformer models loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load transformer models: {str(e)}. Falling back to rule-based approach.")
                self.use_transformer = False
        
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Spacy model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {str(e)}. Will use basic NLP instead.")
            self.nlp = None
        
        # Cache database schema information
        self.tables = self.db.get_all_tables()
        self.table_schemas = {}
        for table in self.tables:
            self.table_schemas[table] = self.db.get_table_schema(table)
    
    def preprocess_text(self, text):
        """
        Preprocess the input text.
        
        Args:
            text (str): Input text
            
        Returns:
            list: List of preprocessed tokens
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stop words and lemmatize
        processed_tokens = [
            self.lemmatizer.lemmatize(token) 
            for token in tokens 
            if token not in self.stop_words
        ]
        
        return processed_tokens
    
    def extract_intent(self, text):
        """
        Extract the intent from the input text.
        
        Args:
            text (str): Input text
            
        Returns:
            str: Intent ('select', 'insert', 'update', 'delete', 'describe', 'unknown')
        """
        processed_tokens = self.preprocess_text(text)
        
        # Check for select intent
        select_keywords = ['show', 'display', 'list', 'get', 'select', 'find', 'search', 'query', 'what', 'how', 'where']
        if any(keyword in processed_tokens for keyword in select_keywords):
            return 'select'
        
        # Check for insert intent
        insert_keywords = ['add', 'insert', 'create', 'new', 'put']
        if any(keyword in processed_tokens for keyword in insert_keywords):
            return 'insert'
        
        # Check for update intent
        update_keywords = ['update', 'change', 'modify', 'edit', 'alter']
        if any(keyword in processed_tokens for keyword in update_keywords):
            return 'update'
        
        # Check for delete intent
        delete_keywords = ['delete', 'remove', 'drop', 'eliminate']
        if any(keyword in processed_tokens for keyword in delete_keywords):
            return 'delete'
        
        # Check for describe intent
        describe_keywords = ['describe', 'explain', 'structure', 'schema']
        if any(keyword in processed_tokens for keyword in describe_keywords):
            return 'describe'
        
        return 'unknown'
    
    def extract_entities(self, text):
        """
        Extract entities from the input text.
        
        Args:
            text (str): Input text
            
        Returns:
            dict: Dictionary of extracted entities
        """
        entities = {
            'tables': [],
            'columns': [],
            'conditions': [],
            'values': [],
            'limit': None
        }
        
        # Use spaCy for entity extraction if available
        if self.nlp:
            doc = self.nlp(text)
            
            # Extract potential table names
            for token in doc:
                if token.pos_ in ['NOUN', 'PROPN']:
                    # Check if token matches any table name
                    for table in self.tables:
                        if token.text.lower() in table.lower():
                            entities['tables'].append(table)
            
            # Extract potential column names
            for table in entities['tables']:
                for column_info in self.table_schemas.get(table, []):
                    column_name = None
                    # Extract column name based on database type
                    if 'column_name' in column_info:
                        column_name = column_info['column_name']
                    elif 'Field' in column_info:
                        column_name = column_info['Field']
                    elif 'name' in column_info:
                        column_name = column_info['name']
                    
                    if column_name:
                        for token in doc:
                            if token.text.lower() in column_name.lower():
                                entities['columns'].append(column_name)
            
            # Extract potential values (numbers, dates, named entities)
            for ent in doc.ents:
                if ent.label_ in ['CARDINAL', 'MONEY', 'PERCENT', 'QUANTITY', 'DATE', 'TIME']:
                    entities['values'].append(ent.text)
                elif ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT']:
                    entities['values'].append(ent.text)
            
            # Extract potential conditions
            condition_patterns = [
                r'where\s+(\w+)\s*(=|>|<|>=|<=|!=|like)\s*(["\']?[\w\s]+["\']?)',
                r'(\w+)\s+(equals|equal to|greater than|less than|not equal to)\s+(["\']?[\w\s]+["\']?)'
            ]
            
            for pattern in condition_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if len(match) >= 3:
                        column, operator, value = match
                        entities['conditions'].append({
                            'column': column,
                            'operator': operator,
                            'value': value.strip('"\'')
                        })
            
            # Extract limit
            limit_pattern = r'(limit|top|first)\s+(\d+)'
            limit_match = re.search(limit_pattern, text, re.IGNORECASE)
            if limit_match:
                entities['limit'] = int(limit_match.group(2))
        
        return entities
    
    def generate_sql_query(self, intent, entities):
        """
        Generate a SQL query based on intent and entities.
        
        Args:
            intent (str): Query intent
            entities (dict): Extracted entities
            
        Returns:
            str: Generated SQL query
        """
        if not entities['tables']:
            return None
        
        table = entities['tables'][0]
        
        if intent == 'select':
            columns = '*'
            if entities['columns']:
                columns = ', '.join(entities['columns'])
            
            query = f"SELECT {columns} FROM {table}"
            
            if entities['conditions']:
                conditions = []
                for condition in entities['conditions']:
                    conditions.append(f"{condition['column']} {condition['operator']} '{condition['value']}'")
                
                query += " WHERE " + " AND ".join(conditions)
            
            if entities['limit']:
                query += f" LIMIT {entities['limit']}"
            
            return query
        
        elif intent == 'describe':
            return f"DESCRIBE {table}"
        
        # For other intents, we'd need more complex logic and user confirmation
        # before executing potentially destructive operations
        
        return None
    
    def process(self, user_message):
        """
        Process a user message and generate a response.
        
        Args:
            user_message (str): User's message
            
        Returns:
            dict: Response containing answer and/or data
        """
        try:
            # Extract intent
            intent = self.extract_intent(user_message)
            
            # Extract entities
            entities = self.extract_entities(user_message)
            
            # Generate SQL query
            sql_query = self.generate_sql_query(intent, entities)
            
            if sql_query:
                # Execute query
                try:
                    results = self.db.execute_query(sql_query)
                    
                    # Format response
                    if intent == 'select':
                        if results:
                            return {
                                'answer': f"Here are the results from the {entities['tables'][0]} table:",
                                'data': results,
                                'sql_query': sql_query
                            }
                        else:
                            return {
                                'answer': f"No results found in the {entities['tables'][0]} table for your query.",
                                'sql_query': sql_query
                            }
                    elif intent == 'describe':
                        return {
                            'answer': f"Here's the structure of the {entities['tables'][0]} table:",
                            'data': results,
                            'sql_query': sql_query
                        }
                except Exception as e:
                    logger.error(f"Error executing query: {str(e)}")
                    return {
                        'answer': f"I encountered an error while querying the database: {str(e)}",
                        'sql_query': sql_query
                    }
            else:
                # Handle cases where SQL generation failed
                if not entities['tables']:
                    return {
                        'answer': "I couldn't identify which table you're referring to. Please specify a table name."
                    }
                else:
                    return {
                        'answer': "I'm not sure how to process that request. Could you rephrase it?"
                    }
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                'answer': "I encountered an error while processing your request. Please try again."
            }