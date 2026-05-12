"""
Trip service - business logic for trip management and state transitions.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from src.repositories.trip_repository import TripRepository
from src.repositories.vehicle_repository import VehicleRepository
from src.repositories.driver_repository import DriverRepository
from src.repositories.cargo_type_repository import CargoTypeRepository
from src.repositories.trip_status_repository import TripStatusRepository
from src.services.invoice_service import InvoiceService
from src.services.audit_service import AuditService
from src.infrastructure.database import MongoDBConnection, RepositoryError
from src.infrastructure.retry_strategy import retry_with_backoff
from src.infrastructure.pdf_generator import (
    generate_orden_cargue,
    generate_manifesto,
    generate_cumplido,
    upload_to_s3
)
from src.infrastructure.retry_utils import manual_retry, is_transient_error

logger = logging.getLogger(__name__)


class TripError(Exception):
    """Base exception for trip operations."""
    pass


class TripValidationError(TripError):
    """Raised when trip data is invalid."""
    pass


class TripNotFoundError(TripError):
    """Raised when trip is not found."""
    pass


class TripStatusTransitionError(TripError):
    """Raised when invalid status transition is attempted."""
    pass


class TripService:
    """Service for trip management."""
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize TripService.
        
        Args:
            connection: MongoDBConnection instance
        """
        self.connection = connection
        self.trip_repo = TripRepository(connection)
        self.vehicle_repo = VehicleRepository(connection)
        self.driver_repo = DriverRepository(connection)
        self.cargo_repo = CargoTypeRepository(connection)
        self.status_repo = TripStatusRepository(connection)
        self.invoice_service = InvoiceService(connection)
        self.audit_service = AuditService(connection)
    
    def create_trip(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Create a new trip with validation.
        
        Business rules:
        - Vehicle must have status 'available'
        - Driver must have license_expired = False
        - Total cost calculated automatically
        - Initial status set to 'scheduled'
        
        Args:
            data: Trip data (origin, destination, departure_date, weight_tons, etc.)
            user_id: User creating the trip
            
        Returns:
            Created trip document
            
        Raises:
            TripValidationError: If validation fails
            TripError: If creation fails
        """
        try:
            # Validate required fields
            required_fields = ['origin', 'destination', 'departure_date', 'weight_tons',
                             'vehicle_id', 'driver_id', 'cargo_id', 'client_id', 'recipient_id']
            
            for field in required_fields:
                if field not in data or not data[field]:
                    raise TripValidationError(f"Missing required field: {field}")
            
            # Validate vehicle is available
            try:
                vehicle = self.vehicle_repo.find_by_id(data['vehicle_id'])
            except Exception:
                raise TripValidationError(f"Invalid vehicle ID format: {data['vehicle_id']}")
            if not vehicle:
                raise TripValidationError(f"Vehicle not found: {data['vehicle_id']}")
            if vehicle.get('status') != 'available':
                raise TripValidationError(f"Vehicle not available (status: {vehicle.get('status')})")
            
            # Validate driver license
            try:
                driver = self.driver_repo.find_by_id(data['driver_id'])
            except Exception:
                raise TripValidationError(f"Invalid driver ID format: {data['driver_id']}")
            if not driver:
                raise TripValidationError(f"Driver not found: {data['driver_id']}")
            if driver.get('license_expired', False):
                raise TripValidationError("Driver license is expired")
            
            # Get cargo type for price calculation
            try:
                cargo = self.cargo_repo.find_by_id(data['cargo_id'])
            except Exception:
                raise TripValidationError(f"Invalid cargo ID format: {data['cargo_id']}")
            if not cargo:
                raise TripValidationError(f"Cargo type not found: {data['cargo_id']}")
            
            # Get scheduled status
            scheduled_status = self.status_repo.find_by_code('scheduled')
            if not scheduled_status:
                raise TripValidationError("'Scheduled' status not found in system")
            
            # Calculate total cost
            weight = float(data['weight_tons'])
            price_per_ton = float(cargo.get('price_per_ton', 0))
            total_cost = weight * price_per_ton
            
            # Create trip document
            trip_doc = {
                'origin': str(data['origin']),
                'destination': str(data['destination']),
                'departure_date': data['departure_date'],
                'arrival_date': data.get('arrival_date'),
                'weight_tons': weight,
                'total_cost': total_cost,
                'vehicle_id': data['vehicle_id'],
                'driver_id': data['driver_id'],
                'cargo_id': data['cargo_id'],
                'client_id': data['client_id'],
                'recipient_id': data['recipient_id'],
                'status_id': scheduled_status['_id'],
                'documents': {},
                'notes': data.get('notes'),
                'created_by': user_id,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Insert and return
            trip_id = self.trip_repo.insert_one(trip_doc)
            trip_doc['_id'] = trip_id
            
            # Log audit (non-blocking)
            try:
                self.audit_service.log_action(
                    'trips', trip_id, 'INSERT', user_id,
                    previous_state=None,
                    new_state=trip_doc
                )
            except Exception as e:
                logger.warning(f"Failed to log audit for trip creation {trip_id}: {str(e)}")
            
            return trip_doc
        
        except TripValidationError:
            raise
        except RepositoryError as e:
            raise TripError(f"Database error: {str(e)}")
        except Exception as e:
            raise TripError(f"Error creating trip: {str(e)}")
    
    def get_trip(self, trip_id: str) -> Dict[str, Any]:
        """
        Get trip by ID.
        
        Args:
            trip_id: Trip ID
            
        Returns:
            Trip document
            
        Raises:
            TripNotFoundError: If trip not found
        """
        try:
            trip = self.trip_repo.find_by_id(trip_id)
            if not trip:
                raise TripNotFoundError(f"Trip not found: {trip_id}")
            return trip
        except TripNotFoundError:
            raise
        except Exception as e:
            raise TripError(f"Error retrieving trip: {str(e)}")
    
    def list_trips(self, filters: Dict[str, Any] = None, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """
        List trips with optional filters.
        
        Args:
            filters: Optional filters (status_id, client_id, vehicle_id, driver_id, etc.)
            limit: Maximum results
            skip: Pagination offset
            
        Returns:
            List of trip documents
        """
        try:
            query = filters or {}
            # Use retry logic for MongoDB query (transient failures)
            return retry_with_backoff(
                lambda: self.trip_repo.find_many(query, limit=limit, skip=skip, sort=[("departure_date", -1)]),
                max_attempts=3,
                initial_delay_ms=100,
                operation_name="list_trips"
            )
        except Exception as e:
            raise TripError(f"Error listing trips: {str(e)}")
    
    def update_trip_status(self, trip_id: str, status_code: str, user_id: str) -> Dict[str, Any]:
        """
        Update trip status with automatic side effects.
        
        Business rules:
        - 'in_transit': Generate PDFs, set vehicle to 'in_trip'
        - 'delivered': Generate invoice, set vehicle to 'available'
        - 'cancelled': Release vehicle and driver
        
        Args:
            trip_id: Trip ID
            status_code: New status code (in_transit, delivered, cancelled)
            user_id: User performing the update
            
        Returns:
            Updated trip document
            
        Raises:
            TripStatusTransitionError: If status transition is invalid
            TripError: If update fails
        """
        try:
            # Get current trip
            trip = self.get_trip(trip_id)
            previous_state = dict(trip)
            
            # Get new status
            new_status = self.status_repo.find_by_code(status_code)
            if not new_status:
                raise TripStatusTransitionError(f"Invalid status code: {status_code}")
            
            # Handle status transitions
            if status_code == 'in_transit':
                trip = self._transition_to_in_transit(trip, new_status, user_id)
            
            elif status_code == 'delivered':
                trip = self._transition_to_delivered(trip, new_status, user_id)
            
            elif status_code == 'cancelled':
                trip = self._transition_to_cancelled(trip, new_status, user_id)
            
            else:
                # Generic status update (no side effects)
                updated = self.trip_repo.update_status(trip_id, new_status['_id'])
                if not updated:
                    raise TripNotFoundError(f"Trip not found: {trip_id}")
                trip = self.get_trip(trip_id)
            
            # Log audit (non-blocking)
            try:
                self.audit_service.log_action(
                    'trips', trip_id, 'UPDATE', user_id,
                    previous_state=previous_state,
                    new_state=trip,
                    details={'status_transition': status_code}
                )
            except Exception as e:
                logger.warning(f"Failed to log audit for trip status update {trip_id}: {str(e)}")
            
            return trip
        
        except (TripStatusTransitionError, TripNotFoundError, TripError):
            raise
        except Exception as e:
            raise TripError(f"Error updating trip status: {str(e)}")
    
    def delete_trip(self, trip_id: str, user_id: str) -> None:
        """
        Soft delete a trip (logical delete with audit trail).
        
        Business rules:
        - Only trips in 'scheduled' status can be deleted
        - Soft delete: mark as deleted, don't remove from DB
        - Logs full before/after states for audit
        
        Args:
            trip_id: Trip ID
            user_id: User performing the deletion
            
        Raises:
            TripStatusTransitionError: If trip has progressed beyond scheduled
            TripNotFoundError: If trip not found
            TripError: If deletion fails
        """
        try:
            # Get current trip
            trip = self.get_trip(trip_id)
            previous_state = dict(trip)
            
            # Check if trip can be deleted (only scheduled trips)
            status = self.status_repo.find_by_id(trip.get('status_id'))
            if status and status.get('code') != 'scheduled':
                raise TripStatusTransitionError(
                    f"Cannot delete trip in '{status.get('code')}' status. Only scheduled trips can be deleted."
                )
            
            # Release vehicle if allocated
            vehicle_id = trip.get('vehicle_id')
            if vehicle_id:
                self.vehicle_repo.update_one(
                    {'_id': vehicle_id},
                    {'$set': {'status': 'available', 'updated_at': datetime.now(timezone.utc)}}
                )
            
            # Soft delete trip
            deleted_at = datetime.now(timezone.utc)
            self.trip_repo.update_one(
                {'_id': trip_id},
                {'$set': {
                    'deleted': True,
                    'deleted_at': deleted_at,
                    'deleted_by': user_id,
                    'updated_at': deleted_at
                }}
            )
            
            # Get updated trip state after soft delete
            new_state = dict(trip)
            new_state.update({
                'deleted': True,
                'deleted_at': deleted_at,
                'deleted_by': user_id,
                'updated_at': deleted_at
            })
            
            # Log audit (non-blocking)
            try:
                self.audit_service.log_action(
                    'trips', trip_id, 'SOFT_DELETE', user_id,
                    previous_state=previous_state,
                    new_state=new_state,
                    details={'vehicle_released': vehicle_id is not None}
                )
            except Exception as e:
                logger.warning(f"Failed to log audit for trip deletion {trip_id}: {str(e)}")
        
        except (TripStatusTransitionError, TripNotFoundError):
            raise
        except Exception as e:
            raise TripError(f"Error deleting trip: {str(e)}")
    
    def _generate_and_upload_document(
        self,
        doc_type: str,
        trip: Dict[str, Any],
        trip_id_str: str,
        generator_func,
    ) -> str:
        """
        Generate and upload a PDF document with automatic retries.
        
        This method wraps PDF generation and S3 upload with exponential backoff
        retry logic. Only transient errors (network, timeout, 5xx) trigger retries.
        Permanent errors (validation, 4xx) are propagated immediately.
        
        Args:
            doc_type: Document type ('orden', 'manifesto', 'cumplido')
            trip: Trip data for generation
            trip_id_str: String representation of trip ID for logging
            generator_func: PDF generation function (e.g., generate_orden_cargue)
            
        Returns:
            Presigned URL for the uploaded PDF
            
        Raises:
            TripError: If generation/upload fails after retries (permanent error)
            PDFGenerationError: If PDF generation fails (non-retryable)
        """
        def _generate_and_upload():
            """Inner function to retry."""
            logger.debug(f"Generating {doc_type} PDF for trip {trip_id_str}")
            pdf_bytes = generator_func(trip)
            
            logger.debug(f"Uploading {doc_type} PDF for trip {trip_id_str} to S3")
            url = upload_to_s3(pdf_bytes, f"{doc_type}-{trip_id_str}")
            
            logger.info(f"Successfully generated and uploaded {doc_type} PDF for trip {trip_id_str}")
            return url
        
        try:
            # Retry with exponential backoff: max 3 attempts, 1s, 2s, 4s
            url = manual_retry(
                _generate_and_upload,
                max_attempts=3,
                initial_wait_seconds=1.0,
                operation_name=f"{doc_type} PDF generation/upload for trip {trip_id_str}"
            )
            return url
        
        except Exception as e:
            # If retries exhausted, raise TripError
            logger.error(f"Failed to generate/upload {doc_type} PDF for trip {trip_id_str} after retries: {str(e)}")
            raise TripError(f"Failed to generate/upload {doc_type} document: {str(e)}")
    
    def _transition_to_in_transit(self, trip: Dict[str, Any], status: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle transition to 'in_transit' status."""
        try:
            trip_id_str = str(trip['_id'])
            
            # Generate and upload PDFs with automatic retries
            # If this fails, exception is raised and trip status remains unchanged
            logger.info(f"Starting PDF generation/upload for trip {trip_id_str} transitioning to in_transit")
            
            orden_url = self._generate_and_upload_document(
                'orden',
                trip,
                trip_id_str,
                generate_orden_cargue
            )
            
            manifesto_url = self._generate_and_upload_document(
                'manifesto',
                trip,
                trip_id_str,
                generate_manifesto
            )
            
            logger.info(f"All PDFs generated successfully for trip {trip_id_str}")
            
            # Update trip with PDF URLs
            additional_updates = {
                'documents.order_pdf': orden_url,
                'documents.manifest_pdf': manifesto_url
            }
            
            # Update vehicle status to 'in_trip'
            vehicle_id = trip['vehicle_id']
            self.vehicle_repo.update_one(
                {'_id': vehicle_id},
                {'$set': {'status': 'in_trip', 'updated_at': datetime.now(timezone.utc)}}
            )
            
            # Update trip status
            self.trip_repo.update_status(trip['_id'], status['_id'], additional_updates)
            
            # Log audit for vehicle update (non-blocking)
            try:
                self.audit_service.log_action(
                    'vehicles', vehicle_id, 'UPDATE', user_id,
                    details={'status_transition': 'available → in_trip', 'trip_id': str(trip['_id'])}
                )
            except Exception as e:
                logger.warning(f"Failed to log audit for vehicle {vehicle_id} status update: {str(e)}")
            
            return self.get_trip(trip['_id'])
        
        except Exception as e:
            raise TripError(f"Error transitioning to in_transit: {str(e)}")
    
    def _transition_to_delivered(self, trip: Dict[str, Any], status: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle transition to 'delivered' status."""
        try:
            trip_id_str = str(trip['_id'])
            
            # Set arrival date if not set
            arrival_date = trip.get('arrival_date') or datetime.now(timezone.utc)
            
            # Generate and upload Cumplido PDF with automatic retries
            logger.info(f"Starting PDF generation/upload for trip {trip_id_str} transitioning to delivered")
            
            cumplido_url = self._generate_and_upload_document(
                'cumplido',
                trip,
                trip_id_str,
                generate_cumplido
            )
            
            # Create invoice
            invoice = self.invoice_service.create_invoice(trip)
            
            # Generate invoice PDF (already done in invoice service)
            invoice_url = invoice.get('pdf_url')
            
            # Update trip with PDFs and set arrival date
            additional_updates = {
                'documents.cumplido_pdf': cumplido_url,
                'documents.invoice_pdf': invoice_url,
                'arrival_date': arrival_date
            }
            
            # Update vehicle status to 'available'
            vehicle_id = trip['vehicle_id']
            self.vehicle_repo.update_one(
                {'_id': vehicle_id},
                {'$set': {'status': 'available', 'updated_at': datetime.now(timezone.utc)}}
            )
            
            # Update trip status
            self.trip_repo.update_status(trip['_id'], status['_id'], additional_updates)
            
            # Log audit for vehicle update (non-blocking)
            try:
                self.audit_service.log_action(
                    'vehicles', vehicle_id, 'UPDATE', user_id,
                    details={'status_transition': 'in_trip → available', 'trip_id': str(trip['_id']), 'invoice_id': str(invoice.get('_id'))}
                )
            except Exception as e:
                logger.warning(f"Failed to log audit for vehicle {vehicle_id} status update: {str(e)}")
            
            return self.get_trip(trip['_id'])
        
        except Exception as e:
            raise TripError(f"Error transitioning to delivered: {str(e)}")
    
    def _transition_to_cancelled(self, trip: Dict[str, Any], status: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle transition to 'cancelled' status."""
        try:
            # Release vehicle (set to available)
            vehicle_id = trip['vehicle_id']
            self.vehicle_repo.update_one(
                {'_id': vehicle_id},
                {'$set': {'status': 'available', 'updated_at': datetime.now(timezone.utc)}}
            )
            
            # Update trip status (no invoice for cancelled trips)
            self.trip_repo.update_status(trip['_id'], status['_id'])
            
            # Log audit for vehicle update (non-blocking)
            try:
                self.audit_service.log_action(
                    'vehicles', vehicle_id, 'UPDATE', user_id,
                    details={'status_transition': 'released from cancelled trip', 'trip_id': str(trip['_id'])}
                )
            except Exception as e:
                logger.warning(f"Failed to log audit for vehicle {vehicle_id} status update: {str(e)}")
            
            return self.get_trip(trip['_id'])
        
        except Exception as e:
            raise TripError(f"Error transitioning to cancelled: {str(e)}")
