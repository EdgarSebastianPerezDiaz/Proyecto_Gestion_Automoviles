"""
Invoice repository - data access layer for invoice entities.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.errors import PyMongoError

from src.repositories.base_repository import BaseRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


class InvoiceRepository(BaseRepository):
    """
    Repository for invoice data access.
    
    Provides CRUD operations and invoice-specific queries.
    Extends BaseRepository for common functionality.
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize invoice repository.
        
        Args:
            connection: MongoDBConnection singleton instance
            
        Raises:
            RepositoryError: If connection is not initialized
        """
        super().__init__('invoices', connection)
    
    def find_by_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """
        Find invoice by trip ID (unique relationship).
        
        Args:
            trip_id: Trip ObjectId as string
            
        Returns:
            Invoice document or None if not found
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            return self.find_one({'trip_id': trip_id})
        except Exception as e:
            raise RepositoryError(f"Error finding invoice by trip {trip_id}: {str(e)}")
    
    def find_by_client(
        self,
        client_id: str,
        status_filter: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Find invoices by client ID with optional status filter.
        
        Args:
            client_id: Client ObjectId as string
            status_filter: Optional status filter ('issued', 'paid', 'void')
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of invoice documents
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            query = {'client_id': client_id}
            if status_filter:
                query['status'] = status_filter
            
            return self.find_many(
                query,
                limit=limit,
                skip=skip,
                sort=[('issued_at', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding invoices for client {client_id}: {str(e)}")
    
    def find_by_status(
        self,
        status: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Find invoices by status.
        
        Args:
            status: Invoice status ('issued', 'paid', 'void')
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of invoice documents
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            return self.find_many(
                {'status': status},
                limit=limit,
                skip=skip,
                sort=[('issued_at', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding invoices with status {status}: {str(e)}")
    
    def find_by_date_range(
        self,
        from_date: datetime,
        to_date: datetime,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Find invoices issued within a date range.
        
        Args:
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of invoice documents
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            return self.find_many(
                {
                    'issued_at': {
                        '$gte': from_date,
                        '$lte': to_date
                    }
                },
                limit=limit,
                skip=skip,
                sort=[('issued_at', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding invoices by date range: {str(e)}")
    
    def update_status(self, invoice_id: str, new_status: str, paid_at: Optional[datetime] = None) -> bool:
        """
        Update invoice status.
        
        Args:
            invoice_id: Invoice ObjectId as string
            new_status: New status ('issued', 'paid', 'void')
            paid_at: Payment date (for 'paid' status)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            update_data = {
                'status': new_status,
                'updated_at': datetime.now(timezone.utc)
            }
            
            if paid_at and new_status == 'paid':
                update_data['paid_at'] = paid_at
            
            return self.update_one(
                {'_id': ObjectId(invoice_id)},
                {'$set': update_data}
            )
        except Exception as e:
            raise RepositoryError(f"Error updating invoice status: {str(e)}")
    
    def get_next_invoice_number(self, year: Optional[int] = None) -> str:
        """
        Generate next invoice number in format INV-YYYY-NNNNN.
        
        Format resets each year for cleaner numbering.
        
        Args:
            year: Year for invoice number (default: current year)
            
        Returns:
            Next invoice number (e.g., 'INV-2026-00001')
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            if year is None:
                year = datetime.now(timezone.utc).year
            
            # Get counters collection for atomic increment
            counters_collection = self.connection.get_collection('counters')
            
            # Increment counter for this year
            counter_key = f'invoice_{year}'
            result = counters_collection.find_one_and_update(
                {'_id': counter_key},
                {'$inc': {'sequence': 1}},
                upsert=True,
                return_document=True
            )
            
            sequence = result['sequence']
            return f'INV-{year}-{sequence:05d}'
        except PyMongoError as e:
            raise RepositoryError(f"Error generating invoice number: {str(e)}")
    
    def find_unpaid(self, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """
        Find all unpaid invoices (status='issued').
        
        Args:
            limit: Maximum number of results
            skip: Number of results to skip for pagination
            
        Returns:
            List of unpaid invoice documents
            
        Raises:
            RepositoryError: On database operation errors
        """
        try:
            return self.find_many(
                {'status': 'issued'},
                limit=limit,
                skip=skip,
                sort=[('issued_at', -1)]
            )
        except Exception as e:
            raise RepositoryError(f"Error finding unpaid invoices: {str(e)}")
