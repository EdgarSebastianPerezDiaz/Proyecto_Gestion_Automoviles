"""
Driver Service

Business logic layer for driver operations.
Handles validation, sanitization, and coordination between repositories.
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from src.repositories.driver_repository import DriverRepository
from src.domain.driver import (
    sanitize_id_number,
    validate_id_number_format,
    validate_license_category,
    calculate_license_status,
    driver_from_dict
)
from src.infrastructure.sanitizer import sanitize_string


class DriverError(Exception):
    """Base exception for driver service."""
    pass


class DriverValidationError(DriverError):
    """Validation error for driver data."""
    pass


class DriverNotFoundError(DriverError):
    """Driver not found error."""
    pass


class DriverAlreadyExistsError(DriverError):
    """Driver already exists error."""
    pass


class DriverService:
    """
    Service for driver business logic.
    
    Validates driver data, handles creation/update/deletion,
    and provides license status queries.
    """
    
    def __init__(self, driver_repository: DriverRepository):
        """
        Initialize driver service.
        
        Args:
            driver_repository: DriverRepository instance for data access
        """
        self.repository = driver_repository
    
    def _validate_driver_data(self, data: dict) -> None:
        """
        Validate driver input data.
        
        Checks for required fields, format validity, and business rules.
        
        Args:
            data: Driver data to validate
            
        Raises:
            DriverValidationError: If validation fails
        """
        required_fields = [
            'id_number',
            'first_name',
            'last_name',
            'phone',
            'address',
            'license_number',
            'license_category',
            'license_expiry'
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                raise DriverValidationError(f"Missing required field: {field}")
        
        # Validate ID number format
        try:
            normalized_id = sanitize_id_number(data['id_number'])
            if not validate_id_number_format(normalized_id):
                raise DriverValidationError(
                    "ID number must be 6-10 digits (cedula format)"
                )
        except ValueError as e:
            raise DriverValidationError(f"Invalid ID number format: {str(e)}")
        
        # Validate license category
        if not validate_license_category(data['license_category']):
            raise DriverValidationError(
                f"Invalid license category. Must be one of: C1, C2, C3, C4"
            )
        
        # Validate license expiry is in the future
        try:
            if isinstance(data['license_expiry'], str):
                expiry = datetime.fromisoformat(data['license_expiry'])
            else:
                expiry = data['license_expiry']
            
            if expiry <= datetime.now():
                raise DriverValidationError(
                    "License expiry date must be in the future"
                )
        except (ValueError, TypeError) as e:
            raise DriverValidationError(f"Invalid license expiry date: {str(e)}")
        
        # Validate phone format (basic: must have digits)
        if not any(c.isdigit() for c in data['phone']):
            raise DriverValidationError("Phone number must contain at least one digit")
        
        # Validate email if provided
        if data.get('email'):
            email = data['email'].strip()
            if '@' not in email or '.' not in email:
                raise DriverValidationError("Invalid email format")
    
    def _log_operation(self, operation: str, driver_id: str, details: str = '') -> None:
        """
        Log driver operation for audit trail.
        
        Currently prints to console; can be extended to write to audit_log collection.
        
        Args:
            operation: Operation type (create, update, delete, etc.)
            driver_id: Driver ID involved
            details: Additional operation details
        """
        timestamp = datetime.now().isoformat()
        message = f"[{timestamp}] Driver {operation}: {driver_id}"
        if details:
            message += f" - {details}"
        print(message)
    
    def create_driver(self, data: dict, user_id: str = None) -> dict:
        """
        Create a new driver.
        
        Args:
            data: Driver data
            user_id: User ID creating the driver (will be stored in created_by field)
            
        Returns:
            Created driver document with _id
            
        Raises:
            DriverValidationError: If validation fails
            DriverAlreadyExistsError: If driver with same ID number exists
        """
        # Validate input
        self._validate_driver_data(data)
        
        # Normalize ID number
        normalized_id = sanitize_id_number(data['id_number'])
        
        # Check uniqueness
        existing = self.repository.find_by_id_number(normalized_id)
        if existing:
            raise DriverAlreadyExistsError(
                f"Driver with ID number {normalized_id} already exists"
            )
        
        # Sanitize string fields
        sanitized_data = {
            **data,
            'id_number': normalized_id,
            'first_name': sanitize_string(data['first_name']),
            'last_name': sanitize_string(data['last_name']),
            'phone': sanitize_string(data['phone']),
            'address': sanitize_string(data['address']),
            'email': sanitize_string(data.get('email', '')).lower() if data.get('email') else None,
            'license_number': sanitize_string(data['license_number']),
            'license_category': data['license_category'].upper(),
        }
        
        # Convert to storable format (calculates license status)
        driver_doc = driver_from_dict(sanitized_data)
        
        # Add ownership tracking
        driver_doc['created_by'] = user_id
        driver_doc['created_at'] = datetime.now(timezone.utc)
        driver_doc['updated_at'] = datetime.now(timezone.utc)
        
        # Create in repository
        driver_id = self.repository.insert_one(driver_doc)
        
        self._log_operation('create', driver_id, f"ID: {normalized_id}")
        
        return {
            **driver_doc,
            '_id': driver_id
        }
    
    def get_driver(self, driver_id: str) -> Optional[dict]:
        """
        Get driver by ID.
        
        Args:
            driver_id: Driver ObjectId as string
            
        Returns:
            Driver document or None if not found
        """
        try:
            driver = self.repository.find_by_id(driver_id)
            if driver:
                driver['_id'] = str(driver['_id'])
            return driver
        except Exception:
            return None
    
    def get_driver_by_id_number(self, id_number: str) -> Optional[dict]:
        """
        Get driver by cédula (ID number).
        
        Args:
            id_number: Raw or normalized ID number
            
        Returns:
            Driver document or None
        """
        try:
            normalized_id = sanitize_id_number(id_number)
            driver = self.repository.find_by_id_number(normalized_id)
            if driver:
                driver['_id'] = str(driver['_id'])
            return driver
        except Exception:
            return None
    
    def list_drivers(
        self,
        active_only: bool = True,
        include_expired: bool = False,
        limit: int = 100,
        skip: int = 0
    ) -> list[dict]:
        """
        List drivers with optional filtering.
        
        Args:
            active_only: Only return active drivers (default True)
            include_expired: Include drivers with expired licenses (default False)
            limit: Maximum results
            skip: Results to skip
            
        Returns:
            List of driver documents
        """
        filter_dict = {}
        
        if active_only:
            filter_dict['is_active'] = True
        
        if not include_expired:
            filter_dict['license_expired'] = False
        
        drivers = self.repository.find_many(filter_dict, limit=limit, skip=skip)
        
        # Ensure _id is string
        for driver in drivers:
            if '_id' in driver:
                driver['_id'] = str(driver['_id'])
        
        return drivers
    
    def update_driver(self, driver_id: str, data: dict) -> dict:
        """
        Update driver information.
        
        Recalculates license status if expiry date changes.
        
        Args:
            driver_id: Driver ObjectId as string
            data: Fields to update
            
        Returns:
            Updated driver document
            
        Raises:
            DriverNotFoundError: If driver not found
            DriverValidationError: If validation fails
        """
        # Check driver exists
        existing = self.get_driver(driver_id)
        if not existing:
            raise DriverNotFoundError(f"Driver {driver_id} not found")
        
        # Validate if changing ID number
        if 'id_number' in data:
            try:
                normalized_id = sanitize_id_number(data['id_number'])
                if normalized_id != existing['id_number']:
                    # Check uniqueness of new ID
                    conflict = self.repository.find_by_id_number(normalized_id)
                    if conflict and str(conflict['_id']) != driver_id:
                        raise DriverAlreadyExistsError(
                            f"ID number {normalized_id} already in use"
                        )
            except ValueError as e:
                raise DriverValidationError(f"Invalid ID number: {str(e)}")
        
        # Validate license category if changing
        if 'license_category' in data:
            if not validate_license_category(data['license_category']):
                raise DriverValidationError(
                    "Invalid license category. Must be one of: C1, C2, C3, C4"
                )
        
        # Sanitize string fields
        update_data = {}
        for key, value in data.items():
            if key in ['first_name', 'last_name', 'phone', 'address', 'license_number']:
                update_data[key] = sanitize_string(value) if value else value
            elif key == 'email':
                update_data[key] = sanitize_string(value).lower() if value else None
            elif key == 'license_category':
                update_data[key] = value.upper()
            elif key == 'id_number':
                update_data[key] = sanitize_id_number(value)
            else:
                update_data[key] = value
        
        # If license_expiry changed, recalculate status
        if 'license_expiry' in update_data:
            expiry = update_data['license_expiry']
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry)
            license_alert, license_expired = calculate_license_status(expiry)
            update_data['license_alert'] = license_alert
            update_data['license_expired'] = license_expired
        
        # Update in repository
        self.repository.update(driver_id, update_data)
        
        self._log_operation('update', driver_id, f"Fields: {list(data.keys())}")
        
        # Return updated driver
        updated = self.get_driver(driver_id)
        if not updated:
            raise DriverNotFoundError("Failed to retrieve updated driver")
        
        return updated
    
    def delete_driver(self, driver_id: str) -> bool:
        """
        Delete driver (soft delete - sets is_active to False).
        
        Args:
            driver_id: Driver ObjectId as string
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DriverNotFoundError: If driver not found
        """
        # Check exists first
        if not self.get_driver(driver_id):
            raise DriverNotFoundError(f"Driver {driver_id} not found")
        
        success = self.repository.soft_delete(driver_id)
        
        if success:
            self._log_operation('delete', driver_id, "Soft delete")
        
        return success
    
    def check_license_valid(self, driver_id: str) -> bool:
        """
        Check if driver's license is valid (not expired).
        
        Args:
            driver_id: Driver ObjectId as string
            
        Returns:
            True if license is valid, False otherwise
        """
        driver = self.get_driver(driver_id)
        if not driver:
            return False
        
        return not driver.get('license_expired', True)
    
    def get_expiring_soon(self, days_threshold: int = 30) -> list[dict]:
        """
        Get drivers with licenses expiring soon (within threshold).
        
        Args:
            days_threshold: Days until expiry to consider "soon" (default 30)
            
        Returns:
            List of drivers with expiring licenses
        """
        drivers = self.repository.find_license_alert(limit=1000)
        
        # Filter by threshold
        cutoff_date = datetime.now() + timedelta(days=days_threshold)
        result = []
        
        for driver in drivers:
            license_expiry = driver.get('license_expiry')
            if license_expiry and license_expiry <= cutoff_date:
                driver['_id'] = str(driver['_id'])
                result.append(driver)
        
        return result
