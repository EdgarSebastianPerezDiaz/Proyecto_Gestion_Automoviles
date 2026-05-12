"""
Query Parameter Validation Schemas for API Endpoints

Provides Pydantic models for validating pagination, filtering, and search parameters
across all API endpoints. Ensures type safety and consistent validation rules.

All models support automatic conversion of string query parameters to appropriate types.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date
import re


class PaginationParams(BaseModel):
    """
    Base pagination parameters for list endpoints.
    
    Attributes:
        page: Page number (1-indexed), range 1-100
        limit: Items per page, range 1-100
        q: Optional search query, 1-100 characters
    
    Example:
        >>> params = PaginationParams(page=1, limit=50, q="search term")
    """
    page: int = Field(default=1, ge=1, le=100, description="Page number (1-indexed)")
    limit: int = Field(default=50, ge=1, le=100, description="Items per page")
    q: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Search query")
    
    model_config = {"str_strip_whitespace": True}
    
    @field_validator("q")
    @classmethod
    def validate_query(cls, v):
        """Validate search query is not just whitespace."""
        if v is not None and v.strip() == "":
            raise ValueError("Search query cannot be empty or whitespace only")
        return v.strip() if v else None


class TripFilters(PaginationParams):
    """
    Filters specific to trips listing endpoint.
    
    Inherits pagination parameters and adds trip-specific filters
    with validation for IDs and dates.
    
    Attributes:
        status: Trip status (pending, in_transit, completed, cancelled)
        client_id: MongoDB ObjectId of client
        vehicle_id: MongoDB ObjectId of vehicle
        driver_id: MongoDB ObjectId of driver
        from_date: Start date (ISO8601 format: YYYY-MM-DD)
        to_date: End date (ISO8601 format: YYYY-MM-DD)
    
    Validations:
        - from_date must be <= to_date
        - Dates must be valid ISO8601 format
        - All dates must be in YYYY-MM-DD format
    
    Example:
        >>> filters = TripFilters(
        ...     page=1,
        ...     limit=50,
        ...     status="completed",
        ...     from_date="2026-01-01",
        ...     to_date="2026-12-31"
        ... )
    """
    status: Optional[str] = Field(
        default=None,
        pattern="^(pending|in_transit|completed|cancelled)$",
        description="Trip status filter"
    )
    client_id: Optional[str] = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern="^[a-fA-F0-9]{24}$",
        description="MongoDB ObjectId of client"
    )
    vehicle_id: Optional[str] = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern="^[a-fA-F0-9]{24}$",
        description="MongoDB ObjectId of vehicle"
    )
    driver_id: Optional[str] = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern="^[a-fA-F0-9]{24}$",
        description="MongoDB ObjectId of driver"
    )
    from_date: Optional[str] = Field(
        default=None,
        description="Start date in ISO8601 format (YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        default=None,
        description="End date in ISO8601 format (YYYY-MM-DD)"
    )
    
    @field_validator("from_date", "to_date", mode="before")
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format is ISO8601 YYYY-MM-DD."""
        if v is None:
            return v
        
        # Check format YYYY-MM-DD
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("Date must be in ISO8601 format (YYYY-MM-DD)")
        
        # Parse to ensure it's a valid date
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date: {v}")
        
        return v
    
    @model_validator(mode="after")
    def validate_date_range(self):
        """Validate that from_date <= to_date if both provided."""
        if self.from_date and self.to_date:
            from_dt = date.fromisoformat(self.from_date)
            to_dt = date.fromisoformat(self.to_date)
            
            if from_dt > to_dt:
                raise ValueError("from_date must be less than or equal to to_date")
        
        return self
