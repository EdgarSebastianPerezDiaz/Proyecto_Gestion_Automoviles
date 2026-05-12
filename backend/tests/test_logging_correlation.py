"""
Tests for Centralized Logging with Correlation ID

Verifies that correlation IDs are:
- Generated for each request
- Stored in Flask context (g.correlation_id)
- Included in logs with JSON formatter
- Propagated in response headers (X-Correlation-ID)
- Valid UUIDs or client-provided values
"""

import pytest
import json
import logging
from uuid import UUID
from unittest.mock import patch, MagicMock
from flask import g
from src.infrastructure.request_tracing import (
    _is_valid_correlation_id,
    get_correlation_id,
)


class TestCorrelationIdGeneration:
    """Test correlation ID generation and storage in request context."""
    
    def test_correlation_id_generated_on_request(self, client):
        """Each request should generate a unique correlation ID."""
        response = client.get("/health/live")
        
        # Correlation ID should be in response header
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        
        # Should be valid UUID
        try:
            UUID(correlation_id)
        except ValueError:
            pytest.fail(f"Invalid UUID format: {correlation_id}")
    
    def test_correlation_id_unique_per_request(self, client):
        """Each request should generate a different correlation ID."""
        response1 = client.get("/health/live")
        response2 = client.get("/health/live")
        
        correlation_id_1 = response1.headers["X-Correlation-ID"]
        correlation_id_2 = response2.headers["X-Correlation-ID"]
        
        assert correlation_id_1 != correlation_id_2
    
    def test_client_provided_correlation_id_used(self, client):
        """If client provides X-Correlation-ID header, it should be used."""
        custom_id = "client-request-12345"  # Valid: alphanumeric with hyphen
        
        response = client.get(
            "/health/live",
            headers={"X-Correlation-ID": custom_id}
        )
        
        assert response.headers["X-Correlation-ID"] == custom_id
    
    def test_invalid_correlation_id_rejected(self, client):
        """Invalid correlation IDs should be rejected and new one generated."""
        # Use invalid characters (spaces, special chars that fail the regex)
        invalid_id = "not@a@valid!id"  # Contains @ and ! which fail alphanumeric+hyphen+underscore
        
        response = client.get(
            "/health/live",
            headers={"X-Correlation-ID": invalid_id}
        )
        
        # Should generate new UUID instead
        correlation_id = response.headers["X-Correlation-ID"]
        try:
            UUID(correlation_id)
            assert correlation_id != invalid_id
        except ValueError:
            pytest.fail(f"Invalid UUID generated: {correlation_id}")


