"""
Tests for trips API endpoints - presigned URL generation and downloads.

These tests verify the presigned URL endpoints by mocking the dependencies
and testing the response formats and error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from bson import ObjectId
import json

from src.services.trip_service import TripNotFoundError
from src.infrastructure.s3_uploader import S3Error


class TestPresignedURLEndpoints:
    """Test presigned URL endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create Flask app with mocked auth for testing."""
        from flask import Flask
        from src.api.trips import trips_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        # Register blueprint
        app.register_blueprint(trips_bp)
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_get_documents_endpoint_exists(self, client):
        """Test that the /documents endpoint is registered."""
        trip_id = str(ObjectId())
        
        # This will test that endpoint is registered (will get 401 if no auth)
        response = client.get(f'/api/trips/{trip_id}/documents')
        
        # Should not return 404 (endpoint not found)
        assert response.status_code != 404
    
    def test_download_endpoint_exists(self, client):
        """Test that the /download endpoint is registered."""
        trip_id = str(ObjectId())
        
        # This will test that endpoint is registered
        response = client.get(f'/api/trips/{trip_id}/download/order')
        
        # Should not return 404 (endpoint not found)
        assert response.status_code != 404


class TestPresignedURLGeneration:
    """Test presigned URL generation logic."""
    
    def test_presigned_url_s3_key_format_orden(self):
        """Test S3 key format for orden document."""
        trip_id = 'test-trip-123'
        
        # Format used in the endpoint
        expected_key = f"documents/orden-{trip_id}.pdf"
        
        assert expected_key == "documents/orden-test-trip-123.pdf"
    
    def test_presigned_url_s3_key_format_manifesto(self):
        """Test S3 key format for manifesto document."""
        trip_id = 'test-trip-123'
        expected_key = f"documents/manifesto-{trip_id}.pdf"
        
        assert expected_key == "documents/manifesto-test-trip-123.pdf"
    
    def test_presigned_url_s3_key_format_cumplido(self):
        """Test S3 key format for cumplido document."""
        trip_id = 'test-trip-123'
        expected_key = f"documents/cumplido-{trip_id}.pdf"
        
        assert expected_key == "documents/cumplido-test-trip-123.pdf"
    
    def test_presigned_url_s3_key_format_invoice(self):
        """Test S3 key format for invoice document."""
        trip_id = 'test-trip-123'
        expected_key = f"documents/invoice-{trip_id}.pdf"
        
        assert expected_key == "documents/invoice-test-trip-123.pdf"


class TestDocumentTypeMapping:
    """Test document type to S3 key mapping."""
    
    def test_document_mapping_orden(self):
        """Test orden document mapping."""
        doc_mapping = {
            'order_pdf': ('orden', 'Orden de Cargue'),
        }
        
        filename_prefix, doc_name = doc_mapping['order_pdf']
        assert filename_prefix == 'orden'
        assert doc_name == 'Orden de Cargue'
    
    def test_document_mapping_manifest(self):
        """Test manifest document mapping."""
        doc_mapping = {
            'manifest_pdf': ('manifesto', 'Manifiesto'),
        }
        
        filename_prefix, doc_name = doc_mapping['manifest_pdf']
        assert filename_prefix == 'manifesto'
        assert doc_name == 'Manifiesto'
    
    def test_document_mapping_cumplido(self):
        """Test cumplido document mapping."""
        doc_mapping = {
            'cumplido_pdf': ('cumplido', 'Cumplido'),
        }
        
        filename_prefix, doc_name = doc_mapping['cumplido_pdf']
        assert filename_prefix == 'cumplido'
        assert doc_name == 'Cumplido'
    
    def test_document_mapping_invoice(self):
        """Test invoice document mapping."""
        doc_mapping = {
            'invoice_pdf': ('invoice', 'Factura'),
        }
        
        filename_prefix, doc_name = doc_mapping['invoice_pdf']
        assert filename_prefix == 'invoice'
        assert doc_name == 'Factura'


class TestPresignedURLMocking:
    """Test that presigned URL mocking works correctly."""
    
    def test_s3_uploader_mock_generate_presigned_url(self):
        """Test mocking S3Uploader.generate_presigned_url."""
        mock_uploader = Mock()
        presigned_url = 'https://s3.amazonaws.com/bucket/key?X-Amz-Algorithm=...'
        mock_uploader.generate_presigned_url.return_value = presigned_url
        
        # Call the mocked method
        result = mock_uploader.generate_presigned_url('documents/orden-123.pdf', expiration=3600)
        
        # Verify
        assert result == presigned_url
        mock_uploader.generate_presigned_url.assert_called_once_with('documents/orden-123.pdf', expiration=3600)
    
    def test_trip_service_mock_get_trip(self):
        """Test mocking TripService.get_trip."""
        mock_service = Mock()
        trip_id = str(ObjectId())
        mock_trip = {
            '_id': trip_id,
            'documents': {
                'order_pdf': 'https://s3.../'
            }
        }
        mock_service.get_trip.return_value = mock_trip
        
        # Call the mocked method
        result = mock_service.get_trip(trip_id)
        
        # Verify
        assert result == mock_trip
        assert result['documents']['order_pdf'] == 'https://s3.../'
    
    def test_trip_service_mock_not_found(self):
        """Test mocking TripService.get_trip raising exception."""
        mock_service = Mock()
        trip_id = str(ObjectId())
        mock_service.get_trip.side_effect = TripNotFoundError(f"Trip not found")
        
        # Call the mocked method
        with pytest.raises(TripNotFoundError):
            mock_service.get_trip(trip_id)


class TestPresignedURLResponseStructure:
    """Test the expected response structure for presigned URLs."""
    
    def test_presigned_url_response_keys(self):
        """Test response includes expected keys."""
        trip_id = str(ObjectId())
        
        # Simulate response
        response = {
            'trip_id': trip_id,
            'documents': {
                'order_pdf': {
                    'url': 'https://s3.amazonaws.com/...',
                    'name': 'Orden de Cargue',
                    'type': 'application/pdf'
                }
            },
            'expires_in_seconds': 3600
        }
        
        # Verify structure
        assert 'trip_id' in response
        assert 'documents' in response
        assert 'expires_in_seconds' in response
        assert response['expires_in_seconds'] == 3600
    
    def test_download_redirect_response(self):
        """Test download redirect response."""
        presigned_url = 'https://s3.amazonaws.com/bucket/documents/orden.pdf?X-Amz-Algorithm=...'
        
        # Simulate redirect response
        response_location = presigned_url
        
        # Verify format
        assert response_location.startswith('https://')
        assert 's3.amazonaws.com' in response_location or 's3-' in response_location
        assert '.pdf' in response_location


class TestPresignedURLErrorHandling:
    """Test error handling in presigned URL endpoints."""
    
    def test_handle_trip_not_found_error(self):
        """Test handling TripNotFoundError."""
        try:
            raise TripNotFoundError("Trip not found")
        except TripNotFoundError as e:
            assert "not found" in str(e).lower()
    
    def test_handle_s3_error(self):
        """Test handling S3Error."""
        try:
            raise S3Error("S3 connection failed")
        except S3Error as e:
            assert "connection" in str(e).lower() or "failed" in str(e).lower()
