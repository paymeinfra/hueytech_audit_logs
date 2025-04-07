"""
MongoDB storage backend for Django Audit Logger.
"""
import logging
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    import pymongo
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

from django.conf import settings

logger = logging.getLogger('django_audit_logger')


class MongoLogStorage:
    """
    MongoDB storage backend for audit logs.
    """
    def __init__(self):
        """Initialize MongoDB connection if available."""
        self.client = None
        self.db = None
        self.request_logs_collection = None
        self.gunicorn_logs_collection = None
        
        if not MONGO_AVAILABLE:
            logger.warning("MongoDB support not available. Install with 'pip install django-audit-logger[mongo]'")
            return
        
        # Get MongoDB settings from environment variables or Django settings
        mongo_settings = getattr(settings, 'AUDIT_LOGS_MONGO', {})
        
        # MongoDB connection settings - try environment variables first, then settings
        self.connection_uri = os.environ.get('AUDIT_LOGS_MONGO_URI') or mongo_settings.get('URI', None)
        self.db_name = os.environ.get('AUDIT_LOGS_MONGO_DB_NAME') or mongo_settings.get('DB_NAME', 'audit_logs')
        self.request_logs_collection_name = os.environ.get('AUDIT_LOGS_MONGO_REQUEST_LOGS_COLLECTION') or mongo_settings.get('REQUEST_LOGS_COLLECTION', 'request_logs')
        self.gunicorn_logs_collection_name = os.environ.get('AUDIT_LOGS_MONGO_GUNICORN_LOGS_COLLECTION') or mongo_settings.get('GUNICORN_LOGS_COLLECTION', 'gunicorn_logs')
        
        # Connect to MongoDB if URI is provided
        if self.connection_uri:
            try:
                self.client = MongoClient(self.connection_uri)
                # Test connection
                self.client.admin.command('ping')
                self.db = self.client[self.db_name]
                self.request_logs_collection = self.db[self.request_logs_collection_name]
                self.gunicorn_logs_collection = self.db[self.gunicorn_logs_collection_name]
                
                # Create indexes for better query performance
                self._create_indexes()
                
                logger.info("Successfully connected to MongoDB")
            except (ConnectionFailure, OperationFailure) as e:
                logger.error("Failed to connect to MongoDB: %s", e)
                self.client = None
    
    def _create_indexes(self):
        """Create indexes for better query performance."""
        if not self.request_logs_collection or not self.gunicorn_logs_collection:
            return
        
        # Indexes for request logs
        self.request_logs_collection.create_index([("timestamp", pymongo.DESCENDING)])
        self.request_logs_collection.create_index([("method", pymongo.ASCENDING)])
        self.request_logs_collection.create_index([("path", pymongo.ASCENDING)])
        self.request_logs_collection.create_index([("status_code", pymongo.ASCENDING)])
        self.request_logs_collection.create_index([("user_id", pymongo.ASCENDING)])
        self.request_logs_collection.create_index([("client_ip", pymongo.ASCENDING)])
        
        # Indexes for Gunicorn logs
        self.gunicorn_logs_collection.create_index([("timestamp", pymongo.DESCENDING)])
        self.gunicorn_logs_collection.create_index([("method", pymongo.ASCENDING)])
        self.gunicorn_logs_collection.create_index([("url", pymongo.ASCENDING)])
        self.gunicorn_logs_collection.create_index([("code", pymongo.ASCENDING)])
        self.gunicorn_logs_collection.create_index([("user_id", pymongo.ASCENDING)])
    
    def is_available(self) -> bool:
        """Check if MongoDB storage is available."""
        return MONGO_AVAILABLE and self.client is not None
    
    def create_request_log(self, **kwargs) -> bool:
        """
        Create a request log entry in MongoDB.
        
        Args:
            **kwargs: Log entry data including method, path, etc.
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            # Convert string JSON to dict if needed
            for field in ['query_params', 'request_headers', 'response_headers']:
                if field in kwargs and isinstance(kwargs[field], str):
                    try:
                        kwargs[field] = json.loads(kwargs[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            # Ensure timestamp is a datetime object
            if 'timestamp' not in kwargs:
                kwargs['timestamp'] = datetime.now()
            
            # Insert document
            result = self.request_logs_collection.insert_one(kwargs)
            return result.acknowledged
        except (PyMongoError, json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error("Failed to create MongoDB request log: %s", e)
            return False
    
    def create_gunicorn_log(self, **kwargs) -> bool:
        """
        Create a Gunicorn log entry in MongoDB.
        
        Args:
            **kwargs: Log entry data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            # Ensure timestamp is a datetime object
            if 'timestamp' not in kwargs:
                kwargs['timestamp'] = datetime.now()
            
            # Insert document
            result = self.gunicorn_logs_collection.insert_one(kwargs)
            return result.acknowledged
        except PyMongoError as e:
            logger.error("Failed to create MongoDB Gunicorn log: %s", e)
            return False
    
    def get_request_logs(self, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         method: Optional[str] = None,
                         path: Optional[str] = None,
                         status_code: Optional[int] = None,
                         user_id: Optional[str] = None,
                         limit: int = 100,
                         skip: int = 0) -> List[Dict[str, Any]]:
        """
        Query request logs from MongoDB.
        
        Args:
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            method: Filter by HTTP method
            path: Filter by request path
            status_code: Filter by status code
            user_id: Filter by user ID
            limit: Maximum number of logs to return
            skip: Number of logs to skip (for pagination)
            
        Returns:
            List of log entries as dictionaries
        """
        if not self.is_available():
            return []
        
        query = {}
        
        # Add date range filter
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query['$gte'] = start_date
            if end_date:
                date_query['$lte'] = end_date
            query['timestamp'] = date_query
        
        # Add other filters
        if method:
            query['method'] = method
        if path:
            query['path'] = {'$regex': path, '$options': 'i'}
        if status_code:
            query['status_code'] = status_code
        if user_id:
            query['user_id'] = user_id
        
        try:
            cursor = self.request_logs_collection.find(query).sort('timestamp', pymongo.DESCENDING).skip(skip).limit(limit)
            return list(cursor)
        except PyMongoError as e:
            logger.error("Failed to query MongoDB request logs: %s", e)
            return []
    
    def get_gunicorn_logs(self,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          method: Optional[str] = None,
                          url: Optional[str] = None,
                          code: Optional[int] = None,
                          user_id: Optional[str] = None,
                          limit: int = 100,
                          skip: int = 0) -> List[Dict[str, Any]]:
        """
        Query Gunicorn logs from MongoDB.
        
        Args:
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            method: Filter by HTTP method
            url: Filter by URL
            code: Filter by status code
            user_id: Filter by user ID
            limit: Maximum number of logs to return
            skip: Number of logs to skip (for pagination)
            
        Returns:
            List of log entries as dictionaries
        """
        if not self.is_available():
            return []
        
        query = {}
        
        # Add date range filter
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query['$gte'] = start_date
            if end_date:
                date_query['$lte'] = end_date
            query['timestamp'] = date_query
        
        # Add other filters
        if method:
            query['method'] = method
        if url:
            query['url'] = {'$regex': url, '$options': 'i'}
        if code:
            query['code'] = code
        if user_id:
            query['user_id'] = user_id
        
        try:
            cursor = self.gunicorn_logs_collection.find(query).sort('timestamp', pymongo.DESCENDING).skip(skip).limit(limit)
            return list(cursor)
        except PyMongoError as e:
            logger.error("Failed to query MongoDB Gunicorn logs: %s", e)
            return []
    
    def cleanup_old_logs(self, days: int = 90, log_type: str = 'all') -> int:
        """
        Delete logs older than the specified number of days.
        
        Args:
            days: Number of days to keep logs for
            log_type: Type of logs to clean up ('request', 'gunicorn', or 'all')
            
        Returns:
            Number of deleted documents
        """
        if not self.is_available():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        try:
            if log_type in ['request', 'all'] and self.request_logs_collection:
                result = self.request_logs_collection.delete_many({'timestamp': {'$lt': cutoff_date}})
                deleted_count += result.deleted_count
                
            if log_type in ['gunicorn', 'all'] and self.gunicorn_logs_collection:
                result = self.gunicorn_logs_collection.delete_many({'timestamp': {'$lt': cutoff_date}})
                deleted_count += result.deleted_count
                
            return deleted_count
        except PyMongoError as e:
            logger.error("Failed to clean up old MongoDB logs: %s", e)
            return 0


# Singleton instance
mongo_storage = MongoLogStorage()
