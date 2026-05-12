"""
Company domain model with type definitions and helper functions.
"""
from typing import TypedDict, Optional
from datetime import datetime, timezone
import re


class CompanyDict(TypedDict):
    """Type definition for Company entity."""
    
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


def company_to_dict(company: dict, include_timestamps: bool = True) -> dict:
    """
    Convert company document to response format.
    
    Args:
        company: Company document from database
        include_timestamps: Whether to include created_at and updated_at
        
    Returns:
        Company dictionary suitable for API responses
    """
    result = {
        "_id": company.get("_id"),
        "nit": company.get("nit"),
        "legal_name": company.get("legal_name"),
        "trade_name": company.get("trade_name"),
        "address": company.get("address"),
        "city": company.get("city"),
        "phone": company.get("phone"),
        "email": company.get("email"),
        "contact_name": company.get("contact_name"),
        "is_active": company.get("is_active", True),
    }
    
    if include_timestamps:
        result["created_at"] = company.get("created_at")
        result["updated_at"] = company.get("updated_at")
    
    return result


def company_from_dict(data: dict) -> dict:
    """
    Convert API input to company database format.
    
    Args:
        data: API request data
        
    Returns:
        Company document ready for database insertion
    """
    now = datetime.now(timezone.utc)
    
    return {
        "nit": data.get("nit"),
        "legal_name": data.get("legal_name"),
        "trade_name": data.get("trade_name"),
        "address": data.get("address"),
        "city": data.get("city"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "contact_name": data.get("contact_name"),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
