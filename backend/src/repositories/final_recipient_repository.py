"""
Final Recipients repository - data access layer for final recipients.
"""
from typing import Optional
from datetime import datetime
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


class FinalRecipientRepository(BaseRepository):
    """
    Repository for final recipient data access.
    Uses MongoDB collection 'final_recipients'.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize FinalRecipientRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('final_recipients', connection)
    
    def find_by_name(self, name: str, limit: int = 10) -> list[dict]:
        """
        Find recipients by partial name match (case-insensitive).
        
        Args:
            name: Partial name to search for
            limit: Maximum results to return
            
        Returns:
            List of matching recipient documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        if not name:
            return []
        
        try:
            query = {
                "name": {"$regex": name, "$options": "i"},
                "is_active": True
            }
            return self.find_many(query, limit=limit)
        except Exception as e:
            raise RepositoryError(f"Error finding recipients by name {name}: {str(e)}")
    
    def find_active(self, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find all active recipients.
        
        Args:
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of active recipient documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many({"is_active": True}, limit=limit, skip=skip)
        except Exception as e:
            raise RepositoryError(f"Error finding active recipients: {str(e)}")
