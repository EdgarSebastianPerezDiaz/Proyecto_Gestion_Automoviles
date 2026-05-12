"""
Driver Domain Model

Defines the Driver entity, validation helpers, and serialization logic
for the freight transport platform.
"""

from typing import TypedDict
from datetime import datetime, timezone, timedelta
import re


class DriverDict(TypedDict, total=False):
    """Driver entity representation."""
    _id: str
    id_number: str  # Cédula (6-10 digits, normalized without formatting)
    first_name: str
    last_name: str
    phone: str
    address: str
    email: str | None
    license_number: str
    license_category: str  # C1, C2, C3, C4 (Colombian categories)
    license_expiry: datetime
    license_alert: bool  # True if license expires within 30 days
    license_expired: bool  # True if license_expiry < today
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Valid Colombian driver license categories
VALID_LICENSE_CATEGORIES = ["C1", "C2", "C3", "C4"]


def sanitize_id_number(id_number: str) -> str:
    """
    Normalize cédula (ID number) to standard format.
    
    Removes dots, dashes, and spaces, keeps only digits.
    
    Args:
        id_number: Raw ID number with possible formatting
        
    Returns:
        Normalized ID number (digits only)
        
    Raises:
        ValueError: If ID number doesn't contain valid digits
    """
    # Remove common formatting characters
    normalized = re.sub(r'[\.\-\s]', '', id_number)
    
    # Keep only digits
    if not re.match(r'^\d+$', normalized):
        raise ValueError("ID number must contain only digits after removing formatting")
    
    return normalized


def validate_id_number_format(id_number: str) -> bool:
    """
    Validate cédula format (6-10 digits).
    
    Args:
        id_number: Normalized ID number (digits only)
        
    Returns:
        True if valid format, False otherwise
    """
    return bool(re.match(r'^\d{6,10}$', id_number))


def validate_license_category(category: str) -> bool:
    """
    Validate license category against Colombian standards.
    
    Args:
        category: License category code
        
    Returns:
        True if valid category, False otherwise
    """
    return category in VALID_LICENSE_CATEGORIES


def calculate_license_status(license_expiry: datetime) -> tuple[bool, bool]:
    """
    Calculate license_alert and license_expired flags based on expiry date.
    
    - license_expired: True if license_expiry < today (UTC)
    - license_alert: True if expiry is within 30 days AND not yet expired
    
    Args:
        license_expiry: License expiration datetime (should be in UTC)
        
    Returns:
        Tuple of (license_alert, license_expired)
    """
    now = datetime.now(timezone.utc)
    days_until_expiry = (license_expiry.date() - now.date()).days
    
    license_expired = days_until_expiry < 0
    license_alert = 0 <= days_until_expiry <= 30 and not license_expired
    
    return license_alert, license_expired


def driver_to_dict(driver_doc: dict, include_expiry: bool = True) -> DriverDict:
    """
    Convert MongoDB driver document to DriverDict.
    
    Args:
        driver_doc: MongoDB driver document
        include_expiry: Whether to include expiry timestamp details
        
    Returns:
        DriverDict with all fields
    """
    return DriverDict(
        _id=str(driver_doc.get('_id', '')),
        id_number=driver_doc.get('id_number', ''),
        first_name=driver_doc.get('first_name', ''),
        last_name=driver_doc.get('last_name', ''),
        phone=driver_doc.get('phone', ''),
        address=driver_doc.get('address', ''),
        email=driver_doc.get('email'),
        license_number=driver_doc.get('license_number', ''),
        license_category=driver_doc.get('license_category', ''),
        license_expiry=driver_doc.get('license_expiry'),
        license_alert=driver_doc.get('license_alert', False),
        license_expired=driver_doc.get('license_expired', False),
        is_active=driver_doc.get('is_active', True),
        created_at=driver_doc.get('created_at'),
        updated_at=driver_doc.get('updated_at'),
    )


def driver_from_dict(data: dict) -> dict:
    """
    Convert input data to MongoDB driver document format.
    
    Handles timestamp creation and normalization.
    
    Args:
        data: Input driver data
        
    Returns:
        MongoDB document-ready dictionary
    """
    now = datetime.now()
    
    # Normalize ID number
    id_number = sanitize_id_number(data.get('id_number', ''))
    
    # Calculate license status
    license_expiry = data.get('license_expiry')
    if isinstance(license_expiry, str):
        license_expiry = datetime.fromisoformat(license_expiry)
    
    license_alert, license_expired = calculate_license_status(license_expiry)
    
    return {
        'id_number': id_number,
        'first_name': data.get('first_name', ''),
        'last_name': data.get('last_name', ''),
        'phone': data.get('phone', ''),
        'address': data.get('address', ''),
        'email': data.get('email'),
        'license_number': data.get('license_number', ''),
        'license_category': data.get('license_category', ''),
        'license_expiry': license_expiry,
        'license_alert': license_alert,
        'license_expired': license_expired,
        'is_active': data.get('is_active', True),
        'created_at': data.get('created_at', now),
        'updated_at': data.get('updated_at', now),
    }