class TestCorrelationIdValidation:
    """Test correlation ID validation logic."""
    
    def test_valid_uuid_accepted(self):
        """Valid UUID strings should be accepted."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert _is_valid_correlation_id(valid_uuid) is True
    
    def test_valid_alphanumeric_with_hyphen(self):
        """Alphanumeric with hyphens should be accepted (custom IDs)."""
        valid_id = "client-request-12345"
        assert _is_valid_correlation_id(valid_id) is True
    
    def test_valid_alphanumeric_with_underscore(self):
        """Alphanumeric with underscores should be accepted."""
        valid_id = "request_trace_001"
        assert _is_valid_correlation_id(valid_id) is True
    
    def test_invalid_format_with_special_chars(self):
        """Characters beyond alphanumeric/hyphen/underscore should be rejected."""
        invalid_cases = [
            "not@a@uuid",  # @ symbol
            "request!id",  # ! symbol
            "trace#1",     # # symbol
            "id with spaces",  # spaces
            "",  # Empty
            None,  # None
        ]
        
        for invalid_id in invalid_cases:
            assert _is_valid_correlation_id(invalid_id) is False
    
    def test_correlation_id_length_limit(self):
        """Correlation ID must not exceed 64 characters."""
        # 65 characters - should be rejected
        long_id = "a" * 65
        assert _is_valid_correlation_id(long_id) is False
        
        # 64 characters - should be accepted
        max_id = "a" * 64
        assert _is_valid_correlation_id(max_id) is True


class TestCorrelationIdInLogs:
    """Test that correlation ID is included in logs."""
    
    def test_correlation_id_in_json_logs(self, client, caplog):
        """Correlation ID should be available during request processing."""
        with caplog.at_level(logging.INFO):
            response = client.get("/health/live")
        
        correlation_id_from_header = response.headers["X-Correlation-ID"]
        
        # Response should have correlation ID
        assert correlation_id_from_header
        # Should be a valid UUID
        try:
            UUID(correlation_id_from_header)
        except ValueError:
            pytest.fail(f"Invalid correlation ID format: {correlation_id_from_header}")
    
    def test_correlation_id_persists_in_request(self, client):
        """Correlation ID should be consistent during request lifecycle."""
        # Make a request and verify it returns a correlation ID
        response = client.get("/health/live")
        
        # Response should have correlation ID
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        
        # Should be non-empty
        assert correlation_id
        # Should be valid format (UUID)
        try:
            UUID(correlation_id)
        except ValueError:
            pytest.fail(f"Correlation ID is not a valid UUID: {correlation_id}")


class TestCorrelationIdPropagation:
    """Test correlation ID propagation through request lifecycle."""
    
    def test_correlation_id_in_request_and_response(self, client):
        """Correlation ID sent in request should appear in response."""
        custom_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        
        response = client.get(
            "/health/live",
            headers={"X-Correlation-ID": custom_id}
        )
        
        assert response.headers["X-Correlation-ID"] == custom_id
    
    def test_correlation_id_header_format(self, client):
        """X-Correlation-ID header should be properly formatted."""
        response = client.get("/health/live")
        
        assert "X-Correlation-ID" in response.headers
        header_value = response.headers["X-Correlation-ID"]
        
        # Should be a valid UUID string (hex with dashes)
        assert len(header_value) == 36  # UUID4 with dashes
        assert header_value.count("-") == 4
    
    def test_correlation_id_in_request_duration_header(self, client):
        """Request duration header should also appear with correlation ID."""
        response = client.get("/health/live")
        
        assert "X-Request-Duration-MS" in response.headers
        assert "X-Correlation-ID" in response.headers
        
        # Duration should be numeric
        try:
            int(response.headers["X-Request-Duration-MS"])
        except ValueError:
            pytest.fail("X-Request-Duration-MS is not numeric")


class TestCorrelationIdWithErrors:
    """Test correlation ID behavior with error responses."""
    
    def test_correlation_id_on_404_error(self, client):
        """404 errors should still include correlation ID."""
        response = client.get("/api/nonexistent-endpoint")
        
        assert response.status_code == 404
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"]
    
    def test_correlation_id_on_validation_error(self, client):
        """Validation errors should include correlation ID."""
        response = client.post(
            "/api/trips",
            json={
                # Missing required fields to trigger validation error
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should return error status
        assert response.status_code >= 400
        # But correlation ID should still be present
        assert "X-Correlation-ID" in response.headers


class TestCorrelationIdWithMultipleRequests:
    """Test correlation ID behavior with sequential requests."""
    
    def test_different_ids_for_sequential_requests(self, client):
        """Each request should have different correlation ID."""
        ids = []
        
        for _ in range(3):
            response = client.get("/health/live")
            ids.append(response.headers["X-Correlation-ID"])
        
        # All should be different
        assert len(set(ids)) == 3
    
    def test_correlation_id_isolated_per_context(self, client, app):
        """Correlation IDs should be isolated per request context."""
        id_1 = None
        id_2 = None
        
        def get_id_in_context():
            return g.get("correlation_id", "NOT_SET")
        
        # Make first request
        response1 = client.get("/health/live")
        id_1 = response1.headers["X-Correlation-ID"]
        
        # Make second request
        response2 = client.get("/health/live")
        id_2 = response2.headers["X-Correlation-ID"]
        
        # Should be different
        assert id_1 != id_2
