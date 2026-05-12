"""
Health Endpoint Tests

Test suite for the health check endpoint.
This endpoint is used by container orchestration and load balancers
to verify the service is operational.
"""

import json
import pytest
from wsgi import create_app


@pytest.fixture
def client():
    """
    Fixture: Flask test client for testing the health endpoint.
    
    Yields:
        FlaskClient: Test client for making HTTP requests
    """
    app = create_app()
    app.config['TESTING'] = True
    yield app.test_client()


class TestHealthEndpoint:
    """Test suite for GET /health endpoint"""
    
    def test_health_endpoint_returns_200(self, client):
        """
        Test that health endpoint returns HTTP 200 status code.
        
        Expected: GET /health -> 200 OK
        """
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_health_endpoint_returns_ok_message(self, client):
        """
        Test that health endpoint returns the expected JSON response.
        
        Expected: {"message": "ok"}
        """
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['message'] == 'ok'
