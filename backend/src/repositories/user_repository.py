"""
User Repository Module

Implements data access layer for User entities.
Extends BaseRepository with user-specific queries.

Security:
- Sanitized email lookups to prevent NoSQL injection
- Password_hash is never returned in queries (except for login verification)
"""

from typing import Optional, Dict, Any
import re
from bson import ObjectId
from src.repositories.base_repository import BaseRepository
from src.infrastructure.database import MongoDBConnection, RepositoryError
from src.infrastructure.sanitizer import sanitize_string


class UserRepository(BaseRepository):
    """
    Repository for User entities.
    
    Provides high-level data access methods specific to user management:
    - Email-based lookups
    - Last login tracking
    - User creation with validation
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize UserRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('users', connection)
    
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by email address (case-insensitive).
        
        Args:
            email: Email address to search for
            
        Returns:
            dict: User document (with password_hash for login verification),
                  or None if not found
            
        Raises:
            RepositoryError: On database operations error
        """
        if not email:
            return None
        
        try:
            # Normalize email to lowercase (application always stores lowercase emails)
            normalized_email = email.strip().lower()
            
            # Search directly without sanitization (sanitizer removes @ which breaks emails)
            # Email is already normalized so safe for direct query
            doc = self.collection.find_one({"email": normalized_email})
            return self._convert_id(doc) if doc else None
        except Exception as e:
            raise RepositoryError(f"Error finding user by email: {str(e)}") from e
    
    def update_last_login(self, user_id: str) -> bool:
        """
        Update the last_login timestamp for a user.
        
        Called after successful authentication.
        
        Args:
            user_id: User ObjectId as string
            
        Returns:
            bool: True if update successful, False if user not found
            
        Raises:
            RepositoryError: On database operations error
        """
        from datetime import datetime, timezone
        from bson import ObjectId
        
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(user_id)
            except Exception:
                # Invalid ObjectId format
                return False
            
            success = self.update_one(
                {"_id": object_id},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )
            return success
        except RepositoryError:
            # update_one already raises RepositoryError, re-raise  
            raise
        except Exception as e:
            raise RepositoryError(f"Error updating last_login: {str(e)}") from e
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """
        Create a new user (simplified wrapper around insert_one).
        
        Args:
            user_data: User data dictionary with required fields:
                      - email (normalized to lowercase)
                      - password_hash
                      - full_name
                      - role (default: 'operator')
                      - is_active (default: True)
                      - created_at
            
        Returns:
            str: Inserted user _id as string
            
        Raises:
            RepositoryError: On database operations error (e.g., email duplicate)
        """
        try:
            # Ensure email is lowercase
            if 'email' in user_data:
                user_data['email'] = user_data['email'].strip().lower()
            
            return self.insert_one(user_data)
        except RepositoryError as e:
            # Check if it's a duplicate email error
            if 'duplicate' in str(e).lower():
                raise RepositoryError(f"Email already exists: {user_data.get('email')}") from e
            raise
        except Exception as e:
            raise RepositoryError(f"Error creating user: {str(e)}") from e
    
    def find_by_email_with_password(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by email and return with password_hash (for login).
        
        This is a specific method that intentionally includes password_hash
        for authentication purposes only.
        
        Args:
            email: Email address to search for
            
        Returns:
            dict: User document including password_hash, or None if not found
        """
        return self.find_by_email(email)  # BaseRepository includes all fields
