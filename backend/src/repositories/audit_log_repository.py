"""
Audit Log Repository

Data access layer for audit log entities.
Extends BaseRepository with audit-specific queries.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


class AuditLogRepository(BaseRepository):
    """
    Repository for audit log data access.
    
    Provides CRUD operations and audit-specific queries.
    Extends BaseRepository for common functionality.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize audit log repository.
        
        Args:
            connection: MongoDBConnection singleton instance
            
        Raises:
            RepositoryError: If connection is not initialized
        """
        super().__init__('audit_log', connection)
    
    def log_action(
        self,
        collection_name: str,
        document_id: str,
        action: str,
        user_id: str,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an action for audit purposes.
        
        Args:
            collection_name: Name of the collection being modified
            document_id: ObjectId of the document as string
            action: Action type ('INSERT', 'UPDATE', 'DELETE', 'SOFT_DELETE')
            user_id: User who performed the action
            previous_state: Previous document state (for UPDATE/DELETE)
            new_state: New document state (for INSERT/UPDATE)
            ip_address: IP address of the request origin
            endpoint: API endpoint that made the change
            details: Additional context information
            
        Returns:
            ID of the created audit log entry
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc),
                'collection_name': collection_name,
                'document_id': document_id,
                'action': action,
                'user_id': user_id,
                'previous_state': previous_state,
                'new_state': new_state,
                'ip_address': ip_address,
                'endpoint': endpoint,
                'details': details or {}
            }
            
            return self.insert_one(log_entry)
        except Exception as e:
            raise RepositoryError(f"Error logging action: {str(e)}")
    
    def get_by_document(
        self,
        collection_name: str,
        document_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get all audit entries for a specific document.
        
        Args:
            collection_name: Name of the collection
            document_id: ObjectId of the document as string
            limit: Maximum number of results
            
        Returns:
            List of audit log entries (newest first)
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            return self.find_many(
                {
                    'collection_name': collection_name,
                    'document_id': document_id
                },
                limit=limit,
                sort=[('timestamp', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error getting document history: {str(e)}")
    
    def get_by_user(
        self,
        user_id: str,
        limit: int = 1000,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all actions performed by a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of audit log entries (newest first)
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            return self.find_many(
                {'user_id': user_id},
                limit=limit,
                skip=skip,
                sort=[('timestamp', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error getting user actions: {str(e)}")
    
    def get_by_action(
        self,
        action: str,
        since_date: Optional[datetime] = None,
        limit: int = 1000,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all entries for a specific action type.
        
        Args:
            action: Action type ('INSERT', 'UPDATE', 'DELETE', 'SOFT_DELETE')
            since_date: Optional start date (inclusive)
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of audit log entries (newest first)
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            query = {'action': action}
            if since_date:
                query['timestamp'] = {'$gte': since_date}
            
            return self.find_many(
                query,
                limit=limit,
                skip=skip,
                sort=[('timestamp', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error getting entries by action: {str(e)}")
    
    def get_collection_changes(
        self,
        collection_name: str,
        limit: int = 1000,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all changes to a specific collection.
        
        Args:
            collection_name: Name of the collection
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of audit log entries (newest first)
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            return self.find_many(
                {'collection_name': collection_name},
                limit=limit,
                skip=skip,
                sort=[('timestamp', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error getting collection changes: {str(e)}")
