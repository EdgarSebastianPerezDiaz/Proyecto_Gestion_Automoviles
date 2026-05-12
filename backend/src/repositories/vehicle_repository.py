"""
Vehicle repository - data access layer for vehicle entities.
"""
from typing import Optional
from datetime import datetime, timezone
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection
from src.domain.vehicle import sanitize_plate


class VehicleRepository(BaseRepository):
    """
    Repository for Vehicle entity operations.
    Extends BaseRepository with vehicle-specific queries.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize VehicleRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('vehicles', connection)
    
    def find_by_plate(self, plate: str) -> Optional[dict]:
        """
        Find vehicle by plate (normalized).
        
        Args:
            plate: Vehicle plate (will be normalized to uppercase)
            
        Returns:
            Vehicle document or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            normalized_plate = sanitize_plate(plate)
            return self.find_one({"plate": normalized_plate})
        except Exception as e:
            raise RepositoryError(f"Error finding vehicle by plate {plate}: {str(e)}")
    
    def find_by_company(self, company_id: str, active_only: bool = True) -> list[dict]:
        """
        Find all vehicles for a company.
        
        Args:
            company_id: Company ID
            active_only: If True, only return active vehicles
            
        Returns:
            List of vehicle documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            filter_dict = {"company_id": company_id}
            if active_only:
                filter_dict["is_active"] = True
            
            return self.find_many(filter_dict)
        except Exception as e:
            raise RepositoryError(f"Error finding vehicles for company {company_id}: {str(e)}")
    
    def find_available(self, limit: int = 100) -> list[dict]:
        """
        Find all available vehicles.
        
        Available = status is 'available' AND is_active is True
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of available vehicle documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"status": "available", "is_active": True},
                limit=limit
            )
        except Exception as e:
            raise RepositoryError(f"Error finding available vehicles: {str(e)}")
    
    def update_status(self, vehicle_id: str, new_status: str) -> bool:
        """
        Update vehicle status.
        
        Args:
            vehicle_id: Vehicle ID as string
            new_status: New status ('available', 'in_trip', or 'inactive')
            
        Returns:
            True if updated successfully, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(vehicle_id)
            except Exception:
                # Invalid ObjectId format
                return False
            
            return self.update_one(
                {"_id": object_id},
                {"$set": {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError(f"Error updating vehicle status {vehicle_id}: {str(e)}")
    
    def soft_delete(self, vehicle_id: str) -> bool:
        """
        Soft delete a vehicle (sets is_active to False).
        
        Args:
            vehicle_id: Vehicle ID as string
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(vehicle_id)
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
            raise RepositoryError(f"Error soft-deleting vehicle {vehicle_id}: {str(e)}")
    
    def find_expiring_soat(self, days_threshold: int = 30) -> list[dict]:
        """
        Find vehicles with SOAT expiring within threshold days.
        
        Args:
            days_threshold: Number of days to check ahead (default 30)
            
        Returns:
            List of vehicle documents with expiring SOAT
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            from datetime import datetime, timezone, timedelta
            today = datetime.now(timezone.utc)
            threshold_date = today + timedelta(days=days_threshold)
            
            return self.find_many({
                "soat_expiry": {
                    "$gte": today,
                    "$lte": threshold_date
                },
                "is_active": True
            })
        except Exception as e:
            raise RepositoryError(f"Error finding vehicles with expiring SOAT: {str(e)}")
    
    def find_expiring_tech_review(self, days_threshold: int = 30) -> list[dict]:
        """
        Find vehicles with technical review expiring within threshold days.
        
        Args:
            days_threshold: Number of days to check ahead (default 30)
            
        Returns:
            List of vehicle documents with expiring tech review
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            from datetime import datetime, timezone, timedelta
            today = datetime.now(timezone.utc)
            threshold_date = today + timedelta(days=days_threshold)
            
            return self.find_many({
                "tech_review_expiry": {
                    "$gte": today,
                    "$lte": threshold_date
                },
                "is_active": True
            })
        except Exception as e:
            raise RepositoryError(f"Error finding vehicles with expiring tech review: {str(e)}")
    
    def update(self, vehicle_id: str, data: dict) -> bool:
        """
        Update vehicle data.
        
        Args:
            vehicle_id: Vehicle ID as string
            data: Fields to update (will add updated_at timestamp)
            
        Returns:
            True if updated successfully, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Convert string ID to ObjectId for query
            try:
                object_id = ObjectId(vehicle_id)
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
            raise RepositoryError(f"Error updating vehicle {vehicle_id}: {str(e)}")

    def find_by_user(self, user_id: str, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find vehicles created by a specific user (ownership-based filtering).
        
        Args:
            user_id: User ID (creator/owner of the vehicles)
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of vehicle documents created by the user
            
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
            raise RepositoryError(f"Error finding vehicles for user {user_id}: {str(e)}")
