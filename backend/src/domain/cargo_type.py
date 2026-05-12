"""
Cargo Types domain - catalog of cargo types with pricing information.
"""
from typing import TypedDict, Optional
from datetime import datetime
from decimal import Decimal


class CargoTypeDict(TypedDict):
    """Type definition for cargo type document."""
    _id: str
    name: str
    description: Optional[str]
    price_per_ton: float
    requires_special_permit: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


def sanitize_cargo_name(name: str) -> str:
    """
    Sanitize cargo type name.
    
    Args:
        name: Raw cargo name
        
    Returns:
        Sanitized name (trimmed, title case)
    """
    return name.strip().title() if name else ""


def validate_cargo_type_data(data: dict) -> tuple[bool, Optional[str]]:
    """
    Validate cargo type data format.
    
    Args:
        data: Cargo type data to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not data.get("name"):
        return False, "Name is required"
    
    if "price_per_ton" not in data:
        return False, "Price per ton is required"
    
    try:
        price = float(data["price_per_ton"])
        if price <= 0:
            return False, "Price per ton must be greater than 0"
    except (ValueError, TypeError):
        return False, "Price per ton must be a valid number"
    
    return True, None


def cargo_type_to_dict(cargo) -> dict:
    """Convert cargo type object to dictionary."""
    if isinstance(cargo, dict):
        return cargo
    return dict(cargo)


def cargo_type_from_dict(data: dict) -> CargoTypeDict:
    """Convert dictionary to CargoTypeDict."""
    return CargoTypeDict(**data)
