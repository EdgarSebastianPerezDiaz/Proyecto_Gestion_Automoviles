"""
Trip validation schemas using Pydantic v2.

Provides request/response models for trip endpoints with
built-in validation for dates, weights, and other fields.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal


class TripCreate(BaseModel):
    """
    Schema for creating a new trip.
    
    Validates:
    - Dates (departure before arrival if provided)
    - Weight (positive)
    - All required IDs
    """
    
    origin: str = Field(..., min_length=2, max_length=255, description="Trip origin")
    destination: str = Field(..., min_length=2, max_length=255, description="Trip destination")
    departure_date: datetime = Field(..., description="Departure date and time")
    arrival_date: Optional[datetime] = Field(None, description="Arrival date and time (optional)")
    weight_tons: float = Field(..., gt=0, description="Cargo weight in metric tons")
    total_cost: float = Field(..., ge=0, description="Total trip cost")
    vehicle_id: str = Field(..., description="Vehicle ID (MongoDB ObjectId)")
    driver_id: str = Field(..., description="Driver ID (MongoDB ObjectId)")
    cargo_id: str = Field(..., description="Cargo ID (MongoDB ObjectId)")
    client_id: str = Field(..., description="Client ID (MongoDB ObjectId)")
    recipient_id: str = Field(..., description="Final recipient ID (MongoDB ObjectId)")
    notes: Optional[str] = Field(None, max_length=1000, description="Trip notes")
    
    @field_validator('origin', 'destination')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()
    
    @field_validator('arrival_date')
    @classmethod
    def validate_arrival_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate arrival date is after departure date if provided."""
        if v is None:
            return v
        
        departure_date = info.data.get('departure_date')
        if departure_date and v <= departure_date:
            raise ValueError("Arrival date must be after departure date")
        
        return v
    
    @field_validator('notes')
    @classmethod
    def normalize_notes(cls, v: Optional[str]) -> Optional[str]:
        """Normalize notes (strip whitespace)."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('departure_date')
    @classmethod
    def validate_departure_date(cls, v: datetime) -> datetime:
        """Validate departure date is not in the past."""
        from datetime import datetime as dt, timezone
        # Allow times up to 1 minute in the past (clock skew tolerance)
        now = dt.now(timezone.utc)
        if v < now:
            raise ValueError("Departure date cannot be in the past")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "origin": "Bogotá, Cundinamarca",
                "destination": "Medellín, Antioquia",
                "departure_date": "2024-02-01T08:00:00Z",
                "arrival_date": "2024-02-01T18:30:00Z",
                "weight_tons": 25.5,
                "total_cost": 1500000.00,
                "vehicle_id": "507f1f77bcf86cd799439012",
                "driver_id": "507f1f77bcf86cd799439013",
                "cargo_id": "507f1f77bcf86cd799439014",
                "client_id": "507f1f77bcf86cd799439015",
                "recipient_id": "507f1f77bcf86cd799439016",
                "notes": "Entrega en horario comercial"
            }
        }
    }


class TripUpdate(BaseModel):
    """
    Schema for updating a trip.
    
    All fields are optional.
    """
    
    origin: Optional[str] = Field(None, min_length=2, max_length=255)
    destination: Optional[str] = Field(None, min_length=2, max_length=255)
    arrival_date: Optional[datetime] = None
    weight_tons: Optional[float] = Field(None, gt=0)
    total_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('origin', 'destination')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('notes')
    @classmethod
    def normalize_notes(cls, v: Optional[str]) -> Optional[str]:
        """Normalize notes (strip whitespace)."""
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


class TripResponse(BaseModel):
    """
    Schema for trip response in API endpoints.
    """
    
    id_field: str = Field(..., alias='_id')
    origin: str
    destination: str
    departure_date: datetime
    arrival_date: Optional[datetime]
    weight_tons: float
    total_cost: float
    vehicle_id: str
    driver_id: str
    cargo_id: str
    client_id: str
    recipient_id: str
    status_id: str
    notes: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439020",
                "origin": "Bogotá, Cundinamarca",
                "destination": "Medellín, Antioquia",
                "departure_date": "2024-02-01T08:00:00Z",
                "arrival_date": "2024-02-01T18:30:00Z",
                "weight_tons": 25.5,
                "total_cost": 1500000.00,
                "vehicle_id": "507f1f77bcf86cd799439012",
                "driver_id": "507f1f77bcf86cd799439013",
                "cargo_id": "507f1f77bcf86cd799439014",
                "client_id": "507f1f77bcf86cd799439015",
                "recipient_id": "507f1f77bcf86cd799439016",
                "status_id": "507f1f77bcf86cd799439050",
                "notes": "Entrega en horario comercial",
                "created_by": "admin_user_id",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class TripStatusUpdate(BaseModel):
    """
    Schema for updating trip status.
    
    Validates:
    - Status ID reference
    - Optional notes for status change
    """
    
    status_id: str = Field(..., description="Trip status ID (MongoDB ObjectId)")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes for status change")
    
    @field_validator('notes')
    @classmethod
    def normalize_notes(cls, v: Optional[str]) -> Optional[str]:
        """Normalize notes (strip whitespace)."""
        if v is None:
            return v
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status_id": "507f1f77bcf86cd799439050",
                "notes": "Llegó al destino, en proceso de descarga"
            }
        }
    }


class TripListResponse(BaseModel):
    """
    Schema for listing trips with pagination.
    """
    
    total: int
    limit: int
    skip: int
    trips: list[TripResponse]
