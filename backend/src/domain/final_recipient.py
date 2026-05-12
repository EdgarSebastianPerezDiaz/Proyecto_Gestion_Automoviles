"""
Final Recipients domain - represents destination companies/persons for shipments.
"""
from typing import TypedDict, Optional
from datetime import datetime


class FinalRecipientDict(TypedDict):
    """Type definition for final recipient document."""
    _id: str
    name: str
    address: str
    city: str
    contact_name: Optional[str]
    phone: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


def sanitize_recipient_name(name: str) -> str:
    """
    Sanitize recipient name.
    
    Args:
        name: Raw recipient name
        
    Returns:
        Sanitized name (uppercase, trimmed)
    """
    return name.strip().upper() if name else ""


def validate_recipient_data(data: dict) -> bool:
    """
    Validate recipient data format.
    
    Args:
        data: Recipient data to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["name", "address", "city", "phone", "email"]
    
    for field in required_fields:
        if not data.get(field):
            return False
    
    # Validate email
    email = data.get("email", "").strip().lower()
    if "@" not in email or "." not in email:
        return False
    
    # Validate phone - at least 7 digits
    phone = data.get("phone", "").replace(" ", "").replace("-", "")
    if not phone or len(phone) < 7:
        return False
    
    return True


def recipient_to_dict(recipient) -> dict:
    """Convert recipient object to dictionary."""
    if isinstance(recipient, dict):
        return recipient
    return dict(recipient)


def recipient_from_dict(data: dict) -> FinalRecipientDict:
    """Convert dictionary to FinalRecipientDict."""
    return FinalRecipientDict(**data)
