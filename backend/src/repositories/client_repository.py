"""
Client repository - data access layer for client entities.
"""
from typing import Optional
from datetime import datetime, timezone
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection
from src.domain.client import sanitize_nit


class ClientRepository(BaseRepository):
    """
    Repository for Client entity operations.
    Extends BaseRepository with client-specific queries.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize ClientRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('clients', connection)
    
    def find_by_nit(self, nit: str) -> Optional[dict]:
        """
        Find client by NIT (normalized).
        
        Args:
            nit: Client NIT (with or without formatting)
            
        Returns:
            Client document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            normalized_nit = sanitize_nit(nit)
            return self.find_one({"nit": normalized_nit})
        except Exception as e:
            raise RepositoryError(f"Error finding client by NIT {nit}: {str(e)}")
    
    def find_active(self, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find all active clients.
        
        Args:
            limit: Maximum number of results (default 100)
            skip: Number of results to skip for pagination (default 0)
            
        Returns:
            List of active client documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"is_active": True},
                skip=skip,
                limit=limit
            )
        except Exception as e:
            raise RepositoryError(f"Error finding active clients: {str(e)}")
    
    def soft_delete(self, client_id: str) -> bool:
        """
        Soft delete a client (sets is_active to False).
        
        Args:
            client_id: Client ID as string
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(client_id)
            except Exception:
                # Invalid ObjectId format
                return False
            
            return self.update_one(
                {"_id": object_id},
                {"$set": {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError(f"Error soft-deleting client {client_id}: {str(e)}")
    
    def update(self, client_id: str, data: dict) -> bool:
        """
        Update client data.
        
        Args:
            client_id: Client ID as string
            data: Fields to update (will add updated_at timestamp)
            
        Returns:
            True if updated successfully, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(client_id)
            except Exception:
                # Invalid ObjectId format
                return False
            
            # Add updated_at timestamp
            update_data = {**data, "updated_at": datetime.now(timezone.utc)}
            
            return self.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError(f"Error updating client {client_id}: {str(e)}")
    
    def find_by_email(self, email: str) -> Optional[dict]:
        """
        Find client by email.
        
        Args:
            email: Client email
            
        Returns:
            Client document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_one({"email": email.lower().strip()})
        except Exception as e:
            raise RepositoryError(f"Error finding client by email {email}: {str(e)}")

    def find_by_user(self, user_id: str, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find clients created by a specific user (ownership-based filtering).
        
        Args:
            user_id: User ID (creator/owner of the clients)
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of client documents created by the user
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"created_by": user_id},
                limit=limit,
                skip=skip,
                sort=[("created_at", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding clients for user {user_id}: {str(e)}")
