"""
Trip Statuses repository - data access layer for trip statuses.
"""
from typing import Optional
from datetime import datetime
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


class TripStatusRepository(BaseRepository):
    """
    Repository for trip status data access.
    Uses MongoDB collection 'trip_statuses'.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize TripStatusRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('trip_statuses', connection)
    
    def find_by_code(self, code: str) -> Optional[dict]:
        """
        Find trip status by code.
        
        Args:
            code: Status code (e.g., 'scheduled', 'in_transit')
            
        Returns:
            Trip status document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        if not code:
            return None
        
        try:
            return self.find_one({"code": code})
        except Exception as e:
            raise RepositoryError(f"Error finding trip status by code {code}: {str(e)}")
    
    def find_non_terminal(self) -> list[dict]:
        """
        Find all non-terminal trip statuses (trip can continue).
        
        Returns:
            List of non-terminal status documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many({"is_terminal": False})
        except Exception as e:
            raise RepositoryError(f"Error finding non-terminal statuses: {str(e)}")
    
    def find_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """
        Find all trip statuses, ordered by sequence.
        
        Args:
            skip: Pagination offset
            limit: Maximum results
            
        Returns:
            List of trip statuses ordered by 'order' field
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {},
                skip=skip,
                limit=limit,
                sort=[("order", 1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding all trip statuses: {str(e)}")
