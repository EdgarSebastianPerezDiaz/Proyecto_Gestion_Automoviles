"""
Trip Statuses service - business logic layer for trip statuses.
"""
from src.repositories.trip_status_repository import TripStatusRepository
from src.domain.trip_status import (
    validate_status_code,
    validate_status_data,
    trip_status_to_dict,
    trip_status_from_dict
)


class TripStatusError(Exception):
    """Base exception for trip status service errors."""
    pass


class TripStatusNotFoundError(TripStatusError):
    """Raised when trip status is not found."""
    pass


class TripStatusValidationError(TripStatusError):
    """Raised when trip status data fails validation."""
    pass


class TripStatusInUseError(TripStatusError):
    """Raised when trip status is currently used in trips."""
    pass


class TripStatusAlreadyExistsError(TripStatusError):
    """Raised when attempting to create trip status that already exists."""
    pass


# Aliases for backward compatibility
ValidationError = TripStatusValidationError
StatusInUseError = TripStatusInUseError
AlreadyExistsError = TripStatusAlreadyExistsError


class TripStatusService:
    """
    Service layer for trip status business logic.
    Handles CRUD operations and validation.
    Trip statuses are typically immutable reference data.
    """
    
    def __init__(self, repository: TripStatusRepository, trips_collection=None):
        """
        Initialize TripStatusService.
        
        Args:
            repository: TripStatusRepository instance
            trips_collection: MongoDB collection for trips (used for deletion checks)
        """
        self.repository = repository
        self.trips_collection = trips_collection
    
    def create_trip_status(self, data: dict) -> dict:
        """
        Create a new trip status.
        
        Args:
            data: Status data (code, label, order, is_terminal)
            
        Returns:
            Created trip status document with _id
            
        Raises:
            TripStatusValidationError: If data validation fails
            TripStatusAlreadyExistsError: If code already exists
        """
        # Validate data
        is_valid, error_msg = validate_status_data(data)
        if not is_valid:
            raise TripStatusValidationError(error_msg)
        
        # Validate code format
        code = data.get("code", "").strip().lower()
        if not validate_status_code(code):
            raise TripStatusValidationError(
                "Status code must be lowercase alphanumeric with underscores only"
            )
        
        # Check if status with same code already exists
        if self.repository.check_code_exists(code):
            raise TripStatusAlreadyExistsError(f"Status code '{code}' already exists")
        
        # Prepare trip status record
        order = data.get("order")
        if order is None:
            order = self.repository.get_next_order_value()
        
        trip_status = {
            "code": code,
            "label": data.get("label", "").strip(),
            "order": int(order),
            "is_terminal": bool(data.get("is_terminal", False))
        }
        
        return self.repository.insert_one(trip_status)
    
    def get_trip_status(self, status_id: str) -> dict:
        """
        Get a specific trip status by ID.
        
        Args:
            status_id: Trip status ID as string
            
        Returns:
            Trip status document
            
        Raises:
            TripStatusNotFoundError: If trip status not found
        """
        trip_status = self.repository.find_by_id(status_id)
        if not trip_status:
            raise TripStatusNotFoundError(f"Trip status {status_id} not found")
        return trip_status
    
    def get_trip_status_by_code(self, code: str) -> dict:
        """
        Get trip status by code.
        
        Args:
            code: Status code
            
        Returns:
            Trip status document
            
        Raises:
            TripStatusNotFoundError: If trip status not found
            ValidationError: If code is invalid
        """
        if not code or len(code.strip()) == 0:
            raise TripStatusValidationError("Status code cannot be empty")
        
        trip_status = self.repository.find_by_code(code)
        if not trip_status:
            raise TripStatusNotFoundError(f"Trip status with code '{code}' not found")
        
        return trip_status
    
    def list_all_statuses(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """
        List all trip statuses ordered by sequence.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of trip status documents
        """
        return self.repository.find_all(skip=skip, limit=limit)
    
    def list_non_terminal_statuses(self) -> list[dict]:
        """
        List all non-terminal trip statuses (trip can continue).
        
        Returns:
            List of non-terminal trip status documents
        """
        return self.repository.find_non_terminal()
    
    def update_trip_status(self, status_id: str, data: dict) -> dict:
        """
        Update an existing trip status.
        
        Args:
            status_id: Trip status ID as string
            data: Data to update (label, order, is_terminal)
            
        Returns:
            Updated trip status document
            
        Raises:
            TripStatusNotFoundError: If trip status not found
            TripStatusValidationError: If data validation fails
            TripStatusAlreadyExistsError: If code already exists (for code changes)
        """
        # Verify trip status exists
        existing = self.repository.find_by_id(status_id)
        if not existing:
            raise TripStatusNotFoundError(f"Trip status {status_id} not found")
        
        # If code is being changed, verify uniqueness
        if "code" in data:
            new_code = data["code"].strip().lower()
            if new_code != existing.get("code"):
                if self.repository.check_code_exists(new_code):
                    raise TripStatusAlreadyExistsError(f"Status code '{new_code}' already exists")
        
        # Validate update data
        update_fields = {k: v for k, v in data.items() 
                        if k in ["code", "label", "order", "is_terminal"]}
        
        if update_fields:
            # Create full record for validation
            full_data = {**existing, **update_fields}
            is_valid, error_msg = validate_status_data(full_data)
            if not is_valid:
                raise TripStatusValidationError(error_msg)
        
        # Prepare update data with validation
        update_data = {}
        if "code" in data:
            code = data["code"].strip().lower()
            if not validate_status_code(code):
                raise TripStatusValidationError(
                    "Status code must be lowercase alphanumeric with underscores"
                )
            update_data["code"] = code
        
        if "label" in data:
            update_data["label"] = data["label"].strip()
        
        if "order" in data:
            update_data["order"] = int(data["order"])
        
        if "is_terminal" in data:
            update_data["is_terminal"] = bool(data["is_terminal"])
        
        if update_data:
            self.repository.update(status_id, update_data)
        
        # Return updated document
        return self.repository.find_by_id(status_id)
    
    def delete_trip_status(self, status_id: str) -> bool:
        """
        Delete a trip status.
        
        Args:
            status_id: Trip status ID as string
            
        Returns:
            True if successful
            
        Raises:
            TripStatusNotFoundError: If trip status not found
            StatusInUseError: If status is used in trips
        """
        existing = self.repository.find_by_id(status_id)
        if not existing:
            raise TripStatusNotFoundError(f"Trip status {status_id} not found")
        
        # Check if status is used in any trips (if trips collection available)
        if self.trips_collection:
            trip_count = self.trips_collection.count_documents({
                "$or": [
                    {"current_status": existing.get("code")},
                    {"status_history": {"$elemMatch": {"status": existing.get("code")}}}
                ]
            })
            if trip_count > 0:
                raise TripStatusInUseError(
                    f"Cannot delete status '{existing.get('code')}' - used in {trip_count} trip(s)"
                )
        
        return self.repository.delete_one(status_id)
    
    def count_all(self) -> int:
        """
        Count all trip statuses.
        
        Returns:
            Number of trip statuses
        """
        return self.repository.collection.count_documents({})
    
    def verify_status_exists(self, code: str) -> bool:
        """
        Verify that a trip status code exists.
        
        Args:
            code: Status code to verify
            
        Returns:
            True if status exists, False otherwise
        """
        return self.repository.find_by_code(code) is not None
