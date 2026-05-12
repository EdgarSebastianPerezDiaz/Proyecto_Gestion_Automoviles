"""
Cargo Types repository - data access layer for cargo types.
"""
from typing import Optional
from datetime import datetime
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


class CargoTypeRepository(BaseRepository):
    """
    Repository for cargo type data access.
    Uses MongoDB collection 'cargo_types'.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize CargoTypeRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('cargo_types', connection)
    
    def find_active(self, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find all active cargo types.
        
        Args:
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of active cargo type documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"is_active": True},
                limit=limit,
                skip=skip
            )
        except Exception as e:
            raise RepositoryError(f"Error finding active cargo types: {str(e)}")
    
    def find_by_name(self, name: str) -> Optional[dict]:
        """
        Find cargo type by exact name match (case-insensitive).
        
        Args:
            name: Cargo type name
            
        Returns:
            Cargo type document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        if not name:
            return None
        
        try:
            query = {
                "name": {"$regex": f"^{name}$", "$options": "i"},
                "is_active": True
            }
            return self.find_one(query)
        except Exception as e:
            raise RepositoryError(f"Error finding cargo type by name {name}: {str(e)}")
