"""
Trip repository - data access layer for trip entities.
"""
from typing import Optional, List
from datetime import datetime, timezone
from bson.objectid import ObjectId

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


class TripRepository(BaseRepository):
    """
    Repository for Trip entity operations.
    Extends BaseRepository with trip-specific queries.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize TripRepository.
        
        Args:
            connection: MongoDBConnection instance
        """
        super().__init__('trips', connection)
    
    def find_by_status(self, status_id: str, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find trips by status.
        
        Args:
            status_id: Trip status ID
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of trip documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"status_id": status_id},
                limit=limit,
                skip=skip,
                sort=[("departure_date", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding trips by status {status_id}: {str(e)}")
    
    def find_active_trips(self, non_terminal_status_ids: list[str], limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Find all active trips (not terminal status).
        
        Args:
            non_terminal_status_ids: List of non-terminal status IDs
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of active trip documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"status_id": {"$in": non_terminal_status_ids}},
                limit=limit,
                skip=skip,
                sort=[("departure_date", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding active trips: {str(e)}")
    
    def update_status(self, trip_id: str, new_status_id: str, additional_updates: dict = None) -> bool:
        """
        Update trip status and other fields.
        
        Args:
            trip_id: Trip ID as string
            new_status_id: New status ID
            additional_updates: Additional fields to update
            
        Returns:
            True if successful, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            object_id = ObjectId(trip_id)
            update_data = {
                "status_id": new_status_id,
                "updated_at": datetime.now(timezone.utc)
            }
            if additional_updates:
                update_data.update(additional_updates)
            
            return self.update_one({"_id": object_id}, {"$set": update_data})
        except Exception as e:
            raise RepositoryError(f"Error updating trip status: {str(e)}")
    
    def add_pdf_urls(self, trip_id: str, doc_type: str, s3_url: str) -> bool:
        """
        Add PDF URL to trip documents.
        
        Args:
            trip_id: Trip ID as string
            doc_type: Document type (order_pdf, manifest_pdf, cumplido_pdf, invoice_pdf)
            s3_url: S3 URL of uploaded PDF
            
        Returns:
            True if successful
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            object_id = ObjectId(trip_id)
            update_field = f"documents.{doc_type}"
            
            return self.update_one(
                {"_id": object_id},
                {
                    "$set": {
                        update_field: s3_url,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        except Exception as e:
            raise RepositoryError(f"Error adding PDF URL to trip: {str(e)}")
    
    def get_trips_by_client(self, client_id: str, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Get all trips for a client.
        
        Args:
            client_id: Client ID
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of trip documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"client_id": client_id},
                limit=limit,
                skip=skip,
                sort=[("departure_date", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding trips for client {client_id}: {str(e)}")
    
    def get_trips_by_vehicle(self, vehicle_id: str, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Get all trips for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of trip documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"vehicle_id": vehicle_id},
                limit=limit,
                skip=skip,
                sort=[("departure_date", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding trips for vehicle {vehicle_id}: {str(e)}")
    
    def get_trips_by_driver(self, driver_id: str, limit: int = 100, skip: int = 0) -> list[dict]:
        """
        Get all trips for a driver.
        
        Args:
            driver_id: Driver ID
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of trip documents
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            return self.find_many(
                {"driver_id": driver_id},
                limit=limit,
                skip=skip,
                sort=[("departure_date", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding trips for driver {driver_id}: {str(e)}")
    
    def find_by_user(self, user_id: str, limit: int = 100, skip: int = 0, filters: dict = None) -> list[dict]:
        """
        Find trips created by a specific user (ownership-based filtering).
        
        Args:
            user_id: User ID (owner of the trips)
            limit: Maximum results
            skip: Pagination offset
            filters: Additional filters to apply (will be combined with created_by filter)
            
        Returns:
            List of trip documents created by the user
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Base filter for ownership
            query = {"created_by": user_id}
            
            # Add additional filters if provided
            if filters:
                query.update(filters)
            
            return self.find_many(
                query,
                limit=limit,
                skip=skip,
                sort=[("departure_date", -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding trips for user {user_id}: {str(e)}")
