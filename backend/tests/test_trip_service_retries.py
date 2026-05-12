"""
Tests for trip service retry logic with transient failure handling.

This module tests that trip PDF generation and S3 upload operations
retry on transient errors (network, timeout) but fail immediately on
permanent errors (validation, auth).
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch
from bson import ObjectId

import boto3
import pytest
from mongomock import MongoClient
from moto import mock_s3
from botocore.exceptions import ClientError

from src.services.trip_service import TripService, TripError
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.retry_utils import is_transient_error


@pytest.fixture
def mock_mongodb():
    """Create a mock MongoDB connection."""
    client = MongoClient()
    db = client['heavy-freight-test']
    return db


@pytest.fixture
def setup_trip_data(mock_mongodb):
    """Set up minimal trip test data in MongoDB."""
    db = mock_mongodb
    
    # Create trip_statuses collection
    in_transit_status = {
        '_id': ObjectId(),
        'status_code': 'in_transit',
        'status_name': 'In Transit',
        'is_final': False,
    }
    delivered_status = {
        '_id': ObjectId(),
        'status_code': 'delivered',
        'status_name': 'Delivered',
        'is_final': True,
    }
    db.trip_statuses.insert_many([in_transit_status, delivered_status])
    
    # Create vehicles collection
    vehicle_doc = {
        '_id': ObjectId(),
        'plate': 'ABC-123',
        'status': 'available',
    }
    db.vehicles.insert_one(vehicle_doc)
    
    # Create drivers collection
    driver_doc = {
        '_id': ObjectId(),
        'name': 'Driver Name',
        'license_expired': False,
    }
    db.drivers.insert_one(driver_doc)
    
    # Create cargo_types collection
    cargo_doc = {
        '_id': ObjectId(),
        'name': 'General Cargo',
    }
    db.cargo_types.insert_one(cargo_doc)
    
    # Create clients collection
    client_doc = {
        '_id': ObjectId(),
        'name': 'Client Name',
    }
    db.clients.insert_one(client_doc)
    
    # Create final_recipients collection
    recipient_doc = {
        '_id': ObjectId(),
        'name': 'Recipient Name',
    }
    db.final_recipients.insert_one(recipient_doc)
    
    # Create trip
    trip_doc = {
        '_id': ObjectId(),
        'status_id': in_transit_status['_id'],
        'vehicle_id': vehicle_doc['_id'],
        'driver_id': driver_doc['_id'],
        'cargo_id': cargo_doc['_id'],
        'client_id': client_doc['_id'],
        'recipient_id': recipient_doc['_id'],
        'origin': 'Bogotá',
        'destination': 'Medellín',
        'departure_date': datetime.now(timezone.utc),
        'documents': {},
        'created_at': datetime.now(timezone.utc),
    }
    db.trips.insert_one(trip_doc)
    
    # Create audit_logs collection
    db.audit_logs.create_index([('collection', 1), ('document_id', 1)])
    
    return {
        'db': db,
        'trip_id': trip_doc['_id'],
        'in_transit_status': in_transit_status,
        'delivered_status': delivered_status,
        'vehicle_id': vehicle_doc['_id'],
    }


class TestTransientErrorDetection:
    """Test the is_transient_error utility function."""
    
    def test_s3_timeout_is_transient(self):
        """Test that S3 timeout errors are detected as transient."""
        error = ClientError(
            {'Error': {'Code': 'ConnectTimeout'}, 'ResponseMetadata': {'HTTPStatusCode': 408}},
            'PutObject'
        )
        assert is_transient_error(error) is True
    
    def test_s3_throttling_is_transient(self):
        """Test that S3 throttling errors are detected as transient."""
        error = ClientError(
            {'Error': {'Code': 'Throttling'}, 'ResponseMetadata': {'HTTPStatusCode': 429}},
            'PutObject'
        )
        assert is_transient_error(error) is True
    
    def test_s3_service_unavailable_is_transient(self):
        """Test that S3 service unavailable is transient."""
        error = ClientError(
            {'Error': {'Code': 'ServiceUnavailable'}, 'ResponseMetadata': {'HTTPStatusCode': 503}},
            'PutObject'
        )
        assert is_transient_error(error) is True
    
    def test_validation_error_is_not_transient(self):
        """Test that validation errors are not transient."""
        error = ClientError(
            {'Error': {'Code': 'ValidationError'}, 'ResponseMetadata': {'HTTPStatusCode': 400}},
            'PutObject'
        )
        assert is_transient_error(error) is False
    
    def test_auth_error_is_not_transient(self):
        """Test that authentication errors are not transient."""
        error = ClientError(
            {'Error': {'Code': 'AccessDenied'}, 'ResponseMetadata': {'HTTPStatusCode': 403}},
            'PutObject'
        )
        assert is_transient_error(error) is False
    
    def test_not_found_is_not_transient(self):
        """Test that 404 errors are not transient."""
        error = ClientError(
            {'Error': {'Code': 'NoSuchBucket'}, 'ResponseMetadata': {'HTTPStatusCode': 404}},
            'PutObject'
        )
        assert is_transient_error(error) is False
    
    def test_timeout_error_is_transient(self):
        """Test that TimeoutError is transient."""
        assert is_transient_error(TimeoutError("Connection timeout")) is True
    
    def test_connection_error_is_transient(self):
        """Test that ConnectionError is transient."""
        assert is_transient_error(ConnectionError("Connection refused")) is True
    
    def test_io_error_is_transient(self):
        """Test that IOError is transient."""
        assert is_transient_error(IOError("I/O error")) is True
    
    def test_value_error_is_not_transient(self):
        """Test that ValueError is not transient."""
        assert is_transient_error(ValueError("Invalid value")) is False


class TestRetryOnTransientErrors:
    """Test that trip service retries on transient S3 errors."""
    
    @patch('src.services.trip_service.MongoDBConnection')
    @patch('src.services.trip_service.generate_orden_cargue')
    @patch('src.services.trip_service.upload_to_s3')
    def test_retry_on_s3_timeout_then_succeed(
        self,
        mock_upload_to_s3,
        mock_generate_orden,
        mock_db_conn,
        setup_trip_data
    ):
        """Test that S3 timeout is retried and eventually succeeds."""
        db = setup_trip_data['db']
        mock_db_conn.return_value.get_collection = lambda name: db[name]
        mock_db_conn.return_value.get_db.return_value = db
        
        # Generate fails with timeout on first attempt, succeeds on second
        trip = db.trips.find_one()
        mock_generate_orden.return_value = b'PDF_DATA'
        
        timeout_error = ClientError(
            {'Error': {'Code': 'ConnectTimeout'}, 'ResponseMetadata': {'HTTPStatusCode': 408}},
            'PutObject'
        )
        mock_upload_to_s3.side_effect = [timeout_error, 's3://bucket/orden.pdf']
        
        # Create trip service
        db_conn = MagicMock()
        db_conn.get_collection = lambda name: db[name]
        db_conn.get_db.return_value = db
        
        service = TripService(db_conn)
        
        # Call the retry-enabled method
        result = service._generate_and_upload_document(
            'orden',
            trip,
            str(trip['_id']),
            mock_generate_orden
        )
        
        # Should eventually succeed
        assert result == 's3://bucket/orden.pdf'
        # Should have been called twice (first fail, then succeed)
        assert mock_upload_to_s3.call_count == 2
    
    @patch('src.services.trip_service.MongoDBConnection')
    @patch('src.services.trip_service.generate_orden_cargue')
    @patch('src.services.trip_service.upload_to_s3')
    def test_fail_immediately_on_validation_error(
        self,
        mock_upload_to_s3,
        mock_generate_orden,
        mock_db_conn,
        setup_trip_data
    ):
        """Test that validation errors fail immediately without retries."""
        db = setup_trip_data['db']
        mock_db_conn.return_value.get_collection = lambda name: db[name]
        mock_db_conn.return_value.get_db.return_value = db
        
        trip = db.trips.find_one()
        mock_generate_orden.return_value = b'PDF_DATA'
        
        # Validation error - should NOT retry
        validation_error = ClientError(
            {'Error': {'Code': 'ValidationError'}, 'ResponseMetadata': {'HTTPStatusCode': 400}},
            'PutObject'
        )
        mock_upload_to_s3.side_effect = validation_error
        
        db_conn = MagicMock()
        db_conn.get_collection = lambda name: db[name]
        db_conn.get_db.return_value = db
        
        service = TripService(db_conn)
        
        # Should raise immediately
        with pytest.raises(TripError):
            service._generate_and_upload_document(
                'orden',
                trip,
                str(trip['_id']),
                mock_generate_orden
            )
        
        # Should have been called only once (no retries)
        assert mock_upload_to_s3.call_count == 1
    
    @patch('src.services.trip_service.MongoDBConnection')
    @patch('src.services.trip_service.generate_orden_cargue')
    @patch('src.services.trip_service.upload_to_s3')
    def test_exhaust_retries_then_fail(
        self,
        mock_upload_to_s3,
        mock_generate_orden,
        mock_db_conn,
        setup_trip_data
    ):
        """Test that after 3 retries, the error is raised."""
        db = setup_trip_data['db']
        mock_db_conn.return_value.get_collection = lambda name: db[name]
        mock_db_conn.return_value.get_db.return_value = db
        
        trip = db.trips.find_one()
        mock_generate_orden.return_value = b'PDF_DATA'
        
        # Always timeout
        timeout_error = ClientError(
            {'Error': {'Code': 'ServiceUnavailable'}, 'ResponseMetadata': {'HTTPStatusCode': 503}},
            'PutObject'
        )
        mock_upload_to_s3.side_effect = [timeout_error, timeout_error, timeout_error]
        
        db_conn = MagicMock()
        db_conn.get_collection = lambda name: db[name]
        db_conn.get_db.return_value = db
        
        service = TripService(db_conn)
        
        # Should raise after 3 attempts
        with pytest.raises(TripError):
            service._generate_and_upload_document(
                'orden',
                trip,
                str(trip['_id']),
                mock_generate_orden
            )
        
        # Should have tried exactly 3 times
        assert mock_upload_to_s3.call_count == 3


class TestTripStatusTransitionWithRetries:
    """Test that trip status transitions don't change state on transient failures."""
    
    @patch('src.services.trip_service.MongoDBConnection')
    @patch('src.services.trip_service.generate_orden_cargue')
    @patch('src.services.trip_service.generate_manifesto')
    @patch('src.services.trip_service.upload_to_s3')
    def test_in_transit_unchanged_on_pdf_failure(
        self,
        mock_upload_to_s3,
        mock_generate_manifesto,
        mock_generate_orden,
        mock_db_conn,
        setup_trip_data
    ):
        """Test that trip status doesn't change if PDF upload fails after retries."""
        db = setup_trip_data['db']
        mock_db_conn.return_value.get_collection = lambda name: db[name]
        mock_db_conn.return_value.get_db.return_value = db
        
        # Get the trip
        trip = db.trips.find_one()
        original_status = trip['status_id']
        
        # PDFs fail permanently (validation error - no retries)
        mock_generate_orden.return_value = b'PDF_DATA'
        mock_generate_manifesto.return_value = b'PDF_DATA'
        
        validation_error = ClientError(
            {'Error': {'Code': 'ValidationError'}, 'ResponseMetadata': {'HTTPStatusCode': 400}},
            'PutObject'
        )
        mock_upload_to_s3.side_effect = validation_error
        
        db_conn = MagicMock()
        db_conn.get_collection = lambda name: db[name]
        db_conn.get_db.return_value = db
        
        service = TripService(db_conn)
        
        # Try to transition to in_transit - should fail
        with pytest.raises(TripError):
            service._transition_to_in_transit(
                trip,
                setup_trip_data['in_transit_status'],
                'test-user'
            )
        
        # Verify trip status hasn't changed in database
        updated_trip = db.trips.find_one({'_id': trip['_id']})
        assert updated_trip['status_id'] == original_status
        
        # Verify documents are still empty
        assert not updated_trip.get('documents', {}).get('order_pdf')
        assert not updated_trip.get('documents', {}).get('manifest_pdf')


