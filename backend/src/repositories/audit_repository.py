"""
Audit repository - data access layer for audit log entities.
"""
from typing import Optional, List
from datetime import datetime, timezone
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


class AuditRepository(BaseRepository):
    """
    Repository for Audit Log entity operations.
    Extends BaseRepository with audit-specific queries.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize AuditRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('audit_logs', connection)
    
    def find_document_history(self, collection: str, document_id: str, limit: int = 100) -> List[dict]:
        """
        Find all audit entries for a specific document.
        
        Args:
            collection: Collection name
            document_id: Document ID
            limit: Maximum results
            
        Returns:
            List of audit log entries
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {
                    "collection": collection,
                    "document_id": document_id
                },
                limit=limit,
                sort=[("timestamp", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding history for {collection}.{document_id}: {str(e)}")
    
    def find_user_actions(self, user_id: str, limit: int = 100, skip: int = 0) -> List[dict]:
        """
        Find all actions performed by a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of audit log entries
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"user_id": user_id},
                limit=limit,
                skip=skip,
                sort=[("timestamp", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding actions for user {user_id}: {str(e)}")
    
    def find_collection_changes(self, collection: str, limit: int = 100, skip: int = 0) -> List[dict]:
        """
        Find all changes to a specific collection.
        
        Args:
            collection: Collection name
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of audit log entries
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"collection": collection},
                limit=limit,
                skip=skip,
                sort=[("timestamp", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding changes for {collection}: {str(e)}")
    
    def find_action_type(self, action: str, limit: int = 100, skip: int = 0) -> List[dict]:
        """
        Find all entries for a specific action type.
        
        Args:
            action: Action name (create, update, delete, etc.)
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of audit log entries
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"action": action},
                limit=limit,
                skip=skip,
                sort=[("timestamp", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding actions of type {action}: {str(e)}")
    
    def find_user_collection_actions(self, user_id: str, collection: str, limit: int = 100, skip: int = 0) -> List[dict]:
        """
        Find all actions by a user on a specific collection.
        
        Args:
            user_id: User ID
            collection: Collection name
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of audit log entries
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {
                    "user_id": user_id,
                    "collection": collection
                },
                limit=limit,
                skip=skip,
                sort=[("timestamp", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding actions for user {user_id} on {collection}: {str(e)}")
    
    def find_recent_changes(self, hours: int = 24, limit: int = 100) -> List[dict]:
        """
        Find audit entries from the last N hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum results
            
        Returns:
            List of audit log entries
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            return self.find_many(
                {"timestamp": {"$gte": cutoff_time}},
                limit=limit,
                sort=[("timestamp", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding recent changes: {str(e)}")
