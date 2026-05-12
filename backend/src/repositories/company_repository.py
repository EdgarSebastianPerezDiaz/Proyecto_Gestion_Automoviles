"""
Company repository - data access layer for company entities.
"""
from typing import Optional
from datetime import datetime, timezone
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection
from src.domain.company import sanitize_nit


class CompanyRepository(BaseRepository):
    """
    Repository for Company entity operations.
    Extends BaseRepository with company-specific queries.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize CompanyRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('companies', connection)
    
    def find_by_nit(self, nit: str) -> Optional[dict]:
        """
        Find company by NIT (normalized).
        
        Args:
            nit: Company NIT (with or without formatting)
            
        Returns:
            Company document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            normalized_nit = sanitize_nit(nit)
            return self.find_one({"nit": normalized_nit})
        except Exception as e:
            raise RepositoryError(f"Error finding company by NIT {nit}: {str(e)}")
    
    def find_active(self, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find all active companies.
        
        Args:
            limit: Maximum number of results (default 100)
            skip: Number of results to skip for pagination (default 0)
            
        Returns:
            List of active company documents
            
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
            raise RepositoryError(f"Error finding active companies: {str(e)}")
    
    def soft_delete(self, company_id: str) -> bool:
        """
        Soft delete a company (sets is_active to False).
        
        Args:
            company_id: Company ID as string
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(company_id)
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
            raise RepositoryError(f"Error soft-deleting company {company_id}: {str(e)}")
    
    def update(self, company_id: str, data: dict) -> bool:
        """
        Update company data.
        
        Args:
            company_id: Company ID as string
            data: Fields to update (will add updated_at timestamp)
            
        Returns:
            True if updated successfully, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(company_id)
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
            raise RepositoryError(f"Error updating company {company_id}: {str(e)}")
    
    def find_by_email(self, email: str) -> Optional[dict]:
        """
        Find company by email.
        
        Args:
            email: Company email
            
        Returns:
            Company document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_one({"email": email.lower().strip()})
        except Exception as e:
            raise RepositoryError(f"Error finding company by email {email}: {str(e)}")
    
    def find_by_legal_name(self, legal_name: str) -> Optional[dict]:
        """
        Find company by legal name (case-insensitive).
        
        Args:
            legal_name: Company legal name
            
        Returns:
            Company document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_one({"legal_name": {"$regex": f"^{legal_name}$", "$options": "i"}})
        except Exception as e:
            raise RepositoryError(f"Error finding company by legal name {legal_name}: {str(e)}")