class TestPDFGenerationErrorHandling:
    """Test handling of PDF generation errors vs S3 upload errors."""
    
    @patch('src.services.trip_service.MongoDBConnection')
    @patch('src.services.trip_service.generate_orden_cargue')
    def test_pdf_generation_error_not_retried(
        self,
        mock_generate_orden,
        mock_db_conn,
        setup_trip_data
    ):
        """Test that PDF generation errors are not retried (they're permanent)."""
        db = setup_trip_data['db']
        mock_db_conn.return_value.get_collection = lambda name: db[name]
        mock_db_conn.return_value.get_db.return_value = db
        
        trip = db.trips.find_one()
        
        # PDF generation error (e.g., invalid trip data)
        from src.infrastructure.pdf_generator import PDFGenerationError
        mock_generate_orden.side_effect = PDFGenerationError("Invalid trip data")
        
        db_conn = MagicMock()
        db_conn.get_collection = lambda name: db[name]
        db_conn.get_db.return_value = db
        
        service = TripService(db_conn)
        
        # Should fail immediately (no retries for non-transient errors)
        with pytest.raises(TripError):
            service._generate_and_upload_document(
                'orden',
                trip,
                str(trip['_id']),
                mock_generate_orden
            )
        
        # Should have been called only once
        assert mock_generate_orden.call_count == 1
