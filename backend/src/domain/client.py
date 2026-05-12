"""
Client domain model with type definitions and helper functions.

Clients are companies that request freight transport services.
"""
from typing import TypedDict, Optional
from datetime import datetime
import re


class ClientDict(TypedDict, total=False):
    """Type definition for Client entity."""
    
    _id: str
    nit: str
    legal_name: str
    trade_name: Optional[str]
    address: str
    city: str
    phone: str
    email: str
    contact_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


def sanitize_nit(nit: str) -> str:
    """
    Sanitize and normalize NIT format.
    
    Removes dots and dashes, keeps digits and verification digit.
    Converts "123.456.789-0" or "1234567890" to "123456789-0" format.
    
    Args:
        nit: NIT string (with or without formatting)
        
    Returns:
        Normalized NIT in "XXXXXXXXX-Y" format (9 digits + dash + 1 verification digit)
        
    Raises:
        ValueError: If NIT format is invalid
    """
    # Remove common formatting characters
    clean_nit = nit.replace('.', '').replace('-', '').replace(' ', '')
    
    # Validate: must be 10 digits
    if not re.match(r'^\d{10}$', clean_nit):
        raise ValueError(f"Invalid NIT format: {nit}. Expected 10 digits (with or without dashes/dots).")
    
    # Format as XXXXXXXXX-Y (9 digits + dash + 1 verification digit)
    return f"{clean_nit[:9]}-{clean_nit[9]}"


def validate_nit_format(nit: str) -> bool:
    """
    Validate NIT format (with or without formatting).
    
    Args:
        nit: NIT string to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Accept "XXXXXXXXX-Y" or "XXXXXXXXXX" format
    return bool(re.match(r'^(\d{9}-\d|\d{10})$', nit.replace('.', '')))


def client_to_dict(client: dict, include_timestamps: bool = True) -> dict:
    """
    Convert client document to response format.
    
    Args:
        client: Client document from database
        include_timestamps: Whether to include created_at and updated_at
        
    Returns:
        Client dictionary suitable for API responses
    """
    result = {
        "_id": client.get("_id"),
        "nit": client.get("nit"),
        "legal_name": client.get("legal_name"),
        "trade_name": client.get("trade_name"),
        "address": client.get("address"),
        "city": client.get("city"),
        "phone": client.get("phone"),
        "email": client.get("email"),
        "contact_name": client.get("contact_name"),
        "is_active": client.get("is_active", True),
    }
    
    if include_timestamps:
        result["created_at"] = client.get("created_at")
        result["updated_at"] = client.get("updated_at")
    
    return result


def client_from_dict(data: dict) -> dict:
    """
    Convert API input to client database format.
    
    Args:
        data: Raw API input
        
    Returns:
        Client data ready for database
    """
    # This is typically used by service layer for validation
    # Returns a dict that will be processed further
    return {k: v for k, v in data.items() if v is not None}
