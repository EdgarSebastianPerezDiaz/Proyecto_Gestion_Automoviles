"""
User Domain Model

Defines the User entity with validation and serialization utilities.
Used across repositories, services, and API layers.
"""

from typing import Optional, Literal, TypedDict
from datetime import datetime, timezone


class UserDict(TypedDict, total=False):
    """User dictionary representation for type hints."""
    _id: str
    email: str
    password_hash: str
    role: Literal['admin', 'operator']
    full_name: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


def user_to_dict(user: dict, include_password: bool = False) -> dict:
    """
    Convert user document to dictionary, optionally excluding sensitive fields.
    
    Args:
        user: User document from MongoDB
        include_password: Whether to include password_hash (usually False)
        
    Returns:
        Dictionary with user data (ObjectId converted to string)
    """
    if not user:
        return {}
    
    result = {
        "id": str(user.get("_id", "")),
        "email": user.get("email"),
        "role": user.get("role"),
        "full_name": user.get("full_name"),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
        "last_login": user.get("last_login").isoformat() if user.get("last_login") else None,
    }
    
    if include_password:
        result["password_hash"] = user.get("password_hash")
    
    return result


def user_from_dict(data: dict) -> dict:
    """
    Convert user input data to database format.
    
    Args:
        data: User data from API request
        
    Returns:
        Dictionary ready for database insertion
    """
    document = {
        "email": data.get("email", "").strip().lower(),
        "password_hash": data.get("password_hash", ""),
        "role": data.get("role", "operator"),
        "full_name": data.get("full_name", "").strip(),
        "is_active": data.get("is_active", True),
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }
    
    return document
