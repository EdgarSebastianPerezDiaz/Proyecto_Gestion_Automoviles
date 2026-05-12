"""
Invoice Domain Model

Defines the Invoice entity and related validation logic
for the freight transport platform.
"""

from typing import TypedDict, Optional
from datetime import datetime


class InvoiceDict(TypedDict, total=False):
    """Invoice entity representation."""
    _id: str
    invoice_number: str  # Format: INV-YYYY-NNNNN (e.g., INV-2026-00001)
    trip_id: str
    client_id: str
    amount: float  # Base amount (without tax)
    tax_amount: float  # Calculated tax (typically 19% IVA in Colombia)
    total_amount: float  # amount + tax_amount
    currency: str  # 'COP' (Colombian Peso)
    status: str  # 'issued', 'paid', 'void'
    issued_at: datetime
    paid_at: Optional[datetime]
    pdf_url: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# Valid invoice statuses
VALID_STATUSES = ['issued', 'paid', 'void']

# Tax rate in Colombia (19% IVA - Impuesto al Valor Agregado)
DEFAULT_TAX_RATE = 0.19

# Currency code
DEFAULT_CURRENCY = 'COP'


def validate_status(status: str) -> bool:
    """
    Validate invoice status.
    
    Args:
        status: Status code to validate
        
    Returns:
        True if valid status, False otherwise
    """
    return status in VALID_STATUSES


def calculate_tax_amount(base_amount: float, tax_rate: float = DEFAULT_TAX_RATE) -> float:
    """
    Calculate tax amount.
    
    Args:
        base_amount: Base amount before tax
        tax_rate: Tax rate (default 0.19 for 19% IVA)
        
    Returns:
        Calculated tax amount
    """
    return round(base_amount * tax_rate, 2)


def calculate_total_amount(base_amount: float, tax_amount: float = None, tax_rate: float = DEFAULT_TAX_RATE) -> float:
    """
    Calculate total amount including tax.
    
    Args:
        base_amount: Base amount before tax
        tax_amount: Tax amount (if None, calculated from base_amount and tax_rate)
        tax_rate: Tax rate (default 0.19 for 19% IVA)
        
    Returns:
        Total amount (base + tax)
    """
    if tax_amount is None:
        tax_amount = calculate_tax_amount(base_amount, tax_rate)
    return round(base_amount + tax_amount, 2)


def invoice_to_dict(invoice_doc: dict) -> InvoiceDict:
    """
    Convert MongoDB invoice document to InvoiceDict.
    
    Args:
        invoice_doc: MongoDB invoice document
        
    Returns:
        InvoiceDict with all fields
    """
    return InvoiceDict(
        _id=str(invoice_doc.get('_id', '')),
        invoice_number=invoice_doc.get('invoice_number'),
        trip_id=str(invoice_doc.get('trip_id', '')),
        client_id=str(invoice_doc.get('client_id', '')),
        amount=invoice_doc.get('amount'),
        tax_amount=invoice_doc.get('tax_amount'),
        total_amount=invoice_doc.get('total_amount'),
        currency=invoice_doc.get('currency', DEFAULT_CURRENCY),
        status=invoice_doc.get('status', 'issued'),
        issued_at=invoice_doc.get('issued_at'),
        paid_at=invoice_doc.get('paid_at'),
        pdf_url=invoice_doc.get('pdf_url'),
        notes=invoice_doc.get('notes'),
        created_at=invoice_doc.get('created_at'),
        updated_at=invoice_doc.get('updated_at')
    )
