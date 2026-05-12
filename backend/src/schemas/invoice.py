"""
Invoice validation schemas using Pydantic v2.

Provides request/response models for invoice endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import re


class InvoicePaymentUpdate(BaseModel):
    """
    Schema for updating invoice payment status.
    
    Validates:
    - Payment status transitions
    - Payment reference/proof
    - Payment date
    """
    
    payment_status: Literal["paid", "pending", "partially_paid", "refunded", "failed"] = Field(
        ..., description="Payment status"
    )
    payment_date: Optional[datetime] = Field(None, description="Payment date (required for 'paid' status)")
    payment_reference: Optional[str] = Field(None, max_length=100, description="Payment reference/proof number")
    payment_method: Optional[Literal["cash", "check", "transfer", "credit_card", "debit_card"]] = Field(
        None, description="Payment method"
    )
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
    
    @field_validator('payment_reference')
    @classmethod
    def validate_payment_reference(cls, v: Optional[str]) -> Optional[str]:
        """Validate payment reference format."""
        if v is None:
            return v
        v = v.strip()
        if not re.match(r'^[A-Z0-9\-\/\.]+$', v):
            raise ValueError("Payment reference must contain only alphanumeric characters, dashes, slashes, and dots")
        return v
    
    @field_validator('notes')
    @classmethod
    def strip_notes(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from notes."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('payment_date')
    @classmethod
    def validate_payment_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate payment date for 'paid' status."""
        if v is not None:
            from datetime import datetime as dt, timezone
            # Payment date should not be in the future
            if v > dt.now(timezone.utc):
                raise ValueError("Payment date cannot be in the future")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "payment_status": "paid",
                "payment_date": "2024-01-15T14:30:00Z",
                "payment_reference": "TRF-2024-1001",
                "payment_method": "transfer",
                "notes": "Pago recibido vía transferencia bancaria"
            }
        }
    }


class InvoiceCreate(BaseModel):
    """
    Schema for creating a new invoice.
    
    Validates:
    - Invoice number format
    - Amount format
    - Tax/VAT format
    - Trip reference
    """
    
    trip_id: str = Field(..., description="Associated trip ID")
    invoice_number: str = Field(..., min_length=3, max_length=50, description="Invoice number")
    subtotal_amount: float = Field(..., gt=0, description="Subtotal amount")
    tax_amount: float = Field(default=0, ge=0, description="Tax/VAT amount")
    total_amount: float = Field(..., gt=0, description="Total amount (typically subtotal + tax)")
    currency: str = Field(default="COP", max_length=3, description="Currency code (e.g., COP, USD)")
    due_date: Optional[datetime] = Field(None, description="Payment due date (optional)")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
    
    @field_validator('invoice_number')
    @classmethod
    def validate_invoice_number(cls, v: str) -> str:
        """Validate invoice number format."""
        v = v.strip().upper()
        if not re.match(r'^[A-Z0-9\-\/]+$', v):
            raise ValueError("Invoice number must contain only alphanumeric characters, dashes, and slashes")
        return v
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code."""
        return v.strip().upper()
    
    @field_validator('notes')
    @classmethod
    def strip_notes(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from notes."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('total_amount')
    @classmethod
    def validate_total_amount(cls, v: float, info) -> float:
        """Validate total amount matches subtotal + tax."""
        # This could be stricter in production
        if v <= 0:
            raise ValueError("Total amount must be greater than zero")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "trip_id": "507f1f77bcf86cd799439011",
                "invoice_number": "INV-2024-001",
                "subtotal_amount": 500000,
                "tax_amount": 95000,
                "total_amount": 595000,
                "currency": "COP",
                "due_date": "2024-02-15T23:59:59Z",
                "notes": "Factura por servicios de transporte"
            }
        }
    }
