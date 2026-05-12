"""
Vehicle Domain Model

Defines the Vehicle entity, validation helpers, and serialization logic
for the freight transport platform.
"""

from typing import TypedDict, Optional, Literal
from datetime import datetime
import re


class VehicleDict(TypedDict, total=False):
    """Vehicle entity representation."""
    _id: str
    plate: str  # Uppercase alphanumeric (e.g., ABC123)
    vehicle_type: str  # truck, trailer, van, etc.
    brand: str  # Vehicle manufacturer
    model_year: int  # Year of manufacture
    capacity_tons: float  # Maximum cargo capacity in metric tons
    volume_m3: Optional[float]  # Cargo volume in cubic meters (optional)
    status: Literal['available', 'in_trip', 'inactive']  # Current status
    company_id: str  # Reference to owning company
    soat_expiry: Optional[datetime]  # SOAT (insurance) expiration date
    tech_review_expiry: Optional[datetime]  # Technical review expiration date
    is_active: bool  # Soft delete flag
    created_at: datetime
    updated_at: datetime


def sanitize_plate(plate: str) -> str:
    """
    Normalize vehicle plate to uppercase.
    
    Accepts any alphanumeric format after removing spaces and dashes.
    Converts to uppercase for standard format.
    
    Args:
        plate: Raw plate string (any case, with optional formatting)
        
    Returns:
        Normalized plate (uppercase alphanumeric)
        
    Raises:
        ValueError: If plate format is invalid (not alphanumeric)
    """
    # Remove common formatting characters
    clean_plate = re.sub(r'[\s\-]', '', plate)
    
    # Validate: must be alphanumeric only
    if not re.match(r'^[a-zA-Z0-9]+$', clean_plate):
        raise ValueError(f"Invalid plate format: {plate}. Expected alphanumeric characters only.")
    
    # Convert to uppercase
    return clean_plate.upper()


def validate_plate_format(plate: str) -> bool:
    """
    Validate plate format (alphanumeric, 3-8 characters).
    
    Args:
        plate: Plate string to validate (can include spaces/dashes)
        
    Returns:
        True if valid format, False otherwise
    """
    clean_plate = re.sub(r'[\s\-]', '', plate)
    return bool(re.match(r'^[a-zA-Z0-9]{3,8}$', clean_plate))


def validate_vehicle_type(vehicle_type: str) -> bool:
    """
    Validate vehicle type against known types.
    
    Args:
        vehicle_type: Vehicle type code
        
    Returns:
        True if valid type, False otherwise
    """
    valid_types = {'truck', 'trailer', 'van', 'platform', 'tanker', 'refrigerated'}
    return vehicle_type.lower() in valid_types


def validate_status(status: str) -> bool:
    """
    Validate vehicle status.
    
    Args:
        status: Status string
        
    Returns:
        True if valid status, False otherwise
    """
    valid_statuses = {'available', 'in_trip', 'inactive'}
    return status.lower() in valid_statuses


def calculate_document_expiry_alerts(
    soat_expiry: Optional[datetime],
    tech_review_expiry: Optional[datetime],
    days_threshold: int = 30
) -> dict:
    """
    Calculate document expiry alert flags.
    
    Args:
        soat_expiry: SOAT expiration datetime
        tech_review_expiry: Tech review expiration datetime
        days_threshold: Days threshold for alerts
        
    Returns:
        Dictionary with alert flags for soat and tech_review
    """
    today = datetime.now()
    from datetime import timedelta
    threshold_date = today + timedelta(days=days_threshold)
    
    alerts = {
        'soat_expiring': False,
        'soat_expired': False,
        'tech_review_expiring': False,
        'tech_review_expired': False,
    }
    
    if soat_expiry:
        if soat_expiry < today:
            alerts['soat_expired'] = True
        elif soat_expiry <= threshold_date:
            alerts['soat_expiring'] = True
    
    if tech_review_expiry:
        if tech_review_expiry < today:
            alerts['tech_review_expired'] = True
        elif tech_review_expiry <= threshold_date:
            alerts['tech_review_expiring'] = True
    
    return alerts


def vehicle_to_dict(vehicle: dict, include_timestamps: bool = True) -> dict:
    """
    Convert vehicle document to response format.
    
    Args:
        vehicle: Vehicle document from database
        include_timestamps: Whether to include created_at and updated_at
        
    Returns:
        Vehicle dictionary suitable for API responses
    """
    result = {
        "_id": vehicle.get("_id"),
        "plate": vehicle.get("plate"),
        "vehicle_type": vehicle.get("vehicle_type"),
        "brand": vehicle.get("brand"),
        "model_year": vehicle.get("model_year"),
        "capacity_tons": vehicle.get("capacity_tons"),
        "volume_m3": vehicle.get("volume_m3"),
        "status": vehicle.get("status", "available"),
        "company_id": vehicle.get("company_id"),
        "soat_expiry": vehicle.get("soat_expiry"),
        "tech_review_expiry": vehicle.get("tech_review_expiry"),
        "is_active": vehicle.get("is_active", True),
    }
    
    if include_timestamps:
        result["created_at"] = vehicle.get("created_at")
        result["updated_at"] = vehicle.get("updated_at")
    
    return result


def vehicle_from_dict(data: dict) -> dict:
    """
    Convert API input to vehicle database format.
    
    Args:
        data: Raw API input
        
    Returns:
        Vehicle data ready for database
    """
    # This is typically used by service layer for validation
    # Returns a dict that will be processed further
    return {k: v for k, v in data.items() if v is not None}
