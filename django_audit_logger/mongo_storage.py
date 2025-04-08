"""
MongoDB storage backend for Django Audit Logger.
"""
import logging
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Try to import MongoEngine first
try:
    import mongoengine
    from mongoengine import connect, Document, DateTimeField, StringField, IntField, DictField
    from mongoengine.connection import ConnectionFailure
    from mongoengine.errors import NotUniqueError, ValidationError, OperationError
    MONGO_AVAILABLE = True
except ImportError:
    # Fall back to PyMongo if MongoEngine is not available
    try:
        import pymongo
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError
        MONGO_AVAILABLE = True
        USING_MONGOENGINE = False
    except ImportError:
        MONGO_AVAILABLE = False
        USING_MONGOENGINE = False
    else:
        USING_MONGOENGINE = False
else:
    USING_MONGOENGINE = True

from django.conf import settings

logger = logging.getLogger('django_audit_logger')


# Define MongoEngine document models if available
if USING_MONGOENGINE:
    class RequestLogDocument(Document):
        """MongoDB document model for request logs."""
        timestamp = DateTimeField(default=datetime.now, required=True)
        method = StringField(max_length=10, required=True)
        path = StringField(required=True)
        query_params = DictField()
        headers = DictField()
        body = StringField()
        ip_address = StringField()
        user_id = StringField()
        status_code = IntField()
        response_headers = DictField()
        response_body = StringField()
        response_time_ms = IntField()
        
        meta = {
            'collection': 'request_logs',
            'indexes': [
                'timestamp',
                'method',
                'path',
                'status_code',
                'user_id',
                'ip_address'
            ]
        }
    
    class GunicornLogDocument(Document):
        """MongoDB document model for Gunicorn logs."""
        timestamp = DateTimeField(default=datetime.now, required=True)
        method = StringField(max_length=10)
        url = StringField()
        code = IntField()
        user_id = StringField()
        message = StringField()
        level = StringField()
        
        meta = {
            'collection': 'gunicorn_logs',
            'indexes': [
                'timestamp',
                'method',
                'url',
                'code',
                'user_id'
            ]
        }


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
                if USING_MONGOENGINE:
                    # Connect using MongoEngine
                    connect(db=self.db_name, host=self.connection_uri)
                    # Update collection names if they differ from defaults
                    if self.request_logs_collection_name != 'request_logs':
                        RequestLogDocument._meta['collection'] = self.request_logs_collection_name
                    if self.gunicorn_logs_collection_name != 'gunicorn_logs':
                        GunicornLogDocument._meta['collection'] = self.gunicorn_logs_collection_name
                    
                    # Test connection
                    RequestLogDocument.objects.count()
                    logger.info("Successfully connected to MongoDB using MongoEngine")
                else:
                    # Connect using PyMongo
                    self.client = MongoClient(self.connection_uri)
                    # Test connection
                    self.client.admin.command('ping')
                    self.db = self.client[self.db_name]
                    self.request_logs_collection = self.db[self.request_logs_collection_name]
                    self.gunicorn_logs_collection = self.db[self.gunicorn_logs_collection_name]
                    
                    # Create indexes for better query performance
                    self._create_indexes()
                    
                    logger.info("Successfully connected to MongoDB using PyMongo")
            except ConnectionFailure as e:
                logger.error("Failed to connect to MongoDB: %s", e)
                self.client = None
            except Exception as e:
                logger.error("Unexpected error connecting to MongoDB: %s", e)
                self.client = None
    
    def _create_indexes(self):
        """Create indexes for better query performance."""
        if USING_MONGOENGINE:
            # Indexes are defined in the Document meta classes
            return
            
        if self.request_logs_collection is None or self.gunicorn_logs_collection is None:
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
        if USING_MONGOENGINE:
            try:
                # Try a simple query to check connection
                RequestLogDocument.objects.limit(1).count()
                return True
            except Exception:
                return False
        else:
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
            for field in ['query_params', 'headers', 'response_headers']:
                if field in kwargs and isinstance(kwargs[field], str):
                    try:
                        kwargs[field] = json.loads(kwargs[field])
                    except json.JSONDecodeError:
                        pass
            
            # Ensure timestamp is a datetime object
            if 'timestamp' not in kwargs:
                kwargs['timestamp'] = datetime.now()
            
            # Map client_ip to ip_address if needed (for backward compatibility)
            if 'client_ip' in kwargs and 'ip_address' not in kwargs:
                kwargs['ip_address'] = kwargs.pop('client_ip')
                
            # Map execution_time to response_time_ms if needed (for backward compatibility)
            if 'execution_time' in kwargs and 'response_time_ms' not in kwargs:
                execution_time = kwargs.pop('execution_time')
                kwargs['response_time_ms'] = int(execution_time * 1000) if execution_time else None
            
            if USING_MONGOENGINE:
                # Create document using MongoEngine
                doc = RequestLogDocument(**kwargs)
                doc.save()
                return True
            else:
                # Insert document using PyMongo
                result = self.request_logs_collection.insert_one(kwargs)
                # Explicitly check if the operation was acknowledged
                return bool(result.acknowledged) if hasattr(result, 'acknowledged') else True
        except Exception as e:
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
            
            # Convert string fields to dict if needed
            for field in ['headers', 'response_headers']:
                if field in kwargs and isinstance(kwargs[field], str):
                    try:
                        kwargs[field] = json.loads(kwargs[field])
                    except json.JSONDecodeError:
                        pass
            
            if USING_MONGOENGINE:
                # Create document using MongoEngine
                doc = GunicornLogDocument(**kwargs)
                doc.save()
                return True
            else:
                # Insert document using PyMongo
                result = self.gunicorn_logs_collection.insert_one(kwargs)
                # Explicitly check if the operation was acknowledged
                return bool(result.acknowledged) if hasattr(result, 'acknowledged') else True
        except Exception as e:
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
        
        try:
            if USING_MONGOENGINE:
                # Build query using MongoEngine
                query = {}
                
                # Add date range filter
                if start_date or end_date:
                    if start_date and end_date:
                        query['timestamp__gte'] = start_date
                        query['timestamp__lte'] = end_date
                    elif start_date:
                        query['timestamp__gte'] = start_date
                    elif end_date:
                        query['timestamp__lte'] = end_date
                
                # Add other filters
                if method:
                    query['method'] = method
                if path:
                    query['path__icontains'] = path
                if status_code:
                    query['status_code'] = status_code
                if user_id:
                    query['user_id'] = user_id
                
                # Execute query
                results = RequestLogDocument.objects(**query).order_by('-timestamp').skip(skip).limit(limit)
                return [doc.to_mongo().to_dict() for doc in results]
            else:
                # Build query using PyMongo
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
                
                # Execute query
                cursor = self.request_logs_collection.find(query).sort('timestamp', pymongo.DESCENDING).skip(skip).limit(limit)
                return list(cursor)
        except Exception as e:
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
        
        try:
            if USING_MONGOENGINE:
                # Build query using MongoEngine
                query = {}
                
                # Add date range filter
                if start_date or end_date:
                    if start_date and end_date:
                        query['timestamp__gte'] = start_date
                        query['timestamp__lte'] = end_date
                    elif start_date:
                        query['timestamp__gte'] = start_date
                    elif end_date:
                        query['timestamp__lte'] = end_date
                
                # Add other filters
                if method:
                    query['method'] = method
                if url:
                    query['url__icontains'] = url
                if code:
                    query['code'] = code
                if user_id:
                    query['user_id'] = user_id
                
                # Execute query
                results = GunicornLogDocument.objects(**query).order_by('-timestamp').skip(skip).limit(limit)
                return [doc.to_mongo().to_dict() for doc in results]
            else:
                # Build query using PyMongo
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
                
                # Execute query
                cursor = self.gunicorn_logs_collection.find(query).sort('timestamp', pymongo.DESCENDING).skip(skip).limit(limit)
                return list(cursor)
        except Exception as e:
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
            if USING_MONGOENGINE:
                # Delete using MongoEngine
                if log_type in ['request', 'all']:
                    result = RequestLogDocument.objects(timestamp__lt=cutoff_date).delete()
                    deleted_count += result
                    
                if log_type in ['gunicorn', 'all']:
                    result = GunicornLogDocument.objects(timestamp__lt=cutoff_date).delete()
                    deleted_count += result
            else:
                # Delete using PyMongo
                if log_type in ['request', 'all'] and self.request_logs_collection is not None:
                    result = self.request_logs_collection.delete_many({'timestamp': {'$lt': cutoff_date}})
                    deleted_count += result.deleted_count
                    
                if log_type in ['gunicorn', 'all'] and self.gunicorn_logs_collection is not None:
                    result = self.gunicorn_logs_collection.delete_many({'timestamp': {'$lt': cutoff_date}})
                    deleted_count += result.deleted_count
                
            return deleted_count
        except Exception as e:
            logger.error("Failed to clean up old MongoDB logs: %s", e)
            return 0


# Singleton instance
mongo_storage = MongoLogStorage()
