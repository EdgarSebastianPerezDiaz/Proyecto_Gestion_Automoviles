"""
Trip domain model.

Represents a freight transportation trip with all associated data.
"""
from typing import TypedDict, Optional
from datetime import datetime


class TripDocuments(TypedDict, total=False):
    """Trip attached documents with S3 URLs."""
    order_pdf: Optional[str]
    manifest_pdf: Optional[str]
    cumplido_pdf: Optional[str]
    invoice_pdf: Optional[str]


class Trip(TypedDict, total=False):
    """
    Trip domain model.
    
    Represents a freight trip with origin, destination, vehicle, driver,
    cargo and client information. Includes automatic cost calculation and
    document management.
    """
    _id: str
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
    documents: TripDocuments
    notes: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
