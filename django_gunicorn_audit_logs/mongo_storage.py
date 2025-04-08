"""
MongoDB storage backend for Django Gunicorn Audit Logs.
"""
import logging
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Try to import MongoEngine first
try:
    # Only import what we actually use
    from mongoengine import connect, Document, DateTimeField, StringField, IntField, DictField
    from mongoengine.connection import ConnectionFailure
    from mongoengine.errors import ValidationError
    MONGO_AVAILABLE = True
    USING_MONGOENGINE = True
except ImportError:
    # Fall back to PyMongo if MongoEngine is not available
    try:
        import pymongo
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, OperationFailure
        MONGO_AVAILABLE = True
        USING_MONGOENGINE = False
    except ImportError:
        MONGO_AVAILABLE = False
        USING_MONGOENGINE = False
        # Define these to avoid NameError when they're referenced
        pymongo = None
        MongoClient = None
        OperationFailure = Exception  # Fallback definition
    else:
        USING_MONGOENGINE = False
else:
    USING_MONGOENGINE = True

# Use try/except for Django imports to handle cases where Django isn't fully initialized
try:
    from django.conf import settings
except ImportError:
    settings = None
    logger = logging.getLogger('django_gunicorn_audit_logs')
else:
    logger = logging.getLogger('django_gunicorn_audit_logs')


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
            logger.warning("MongoDB support not available. Install with 'pip install django-gunicorn-audit-logs[mongo]'")
            return
        
        # Get MongoDB settings from environment variables or Django settings
        mongo_settings = getattr(settings, 'AUDIT_LOGS_MONGO', {}) if settings else {}
        
        # MongoDB connection settings - try environment variables first, then settings
        self.connection_uri = os.environ.get('AUDIT_LOGS_MONGO_URI') or mongo_settings.get('URI', None)
        self.db_name = os.environ.get('AUDIT_LOGS_MONGO_DB_NAME') or mongo_settings.get('DB_NAME', 'audit_logs')
        self.request_logs_collection_name = (
            os.environ.get('AUDIT_LOGS_MONGO_REQUEST_LOGS_COLLECTION') or 
            mongo_settings.get('REQUEST_LOGS_COLLECTION', 'request_logs')
        )
        self.gunicorn_logs_collection_name = (
            os.environ.get('AUDIT_LOGS_MONGO_GUNICORN_LOGS_COLLECTION') or 
            mongo_settings.get('GUNICORN_LOGS_COLLECTION', 'gunicorn_logs')
        )
        
        # Connect to MongoDB
        try:
            if USING_MONGOENGINE:
                # Connect using MongoEngine
                if self.connection_uri:
                    connect(host=self.connection_uri, alias='audit_logs')
                    logger.info("Connected to MongoDB using MongoEngine")
            else:
                # Connect using PyMongo
                if self.connection_uri:
                    # Define MongoClient before using it
                    self.client = MongoClient(self.connection_uri)
                    self.db = self.client[self.db_name]
                    self.request_logs_collection = self.db[self.request_logs_collection_name]
                    self.gunicorn_logs_collection = self.db[self.gunicorn_logs_collection_name]
                    logger.info("Connected to MongoDB using PyMongo")
            
            # Create indexes
            self._create_indexes()
        except ConnectionFailure as e:
            logger.error("Failed to connect to MongoDB: %s", e)
        except (ValueError, AttributeError) as e:
            logger.error("Invalid MongoDB configuration: %s", e)
    
    def _create_indexes(self):
        """Create indexes for better query performance."""
        try:
            if not USING_MONGOENGINE and self.db is not None:
                # Create indexes using PyMongo
                if pymongo is not None:
                    # Request logs indexes
                    if self.request_logs_collection is not None:
                        self.request_logs_collection.create_index([("timestamp", pymongo.DESCENDING)])
                        self.request_logs_collection.create_index("method")
                        self.request_logs_collection.create_index("path")
                        self.request_logs_collection.create_index("status_code")
                        self.request_logs_collection.create_index("user_id")
                        self.request_logs_collection.create_index("ip_address")
                    
                    # Gunicorn logs indexes
                    if self.gunicorn_logs_collection is not None:
                        self.gunicorn_logs_collection.create_index([("timestamp", pymongo.DESCENDING)])
                        self.gunicorn_logs_collection.create_index("method")
                        self.gunicorn_logs_collection.create_index("url")
                        self.gunicorn_logs_collection.create_index("code")
                        self.gunicorn_logs_collection.create_index("user_id")
        except OperationFailure as e:
            logger.error("Failed to create MongoDB indexes: %s", e)
        except (ValueError, AttributeError) as e:
            logger.error("Invalid MongoDB configuration for indexes: %s", e)
    
    def is_available(self):
        """Check if MongoDB storage is available."""
        try:
            if USING_MONGOENGINE:
                return MONGO_AVAILABLE
            else:
                return self.client is not None and self.db is not None
        except (ValueError, AttributeError) as e:
            logger.error("Error checking MongoDB availability: %s", e)
            return False
    
    def create_request_log(self, **kwargs):
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
            if USING_MONGOENGINE:
                # Create document using MongoEngine
                log = RequestLogDocument(**kwargs)
                log.save()
                return True
            else:
                # Create document using PyMongo
                if self.request_logs_collection is not None:
                    # Ensure timestamp is a datetime object
                    if 'timestamp' not in kwargs:
                        kwargs['timestamp'] = datetime.now()
                    self.request_logs_collection.insert_one(kwargs)
                    return True
                return False
        except ValidationError as e:
            logger.error("MongoDB validation error: %s", e)
            return False
        except OperationFailure as e:
            logger.error("MongoDB operation error: %s", e)
            return False
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Invalid data for MongoDB request log: %s", e)
            return False
    
    def create_gunicorn_log(self, **kwargs):
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
            if USING_MONGOENGINE:
                # Create document using MongoEngine
                log = GunicornLogDocument(**kwargs)
                log.save()
                return True
            else:
                # Create document using PyMongo
                if self.gunicorn_logs_collection is not None:
                    # Ensure timestamp is a datetime object
                    if 'timestamp' not in kwargs:
                        kwargs['timestamp'] = datetime.now()
                    self.gunicorn_logs_collection.insert_one(kwargs)
                    return True
                return False
        except ValidationError as e:
            logger.error("MongoDB validation error: %s", e)
            return False
        except OperationFailure as e:
            logger.error("MongoDB operation error: %s", e)
            return False
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Invalid data for MongoDB Gunicorn log: %s", e)
            return False
    
    def get_request_logs(self, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         method: Optional[str] = None,
                         path: Optional[str] = None,
                         status_code: Optional[int] = None,
                         user_id: Optional[str] = None,
                         limit: int = 100,
                         skip: int = 0):
        """
        Query request logs from MongoDB.
        
        Args:
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            method: Filter by HTTP method
            path: Filter by request path
            status_code: Filter by HTTP status code
            user_id: Filter by user ID
            limit: Maximum number of results to return
            skip: Number of results to skip (for pagination)
            
        Returns:
            List of log entries
        """
        if not self.is_available():
            return []
        
        try:
            if USING_MONGOENGINE:
                # Build query using MongoEngine
                query = {}
                
                # Add date range filter
                if start_date or end_date:
                    if start_date:
                        query['timestamp__gte'] = start_date
                    if end_date:
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
                if self.request_logs_collection is not None and pymongo is not None:
                    cursor = self.request_logs_collection.find(query).sort('timestamp', pymongo.DESCENDING).skip(skip).limit(limit)
                    return list(cursor)
                return []
        except ValidationError as e:
            logger.error("MongoDB validation error: %s", e)
            return []
        except OperationFailure as e:
            logger.error("MongoDB operation error: %s", e)
            return []
        except (ValueError, TypeError, AttributeError) as e:
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
                          skip: int = 0):
        """
        Query Gunicorn logs from MongoDB.
        
        Args:
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            method: Filter by HTTP method
            url: Filter by URL
            code: Filter by HTTP status code
            user_id: Filter by user ID
            limit: Maximum number of results to return
            skip: Number of results to skip (for pagination)
            
        Returns:
            List of log entries
        """
        if not self.is_available():
            return []
        
        try:
            if USING_MONGOENGINE:
                # Build query using MongoEngine
                query = {}
                
                # Add date range filter
                if start_date or end_date:
                    if start_date:
                        query['timestamp__gte'] = start_date
                    if end_date:
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
                if self.gunicorn_logs_collection is not None and pymongo is not None:
                    cursor = self.gunicorn_logs_collection.find(query).sort('timestamp', pymongo.DESCENDING).skip(skip).limit(limit)
                    return list(cursor)
                return []
        except ValidationError as e:
            logger.error("MongoDB validation error: %s", e)
            return []
        except OperationFailure as e:
            logger.error("MongoDB operation error: %s", e)
            return []
        except (ValueError, TypeError, AttributeError) as e:
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
        except ValidationError as e:
            logger.error("MongoDB validation error: %s", e)
            return 0
        except OperationFailure as e:
            logger.error("MongoDB operation error: %s", e)
            return 0
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Failed to clean up old MongoDB logs: %s", e)
            return 0


# Singleton instance
mongo_storage = MongoLogStorage()
