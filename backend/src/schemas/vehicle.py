"""
Vehicle validation schemas using Pydantic v2.

Provides request/response models for vehicle endpoints with
built-in validation for plates, capacity, and other fields.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime
import re


def sanitize_plate(plate: str) -> str:
    """
    Normalize vehicle plate to uppercase.
    
    Accepts any alphanumeric format after removing spaces and dashes.
    """
    clean_plate = re.sub(r'[\s\-]', '', plate)
    
    if not re.match(r'^[a-zA-Z0-9]+$', clean_plate):
        raise ValueError(f"Invalid plate format: {plate}. Expected alphanumeric characters only.")
    
    if not re.match(r'^[a-zA-Z0-9]{3,8}$', clean_plate):
        raise ValueError("Plate must be 3-8 alphanumeric characters")
    
    return clean_plate.upper()


class VehicleCreate(BaseModel):
    """
    Schema for creating a new vehicle.
    
    Validates:
    - Plate format (3-8 alphanumeric characters, uppercase)
    - Vehicle type
    - Capacity (positive number)
    - Company ID reference
    """
    
    plate: str = Field(..., min_length=3, max_length=10, description="Vehicle plate")
    vehicle_type: str = Field(..., min_length=2, max_length=50, description="Type (truck, trailer, van, etc.)")
    brand: str = Field(..., min_length=2, max_length=100, description="Vehicle brand/manufacturer")
    model_year: int = Field(..., ge=1990, le=2050, description="Year of manufacture")
    capacity_tons: float = Field(..., gt=0, description="Maximum cargo capacity in metric tons")
    volume_m3: Optional[float] = Field(None, gt=0, description="Cargo volume in cubic meters (optional)")
    company_id: str = Field(..., description="Company ID (MongoDB ObjectId)")
    soat_expiry: Optional[datetime] = Field(None, description="SOAT insurance expiry date")
    tech_review_expiry: Optional[datetime] = Field(None, description="Technical review expiry date")
    
    @field_validator('plate')
    @classmethod
    def validate_plate(cls, v: str) -> str:
        """Validate and normalize plate format."""
        return sanitize_plate(v)
    
    @field_validator('vehicle_type', 'brand')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "plate": "ABC123",
                "vehicle_type": "truck",
                "brand": "Volvo",
                "model_year": 2022,
                "capacity_tons": 30.0,
                "volume_m3": 85.5,
                "company_id": "507f1f77bcf86cd799439011",
                "soat_expiry": "2026-03-15T23:59:59Z",
                "tech_review_expiry": "2024-12-31T23:59:59Z"
            }
        }
    }


class VehicleUpdate(BaseModel):
    """
    Schema for updating a vehicle.
    
    All fields are optional.
    """
    
    vehicle_type: Optional[str] = Field(None, min_length=2, max_length=50)
    brand: Optional[str] = Field(None, min_length=2, max_length=100)
    model_year: Optional[int] = Field(None, ge=1990, le=2050)
    capacity_tons: Optional[float] = Field(None, gt=0)
    volume_m3: Optional[float] = Field(None, gt=0)
    soat_expiry: Optional[datetime] = None
    tech_review_expiry: Optional[datetime] = None
    is_active: Optional[bool] = None
    status: Optional[Literal['available', 'in_trip', 'inactive']] = None
    
    @field_validator('vehicle_type', 'brand')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace."""
        if v is None:
            return v
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def check_at_least_one_field(cls, data):
        """Ensure at least one field is provided for update."""
        if not data or all(v is None for v in data.values()):
            raise ValueError("At least one field must be provided for update")
        return data


class VehicleResponse(BaseModel):
    """
    Schema for vehicle response in API endpoints.
    """
    
    id_field: str = Field(..., alias='_id')
    plate: str
    vehicle_type: str
    brand: str
    model_year: int
    capacity_tons: float
    volume_m3: Optional[float]
    status: Literal['available', 'in_trip', 'inactive']
    company_id: str
    soat_expiry: Optional[datetime]
    tech_review_expiry: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439012",
                "plate": "ABC123",
                "vehicle_type": "truck",
                "brand": "Volvo",
                "model_year": 2022,
                "capacity_tons": 30.0,
                "volume_m3": 85.5,
                "status": "available",
                "company_id": "507f1f77bcf86cd799439011",
                "soat_expiry": "2026-03-15T23:59:59Z",
                "tech_review_expiry": "2024-12-31T23:59:59Z",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class VehicleListResponse(BaseModel):
    """
    Schema for listing vehicles with pagination.
    """
    
    total: int
    limit: int
    skip: int
    vehicles: list[VehicleResponse]
