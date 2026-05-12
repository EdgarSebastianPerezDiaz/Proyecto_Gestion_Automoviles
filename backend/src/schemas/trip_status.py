"""
Trip Status validation schemas using Pydantic v2.

Provides request/response models for trip status endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


class TripStatusCreate(BaseModel):
    """
    Schema for creating a new trip status type.
    
    Validates:
    - Status name format
    - Description format
    - Sequence/order for workflow
    """
    
    name: str = Field(..., min_length=2, max_length=50, description="Status name (e.g., 'In Transit', 'Delivered')")
    description: Optional[str] = Field(None, min_length=5, max_length=255, description="Description (optional)")
    sequence_order: int = Field(..., ge=0, le=100, description="Order in workflow (0-100)")
    is_terminal: bool = Field(default=False, description="Is this a terminal/final status?")
    
    @field_validator('name')
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize status name."""
        return v.strip().title()
    
    @field_validator('description')
    @classmethod
    def strip_description(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from description."""
        if v is None:
            return v
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "En Tránsito",
                "description": "El envío está en tránsito hacia su destino",
                "sequence_order": 2,
                "is_terminal": False
            }
        }
    }


class TripStatusUpdate(BaseModel):
    """
    Schema for updating a trip status type.
    
    All fields are optional.
    """
    
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, min_length=5, max_length=255)
    sequence_order: Optional[int] = Field(None, ge=0, le=100)
    is_terminal: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        """Normalize status name."""
        if v is None:
            return v
        return v.strip().title()
    
    @field_validator('description')
    @classmethod
    def strip_description(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from description."""
        if v is None:
            return v
        return v.strip()
