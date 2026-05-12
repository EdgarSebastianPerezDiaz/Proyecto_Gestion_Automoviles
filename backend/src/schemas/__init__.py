"""
Pydantic schemas for API request/response validation.

This module exports all Pydantic models for request/response validation.
Each model includes type hints, validators, and documentation.
"""

from .company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyListResponse,
)

from .driver import (
    DriverCreate,
    DriverUpdate,
    DriverResponse,
    DriverListResponse,
)

from .vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    VehicleListResponse,
)

from .trip import (
    TripCreate,
    TripUpdate,
    TripResponse,
    TripListResponse,
)

from .client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientListResponse,
)

__all__ = [
    # Company schemas
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyResponse",
    "CompanyListResponse",
    # Driver schemas
    "DriverCreate",
    "DriverUpdate",
    "DriverResponse",
    "DriverListResponse",
    # Vehicle schemas
    "VehicleCreate",
    "VehicleUpdate",
    "VehicleResponse",
    "VehicleListResponse",
    # Trip schemas
    "TripCreate",
    "TripUpdate",
    "TripResponse",
    "TripListResponse",
    # Client schemas
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    "ClientListResponse",
]
