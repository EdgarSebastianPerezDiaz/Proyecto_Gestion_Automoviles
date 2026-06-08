"""
Driver Repository

Data access layer for driver entities.
Extends BaseRepository with driver-specific queries.
"""

from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from src.repositories.base_repository import BaseRepository
from src.infrastructure.database import MongoDBConnection
from src.domain.driver import calculate_license_status


class DriverRepository(BaseRepository):
    """
    Repository for driver data access.
    
    Provides CRUD operations and driver-specific queries.
    Extends BaseRepository for common functionality.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize driver repository.
        
        Args:
            connection: MongoDBConnection singleton instance
        """
        super().__init__('drivers', connection)
    
    def find_by_id_number(self, id_number: str) -> Optional[dict]:
        """
        Find driver by cédula (ID number).
        
        Args:
            id_number: Normalized ID number (digits only)
            
        Returns:
            Driver document or None if not found
        """
        collection = self.connection.get_collection(self.collection_name)
        return collection.find_one({'id_number': id_number})
    
    def find_active(self, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find all active drivers with pagination.
        
        Args:
            limit: Maximum number of results (default 100, max 1000)
            skip: Number of results to skip
            
        Returns:
            List of active driver documents
        """
        # Enforce max limit
        limit = min(limit, 1000)
        
        collection = self.connection.get_collection(self.collection_name)
        return list(
            collection.find({'is_active': True})
            .limit(limit)
            .skip(skip)
        )
    
    def find_license_alert(self, limit: int = 100) -> list[dict]:
        """
        Find drivers with license expiring within 30 days.
        
        License alert is True when expiry is within 30 days but not expired.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of drivers with license alerts
        """
        limit = min(limit, 1000)
        
        collection = self.connection.get_collection(self.collection_name)
        return list(
            collection.find({
                'license_alert': True,
                'license_expired': False,
                'is_active': True
            })
            .limit(limit)
        )
    
    def find_expired(self, limit: int = 100) -> list[dict]:
        """
        Find drivers with expired licenses.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of drivers with expired licenses
        """
        limit = min(limit, 1000)
        
        collection = self.connection.get_collection(self.collection_name)
        return list(
            collection.find({'license_expired': True})
            .limit(limit)
        )
    
    def soft_delete(self, driver_id: str) -> bool:
        """
        Soft delete driver (set is_active to False).
        
        Args:
            driver_id: Driver ObjectId as string
            
        Returns:
            True if updated, False if not found
        """
        collection = self.connection.get_collection(self.collection_name)
        
        try:
            driver_oid = ObjectId(driver_id)
        except Exception:
            return False
        
        result = collection.update_one(
            {'_id': driver_oid},
            {'$set': {
                'is_active': False,
                'updated_at': datetime.now(timezone.utc)
            }}
        )
        
        return result.modified_count > 0
    
    def update_license_status(self, driver_id: str) -> bool:
        """
        Recalculate license_alert and license_expired based on current date.
        
        Called when license expiry changes or periodically to update status.
        
        Args:
            driver_id: Driver ObjectId as string
            
        Returns:
            True if updated, False if not found or no changes needed
        """
        # Get current driver to get license_expiry
        driver = self.find_by_id(driver_id)
        if not driver:
            return False
        
        license_expiry = driver.get('license_expiry')
        if not license_expiry:
            return False
        
        # Handle both datetime and string formats
        if isinstance(license_expiry, str):
            license_expiry = datetime.fromisoformat(license_expiry)
        
        # Calculate new status
        license_alert, license_expired = calculate_license_status(license_expiry)

        # Use matched_count (not modified_count) so the method returns True
        # even when the calculated status is identical to the stored values.
        collection = self.connection.get_collection(self.collection_name)
        result = collection.update_one(
            {'_id': ObjectId(driver_id)},
            {'$set': {
                'license_alert': license_alert,
                'license_expired': license_expired,
                'updated_at': datetime.now(timezone.utc)
            }}
        )
        return result.matched_count > 0
    
    def get_available_drivers(self) -> list[dict]:
        """
        Get drivers available for assignment to trips.
        
        Criteria: active, license not expired.
        
        Returns:
            List of available drivers
        """
        collection = self.connection.get_collection(self.collection_name)
        return list(
            collection.find({
                'is_active': True,
                'license_expired': False
            })
        )
    
    def find_many(self, filter_dict: dict, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find multiple drivers matching filter criteria.
        
        Args:
            filter_dict: MongoDB filter dictionary
            limit: Maximum results (max 1000)
            skip: Results to skip
            
        Returns:
            List of driver documents
        """
        limit = min(limit, 1000)
        collection = self.connection.get_collection(self.collection_name)
        
        sanitized_filter = self._sanitize_filter(filter_dict)
        return list(
            collection.find(sanitized_filter)
            .limit(limit)
            .skip(skip)
        )
    
    def update(self, driver_id: str, data: dict) -> bool:
        """
        Update driver document.
        
        Args:
            driver_id: Driver ObjectId as string
            data: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        collection = self.connection.get_collection(self.collection_name)
        
        try:
            driver_oid = ObjectId(driver_id)
        except Exception:
            return False
        
        # Add updated_at timestamp
        update_data = dict(data)
        update_data['updated_at'] = datetime.now(timezone.utc)
        
        result = collection.update_one(
            {'_id': driver_oid},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def find_by_email(self, email: str) -> Optional[dict]:
        """
        Find driver by email (case-insensitive).
        
        Args:
            email: Driver email address
            
        Returns:
            Driver document or None
        """
        collection = self.connection.get_collection(self.collection_name)
        return collection.find_one({'email': {'$regex': f'^{email}$', '$options': 'i'}})

    def find_by_user(self, user_id: str, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find drivers created by a specific user (ownership-based filtering).
        
        Args:
            user_id: User ID (creator/owner of the drivers)
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of driver documents created by the user
        """
        try:
            collection = self.connection.get_collection(self.collection_name)
            return list(collection.find(
                {'created_by': user_id}
            ).sort('created_at', -1).limit(limit).skip(skip))
        except Exception as e:
            self.logger.error(f"Error finding drivers for user {user_id}: {str(e)}")
            return []

