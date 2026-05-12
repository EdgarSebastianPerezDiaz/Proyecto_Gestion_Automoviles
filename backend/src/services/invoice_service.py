"""
Invoice Service

Business logic for invoice management.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.repositories.invoice_repository import InvoiceRepository
from src.infrastructure.database import MongoDBConnection, RepositoryError
from src.infrastructure.pdf_generator import generate_invoice, upload_to_s3
from src.domain.invoice import (
    calculate_tax_amount,
    calculate_total_amount,
    DEFAULT_TAX_RATE,
    DEFAULT_CURRENCY
)


class InvoiceError(Exception):
    """Base exception for invoice service operations."""
    pass


class InvoiceNotFoundError(InvoiceError):
    """Raised when invoice is not found."""
    pass


class InvalidInvoiceStatusError(InvoiceError):
    """Raised when invalid status transition is attempted."""
    pass


class InvoiceService:
    """Service for invoice management and operations."""
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize invoice service.
        
        Args:
            connection: MongoDBConnection instance
        """
        self.connection = connection
        self.repository = InvoiceRepository(connection)
    
    def create_invoice(
        self,
        trip_data: Dict[str, Any],
        trip_total: float,
        tax_rate: float = DEFAULT_TAX_RATE
    ) -> Dict[str, Any]:
        """
        Create invoice for a trip.
        
        Args:
            trip_data: Trip data including client_id, origin, destination, etc.
            trip_total: Base amount (without tax)
            tax_rate: Tax rate (default 19% for Colombian IVA)
            
        Returns:
            Created invoice document
            
        Raises:
            InvoiceError: If invoice creation fails
        """
        try:
            # Calculate tax and total
            tax_amount = calculate_tax_amount(trip_total, tax_rate)
            total_amount = calculate_total_amount(trip_total, tax_amount)
            
            # Generate invoice number
            invoice_number = self.repository.get_next_invoice_number()
            
            # Create invoice document
            invoice_doc = {
                'invoice_number': invoice_number,
                'trip_id': trip_data.get('_id'),
                'client_id': trip_data.get('client_id'),
                'amount': trip_total,
                'tax_amount': tax_amount,
                'total_amount': total_amount,
                'currency': DEFAULT_CURRENCY,
                'status': 'issued',
                'issued_at': datetime.now(timezone.utc),
                'paid_at': None,
                'pdf_url': None,
                'notes': trip_data.get('notes'),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Generate PDF
            try:
                pdf_bytes = generate_invoice(invoice_doc, trip_data)
                pdf_url = upload_to_s3(pdf_bytes, f"invoices/INV-{invoice_number}.pdf")
                invoice_doc['pdf_url'] = pdf_url
            except Exception as e:
                # Log error but continue - invoice still created without PDF
                print(f"Warning: Failed to generate invoice PDF: {str(e)}")
            
            # Insert invoice
            invoice_id = self.repository.insert_one(invoice_doc)
            invoice_doc['_id'] = invoice_id
            
            return invoice_doc
        except RepositoryError as e:
            raise InvoiceError(f"Failed to create invoice: {str(e)}")
        except Exception as e:
            raise InvoiceError(f"Error creating invoice: {str(e)}")
    
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Get invoice by ID.
        
        Args:
            invoice_id: Invoice ObjectId as string
            
        Returns:
            Invoice document
            
        Raises:
            InvoiceNotFoundError: If invoice not found
            InvoiceError: On other errors
        """
        try:
            invoice = self.repository.find_by_id(invoice_id)
            if not invoice:
                raise InvoiceNotFoundError(f"Invoice not found: {invoice_id}")
            return invoice
        except InvoiceNotFoundError:
            raise
        except Exception as e:
            raise InvoiceError(f"Error retrieving invoice: {str(e)}")
    
    def get_invoice_by_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """
        Get invoice for a trip.
        
        Args:
            trip_id: Trip ObjectId as string
            
        Returns:
            Invoice document or None if not found
            
        Raises:
            InvoiceError: On database errors
        """
        try:
            return self.repository.find_by_trip(trip_id)
        except Exception as e:
            raise InvoiceError(f"Error retrieving invoice by trip: {str(e)}")
    
    def list_invoices(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List invoices with optional filters.
        
        Args:
            filters: Optional filters (client_id, status, etc.)
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of invoice documents
            
        Raises:
            InvoiceError: On database errors
        """
        try:
            # Handle common filter scenarios
            if not filters:
                filters = {}
            
            client_id = filters.get('client_id')
            status = filters.get('status')
            
            if client_id:
                return self.repository.find_by_client(
                    client_id,
                    status_filter=status,
                    limit=limit,
                    skip=skip
                )
            elif status:
                return self.repository.find_by_status(status, limit=limit, skip=skip)
            else:
                # Generic find_many
                return self.repository.find_many(filters, limit=limit, skip=skip, sort=[('issued_at', -1)])
        except Exception as e:
            raise InvoiceError(f"Error listing invoices: {str(e)}")
    
    def mark_as_paid(self, invoice_id: str) -> Dict[str, Any]:
        """
        Mark invoice as paid.
        
        Args:
            invoice_id: Invoice ObjectId as string
            
        Returns:
            Updated invoice document
            
        Raises:
            InvoiceNotFoundError: If invoice not found
            InvalidInvoiceStatusError: If invoice already paid or void
            InvoiceError: On other errors
        """
        try:
            # Get current invoice
            invoice = self.get_invoice(invoice_id)
            
            # Validate current status
            if invoice['status'] == 'paid':
                raise InvalidInvoiceStatusError("Invoice is already paid")
            if invoice['status'] == 'void':
                raise InvalidInvoiceStatusError("Cannot mark void invoice as paid")
            
            # Update status
            success = self.repository.update_status(
                invoice_id,
                'paid',
                paid_at=datetime.now(timezone.utc)
            )
            
            if not success:
                raise InvoiceNotFoundError(f"Invoice not found: {invoice_id}")
            
            # Return updated invoice
            return self.get_invoice(invoice_id)
        except (InvoiceNotFoundError, InvalidInvoiceStatusError):
            raise
        except Exception as e:
            raise InvoiceError(f"Error marking invoice as paid: {str(e)}")
    
    def void_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Void an invoice (only if status='issued').
        
        Args:
            invoice_id: Invoice ObjectId as string
            
        Returns:
            Updated invoice document
            
        Raises:
            InvoiceNotFoundError: If invoice not found
            InvalidInvoiceStatusError: If invoice already paid or void
            InvoiceError: On other errors
        """
        try:
            # Get current invoice
            invoice = self.get_invoice(invoice_id)
            
            # Validate current status
            if invoice['status'] != 'issued':
                raise InvalidInvoiceStatusError(
                    f"Can only void invoices with status='issued', current status: {invoice['status']}"
                )
            
            # Update status
            success = self.repository.update_status(invoice_id, 'void')
            
            if not success:
                raise InvoiceNotFoundError(f"Invoice not found: {invoice_id}")
            
            # Return updated invoice
            return self.get_invoice(invoice_id)
        except (InvoiceNotFoundError, InvalidInvoiceStatusError):
            raise
        except Exception as e:
            raise InvoiceError(f"Error voiding invoice: {str(e)}")
    
    def get_unpaid_invoices(
        self,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all unpaid invoices (status='issued').
        
        Args:
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of unpaid invoice documents
            
        Raises:
            InvoiceError: On database errors
        """
        try:
            return self.repository.find_unpaid(limit=limit, skip=skip)
        except Exception as e:
            raise InvoiceError(f"Error retrieving unpaid invoices: {str(e)}")
