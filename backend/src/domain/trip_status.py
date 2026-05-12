"""
Trip Statuses domain - catalog of trip statuses for state machine.
"""
from typing import TypedDict


class TripStatusDict(TypedDict):
    """Type definition for trip status document."""
    _id: str
    code: str
    label: str
    order: int
    is_terminal: bool


# Standard trip status codes
TRIP_STATUS_SCHEDULED = "scheduled"
TRIP_STATUS_IN_TRANSIT = "in_transit"
TRIP_STATUS_DELIVERED = "delivered"
TRIP_STATUS_CANCELLED = "cancelled"


def validate_status_code(code: str) -> bool:
    """
    Validate trip status code format.
    
    Args:
        code: Status code to validate
        
    Returns:
        True if valid (alphanumeric + underscore), False otherwise
    """
    if not code:
        return False
    
    # Only alphanumeric and underscore
    return code.replace("_", "").isalnum() and code.islower()


def validate_status_data(data: dict) -> tuple[bool, str]:
    """
    Validate trip status data format.
    
    Args:
        data: Status data to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not data.get("code"):
        return False, "Code is required"
    
    if not validate_status_code(data["code"]):
        return False, "Code must be lowercase alphanumeric with underscores"
    
    if not data.get("label"):
        return False, "Label is required"
    
    if "order" not in data:
        return False, "Order is required"
    
    try:
        order = int(data["order"])
        if order < 0:
            return False, "Order must be non-negative"
    except (ValueError, TypeError):
        return False, "Order must be an integer"
    
    return True, ""


def trip_status_to_dict(status) -> dict:
    """Convert trip status object to dictionary."""
    if isinstance(status, dict):
        return status
    return dict(status)


def trip_status_from_dict(data: dict) -> TripStatusDict:
    """Convert dictionary to TripStatusDict."""
    return TripStatusDict(**data)
