"""
Cargo Type validation schemas using Pydantic v2.

Provides request/response models for cargo type endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class CargoTypeCreate(BaseModel):
    """
    Schema for creating a new cargo type.
    
    Validates:
    - Name format and length
    - Description format
    - Price must be positive
    """
    
    name: str = Field(..., min_length=2, max_length=100, description="Cargo type name")
    description: Optional[str] = Field(None, min_length=5, max_length=500, description="Description (optional)")
    price_per_ton: float = Field(..., gt=0, description="Price per ton (must be positive)")
    hazardous: bool = Field(default=False, description="Is this hazardous material?")
    requires_temperature_control: bool = Field(default=False, description="Requires temperature control?")
    requires_special_permit: bool = Field(default=False, description="Requires special permit?")
    fragile: bool = Field(default=False, description="Is this fragile?")
    
    @field_validator('name')
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize name to title case and strip whitespace."""
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
                "name": "Alimentos Perecederos",
                "description": "Productos alimenticios que requieren refrigeración",
                "price_per_ton": 125.50,
                "hazardous": False,
                "requires_temperature_control": True,
                "requires_special_permit": False,
                "fragile": False
            }
        }
    }


class CargoTypeUpdate(BaseModel):
    """
    Schema for updating a cargo type.
    
    All fields are optional.
    """
    
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=5, max_length=500)
    price_per_ton: Optional[float] = Field(None, gt=0, description="Price per ton (must be positive if provided)")
    hazardous: Optional[bool] = None
    requires_temperature_control: Optional[bool] = None
    requires_special_permit: Optional[bool] = None
    fragile: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        """Normalize name."""
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
