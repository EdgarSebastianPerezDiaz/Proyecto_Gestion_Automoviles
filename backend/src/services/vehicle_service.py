"""
Vehicle service - business logic layer for vehicle operations.
"""
from typing import Optional
from datetime import datetime, timezone

from src.repositories.vehicle_repository import VehicleRepository, RepositoryError
from src.domain.vehicle import (
    sanitize_plate,
    validate_plate_format,
    validate_vehicle_type,
    validate_status,
    vehicle_to_dict,
)
from src.infrastructure.sanitizer import sanitize_string


class VehicleError(Exception):
    """Base exception for vehicle service errors."""
    pass


class VehicleAlreadyExistsError(VehicleError):
    """Raised when attempting to create vehicle that already exists."""
    pass


class VehicleNotFoundError(VehicleError):
    """Raised when vehicle is not found."""
    pass


class VehicleValidationError(VehicleError):
    """Raised when vehicle data fails validation."""
    pass


class VehicleService:
    """
    Service for vehicle operations.
    Handles business logic, validation, and audit logging.
    """
    
    def __init__(self, vehicle_repository: VehicleRepository):
        """
        Initialize VehicleService.
        
        Args:
            vehicle_repository: Repository instance for vehicle data access
        """
        self.repository = vehicle_repository
    
    def _validate_vehicle_data(self, data: dict, is_update: bool = False) -> None:
        """
        Validate vehicle data.
        
        Args:
            data: Vehicle data to validate
            is_update: If True, skips some required field checks
            
        Raises:
            VehicleValidationError: If validation fails
        """
        if not is_update:
            # Required fields for creation
            required_fields = ["plate", "vehicle_type", "brand", "model_year", "capacity_tons", "company_id"]
            
            for field in required_fields:
                if not data.get(field):
                    raise VehicleValidationError(f"Missing required field: {field}")
        
        # Validate plate format if provided
        if data.get("plate"):
            if not validate_plate_format(data.get("plate", "")):
                raise VehicleValidationError(f"Invalid plate format: {data.get('plate')}")
        
        # Validate vehicle type if provided
        if data.get("vehicle_type"):
            if not validate_vehicle_type(data.get("vehicle_type", "")):
                raise VehicleValidationError(
                    f"Invalid vehicle type: {data.get('vehicle_type')}. "
                    f"Valid types: truck, trailer, van, platform, tanker, refrigerated"
                )
        
        # Validate model year if provided
        if data.get("model_year"):
            try:
                year = int(data.get("model_year", 0))
                if year < 1900 or year > datetime.now(timezone.utc).year + 1:
                    raise VehicleValidationError(f"Invalid model year: {year}")
            except (ValueError, TypeError):
                raise VehicleValidationError(f"Model year must be an integer")
        
        # Validate capacity_tons if provided
        if data.get("capacity_tons"):
            try:
                capacity = float(data.get("capacity_tons", 0))
                if capacity <= 0:
                    raise VehicleValidationError(f"Capacity must be positive")
            except (ValueError, TypeError):
                raise VehicleValidationError(f"Capacity must be a number")
        
        # Validate volume_m3 if provided
        if data.get("volume_m3"):
            try:
                volume = float(data.get("volume_m3", 0))
                if volume <= 0:
                    raise VehicleValidationError(f"Volume must be positive")
            except (ValueError, TypeError):
                raise VehicleValidationError(f"Volume must be a number")
        
        # Validate status if provided
        if data.get("status"):
            if not validate_status(data.get("status", "")):
                raise VehicleValidationError(
                    f"Invalid status: {data.get('status')}. "
                    f"Valid statuses: available, in_trip, inactive"
                )
    
    def create_vehicle(self, data: dict, user_id: str = None) -> dict:
        """
        Create a new vehicle.
        
        Args:
            data: Vehicle data with required fields
            user_id: User ID creating the vehicle (will be stored in created_by field)
            
        Returns:
            Created vehicle document with _id
            
        Raises:
            VehicleValidationError: If validation fails
            VehicleAlreadyExistsError: If vehicle with same plate exists
            VehicleError: If creation fails
        """
        try:
            # Validate data
            self._validate_vehicle_data(data)
            
            # Normalize and sanitize plate
            normalized_plate = sanitize_plate(data["plate"])
            
            # Check if vehicle with this plate already exists
            existing = self.repository.find_by_plate(normalized_plate)
            if existing:
                raise VehicleAlreadyExistsError(
                    f"Vehicle with plate {normalized_plate} already exists"
                )
            
            # Sanitize string fields
            vehicle_data = {
                "plate": normalized_plate,
                "vehicle_type": sanitize_string(data.get("vehicle_type", "")).lower().strip(),
                "brand": sanitize_string(data.get("brand", "")).strip(),
                "model_year": int(data.get("model_year", 0)),
                "capacity_tons": float(data.get("capacity_tons", 0)),
                "volume_m3": float(data.get("volume_m3")) if data.get("volume_m3") else None,
                "status": data.get("status", "available").lower(),
                "company_id": sanitize_string(data.get("company_id", "")).strip(),
                "soat_expiry": data.get("soat_expiry"),
                "tech_review_expiry": data.get("tech_review_expiry"),
                "is_active": True,
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            # Insert into database
            vehicle_id = self.repository.insert_one(vehicle_data)
            
            # Convert ObjectId to string
            vehicle_data["_id"] = vehicle_id
            
            return vehicle_data
        
        except VehicleValidationError:
            raise
        except VehicleAlreadyExistsError:
            raise
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error creating vehicle: {str(e)}") from e
    
    def get_vehicle(self, vehicle_id: str) -> Optional[dict]:
        """
        Get a vehicle by ID.
        
        Args:
            vehicle_id: Vehicle ID as string
            
        Returns:
            Vehicle document or None if not found
            
        Raises:
            VehicleError: If operation fails
        """
        try:
            return self.repository.find_by_id(vehicle_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error getting vehicle {vehicle_id}: {str(e)}") from e
    
    def get_vehicle_by_plate(self, plate: str) -> Optional[dict]:
        """
        Get a vehicle by plate.
        
        Args:
            plate: Vehicle plate
            
        Returns:
            Vehicle document or None if not found
            
        Raises:
            VehicleError: If operation fails
        """
        try:
            return self.repository.find_by_plate(plate)
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error getting vehicle by plate {plate}: {str(e)}") from e
    
    def list_vehicles(
        self,
        active_only: bool = True,
        status_filter: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
        user_id: Optional[str] = None
    ) -> list[dict]:
        """
        List vehicles with optional filtering.
        
        Args:
            active_only: If True, only return active vehicles
            status_filter: Filter by status ('available', 'in_trip', 'inactive')
            limit: Maximum number of results
            skip: Pagination offset
            user_id: If provided, filter by created_by (ownership-based)
            
        Returns:
            List of vehicle documents
            
        Raises:
            VehicleError: If operation fails
        """
        try:
            filter_dict = {}
            
            if active_only:
                filter_dict["is_active"] = True
            
            if status_filter:
                filter_dict["status"] = status_filter.lower()
            
            # Apply ownership filter if user_id provided
            if user_id:
                filter_dict["created_by"] = user_id
            
            return self.repository.find_many(
                filter_dict,
                limit=limit,
                skip=skip
            )
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error listing vehicles: {str(e)}") from e
    
    def update_vehicle(self, vehicle_id: str, data: dict) -> dict:
        """
        Update vehicle data.
        
        Args:
            vehicle_id: Vehicle ID as string
            data: Fields to update
            
        Returns:
            Updated vehicle document
            
        Raises:
            VehicleValidationError: If validation fails
            VehicleNotFoundError: If vehicle not found
            VehicleError: If operation fails
        """
        try:
            # Validate provided data
            self._validate_vehicle_data(data, is_update=True)
            
            # Get existing vehicle
            existing = self.repository.find_by_id(vehicle_id)
            if not existing:
                raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
            
            # If plate is being updated, check for duplicate
            if data.get("plate") and data["plate"] != existing.get("plate"):
                normalized_new_plate = sanitize_plate(data["plate"])
                duplicate = self.repository.find_by_plate(normalized_new_plate)
                if duplicate:
                    raise VehicleAlreadyExistsError(
                        f"Vehicle with plate {normalized_new_plate} already exists"
                    )
                data["plate"] = normalized_new_plate
            
            # Sanitize string fields
            update_data = {}
            if data.get("plate"):
                update_data["plate"] = sanitize_plate(data["plate"])
            if data.get("vehicle_type"):
                update_data["vehicle_type"] = sanitize_string(data.get("vehicle_type")).lower().strip()
            if data.get("brand"):
                update_data["brand"] = sanitize_string(data.get("brand")).strip()
            if data.get("model_year"):
                update_data["model_year"] = int(data.get("model_year"))
            if data.get("capacity_tons"):
                update_data["capacity_tons"] = float(data.get("capacity_tons"))
            if data.get("volume_m3"):
                update_data["volume_m3"] = float(data.get("volume_m3"))
            if data.get("status"):
                update_data["status"] = data.get("status").lower()
            if data.get("soat_expiry") is not None:
                update_data["soat_expiry"] = data.get("soat_expiry")
            if data.get("tech_review_expiry") is not None:
                update_data["tech_review_expiry"] = data.get("tech_review_expiry")
            
            # Update in database
            success = self.repository.update(vehicle_id, update_data)
            if not success:
                raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
            
            # Fetch and return updated vehicle
            updated = self.repository.find_by_id(vehicle_id)
            return updated
        
        except VehicleValidationError:
            raise
        except VehicleAlreadyExistsError:
            raise
        except VehicleNotFoundError:
            raise
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error updating vehicle {vehicle_id}: {str(e)}") from e
    
    def delete_vehicle(self, vehicle_id: str) -> bool:
        """
        Delete a vehicle (soft delete - sets is_active to False).
        
        Args:
            vehicle_id: Vehicle ID as string
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            VehicleError: If operation fails
        """
        try:
            return self.repository.soft_delete(vehicle_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error deleting vehicle {vehicle_id}: {str(e)}") from e
    
    def check_availability(self, vehicle_id: str) -> bool:
        """
        Check if a vehicle is available for trips.
        
        Available = status is 'available' AND is_active is True
        
        Args:
            vehicle_id: Vehicle ID as string
            
        Returns:
            True if available, False otherwise
            
        Raises:
            VehicleNotFoundError: If vehicle not found
            VehicleError: If operation fails
        """
        try:
            vehicle = self.repository.find_by_id(vehicle_id)
            if not vehicle:
                raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
            
            return (
                vehicle.get("status") == "available" and
                vehicle.get("is_active") is True
            )
        except VehicleNotFoundError:
            raise
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error checking vehicle availability {vehicle_id}: {str(e)}") from e
    
    def update_vehicle_status(self, vehicle_id: str, new_status: str) -> dict:
        """
        Update vehicle status.
        
        Args:
            vehicle_id: Vehicle ID as string
            new_status: New status ('available', 'in_trip', or 'inactive')
            
        Returns:
            Updated vehicle document
            
        Raises:
            VehicleValidationError: If status is invalid
            VehicleNotFoundError: If vehicle not found
            VehicleError: If operation fails
        """
        try:
            if not validate_status(new_status):
                raise VehicleValidationError(
                    f"Invalid status: {new_status}. "
                    f"Valid statuses: available, in_trip, inactive"
                )
            
            # Update status
            success = self.repository.update_status(vehicle_id, new_status.lower())
            if not success:
                raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
            
            # Fetch and return updated vehicle
            updated = self.repository.find_by_id(vehicle_id)
            return updated
        
        except VehicleValidationError:
            raise
        except VehicleNotFoundError:
            raise
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error updating vehicle status {vehicle_id}: {str(e)}") from e
    
    def get_expiring_documents(
        self,
        soat_days: int = 30,
        tech_days: int = 30
    ) -> dict:
        """
        Get vehicles with expiring SOAT and/or technical review documents.
        
        Args:
            soat_days: Days threshold for SOAT expiry (default 30)
            tech_days: Days threshold for tech review expiry (default 30)
            
        Returns:
            Dictionary with lists of vehicles and expiry information
            
        Raises:
            VehicleError: If operation fails
        """
        try:
            expiring_soat = self.repository.find_expiring_soat(soat_days)
            expiring_tech = self.repository.find_expiring_tech_review(tech_days)
            
            return {
                "soat_expiring": expiring_soat,
                "tech_review_expiring": expiring_tech,
                "soat_threshold_days": soat_days,
                "tech_threshold_days": tech_days,
            }
        except RepositoryError:
            raise
        except Exception as e:
            raise VehicleError(f"Error getting expiring documents: {str(e)}") from e
