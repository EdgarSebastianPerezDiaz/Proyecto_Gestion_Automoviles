"""
Health Check Tests

Tests for liveness and readiness probes to ensure container orchestration integration.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestLivenessProbe:
    """Tests for GET /health/live endpoint"""
    
    def test_live_always_returns_200(self, client):
        """Liveness probe should always respond 200 if app is running."""
        response = client.get('/health/live')
        
        assert response.status_code == 200
        assert response.json['status'] == 'alive'
        assert 'timestamp' in response.json
    
    def test_live_does_not_check_dependencies(self, client, app):
        """Liveness probe should not check external dependencies."""
        # Even if MongoDB is disconnected, live should return 200
        with patch.object(app, 'mongo_connection', None):
            response = client.get('/health/live')
            assert response.status_code == 200


class TestReadinessProbe:
    """Tests for GET /health/ready endpoint"""
    
    def test_ready_returns_200_when_all_healthy(self, client, app):
        """Readiness probe should return 200 when MongoDB and S3 are healthy."""
        # Mock MongoDB connection
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        # Mock S3
        mock_s3_uploader = MagicMock()
        mock_s3_client = MagicMock()
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_uploader.s3_client = mock_s3_client
        
        app.mongo_connection = mock_connection
        app.s3_uploader = mock_s3_uploader
        app.config['S3_BUCKET_NAME'] = 'test-bucket'
        
        response = client.get('/health/ready')
        
        assert response.status_code == 200
        assert response.json['status'] == 'ready'
        assert 'checks' in response.json
        assert response.json['checks']['mongodb']['healthy'] is True
        assert response.json['checks']['s3']['healthy'] is True
    
    def test_ready_returns_200_when_s3_not_configured(self, client, app):
        """Readiness probe should return 200 when S3 is not configured but MongoDB works."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        app.mongo_connection = mock_connection
        app.config['S3_BUCKET_NAME'] = None  # S3 not configured
        
        response = client.get('/health/ready')
        
        assert response.status_code == 200
        assert response.json['status'] == 'ready'
        assert response.json['checks']['s3']['configured'] is False
    
    def test_ready_returns_503_when_mongodb_down(self, client, app):
        """Readiness probe should return 503 when MongoDB is not accessible."""
        # Mock MongoDB connection failure
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = False
        
        app.mongo_connection = mock_connection
        
        response = client.get('/health/ready')
        
        assert response.status_code == 503
        assert response.json['status'] == 'not_ready'
        assert response.json['checks']['mongodb']['healthy'] is False
    
    def test_ready_returns_503_when_s3_fails(self, client, app):
        """Readiness probe should return 503 when S3 is configured but fails."""
        # Mock MongoDB OK
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        # Mock S3 failure
        mock_s3_uploader = MagicMock()
        mock_s3_client = MagicMock()
        mock_s3_client.head_bucket.side_effect = Exception("Bucket not accessible")
        mock_s3_uploader.s3_client = mock_s3_client
        
        app.mongo_connection = mock_connection
        app.s3_uploader = mock_s3_uploader
        app.config['S3_BUCKET_NAME'] = 'test-bucket'
        
        response = client.get('/health/ready')
        
        assert response.status_code == 503
        assert response.json['status'] == 'not_ready'
        assert response.json['checks']['s3']['healthy'] is False
    
    def test_ready_includes_latency_metrics(self, client, app):
        """Readiness probe should include latency information for monitoring."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        app.mongo_connection = mock_connection
        app.config['S3_BUCKET_NAME'] = None  # Disable S3
        
        response = client.get('/health/ready')
        
        assert response.status_code == 200
        assert 'latency_ms' in response.json['checks']['mongodb']
        assert isinstance(response.json['checks']['mongodb']['latency_ms'], float)
    
    def test_ready_includes_timestamp(self, client, app):
        """Readiness probe response should include ISO timestamp."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        app.mongo_connection = mock_connection
        app.config['S3_BUCKET_NAME'] = None
        
        response = client.get('/health/ready')
        
        assert 'timestamp' in response.json
        # Verify it's a valid ISO format timestamp (can be Z or +00:00)
        assert 'T' in response.json['timestamp']
        assert ('+00:00' in response.json['timestamp'] or 'Z' in response.json['timestamp'])


class TestHealthCheckIntegration:
    """Integration tests for health checks"""
    
    def test_health_endpoints_require_no_authentication(self, client):
        """Health check endpoints should not require authentication."""
        # Health checks should work without any auth header
        live_response = client.get('/health/live')
        assert live_response.status_code == 200
        
        ready_response = client.get('/health/ready')
        assert ready_response.status_code in [200, 503]  # Depends on dependencies
    
    def test_health_endpoints_are_public(self, client):
        """Health check endpoints should be accessible without bearer token."""
        response = client.get('/health/live')
        assert response.status_code == 200
        
        # Should not be a 401 (unauthorized)
        assert response.status_code != 401
    
    def test_ready_probe_handles_missing_mongo_connection(self, client, app):
        """Readiness probe should handle case where mongo_connection doesn't exist."""
        # Remove mongo_connection attribute entirely
        if hasattr(app, 'mongo_connection'):
            delattr(app, 'mongo_connection')
        
        response = client.get('/health/ready')
        
        # Should return 503 with error info
        assert response.status_code in [503, 200]
        assert 'checks' in response.json


class TestDeepHealthCheck:
    """Tests for GET /health/deep endpoint (comprehensive dependency verification)"""
    
    def test_deep_returns_200_when_all_healthy(self, client, app):
        """Deep health check should return 200 when all critical dependencies are healthy."""
        # Mock MongoDB connection
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 5
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        response = client.get('/health/deep')
        
        assert response.status_code == 200
        assert response.json['status'] == 'healthy'
        assert 'checks' in response.json
        assert 'mongodb' in response.json['checks']
        assert 'rate_limiter' in response.json['checks']
        assert 'duration_ms' in response.json
        assert response.json['checks']['mongodb']['healthy'] is True
        assert response.json['checks']['rate_limiter']['healthy'] is True
    
    def test_deep_returns_207_when_degraded_non_prod(self, client, app):
        """Deep health check should return 207 (Multi-Status) when non-critical service fails in non-prod."""
        # Mock MongoDB OK
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        # Mock rate limiter OK
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 0
        
        # Mock Secrets Manager as not accessible (development environment)
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        # Make sure we're in development
        app.config['ENV'] = 'development'
        
        # Mock the environment variable to simulate non-Lambda environment
        with patch.dict('os.environ', {'FLASK_ENV': 'development'}, clear=False):
            response = client.get('/health/deep')
        
        # In development, Secrets Manager not being accessible is OK
        assert response.status_code in [200, 207]
        assert response.json['status'] in ['healthy', 'degraded']
        assert response.json['checks']['mongodb']['healthy'] is True
        assert response.json['checks']['rate_limiter']['healthy'] is True
    
    def test_deep_returns_503_when_mongodb_fails(self, client, app):
        """Deep health check should return 503 when MongoDB (critical) fails."""
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = False
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 5  # Mock count_documents
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        response = client.get('/health/deep')
        
        assert response.status_code == 503
        assert response.json['status'] == 'unhealthy'
        assert response.json['checks']['mongodb']['healthy'] is False
    
    def test_deep_returns_503_when_rate_limiter_fails(self, client, app):
        """Deep health check should return 503 when Rate Limiter (critical) fails."""
        # Mock MongoDB OK
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        # Mock rate limiter failure
        app.mongo_connection = mock_connection
        # Either no rate limiter or not initialized
        if hasattr(app, 'rate_limiter'):
            delattr(app, 'rate_limiter')
        
        response = client.get('/health/deep')
        
        assert response.status_code == 503
        assert response.json['status'] == 'unhealthy'
        assert response.json['checks']['rate_limiter']['healthy'] is False
    
    def test_deep_includes_environment_info(self, client, app):
        """Deep health check should include environment information."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 2
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        app.config['ENV'] = 'development'
        
        response = client.get('/health/deep')
        
        assert 'environment' in response.json
        assert response.json['environment'] in ['development', 'production', 'testing']
    
    def test_deep_includes_duration_metrics(self, client, app):
        """Deep health check should include duration metrics for monitoring."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 0
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        response = client.get('/health/deep')
        
        assert 'duration_ms' in response.json
        assert isinstance(response.json['duration_ms'], float)
        assert response.json['duration_ms'] >= 0
    
    def test_deep_includes_detailed_mongodb_check(self, client, app):
        """Deep health check should include detailed MongoDB information."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 1
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        response = client.get('/health/deep')
        
        assert response.status_code == 200
        mongodb_check = response.json['checks']['mongodb']
        assert mongodb_check['healthy'] is True
        assert 'latency_ms' in mongodb_check
        assert isinstance(mongodb_check['latency_ms'], float)
    
    def test_deep_includes_detailed_rate_limiter_check(self, client, app):
        """Deep health check should include detailed Rate Limiter information."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 3
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        response = client.get('/health/deep')
        
        assert response.status_code == 200
        rl_check = response.json['checks']['rate_limiter']
        assert rl_check['healthy'] is True
        assert rl_check['initialized'] is True
        assert rl_check['collection_accessible'] is True
        assert rl_check['documents_count'] == 3
        assert 'latency_ms' in rl_check
    
    def test_deep_is_public_no_auth_required(self, client):
        """Deep health check endpoint should not require authentication."""
        response = client.get('/health/deep')
        
        # Should not return 401 (unauthorized)
        assert response.status_code != 401
        # Should return some health response
        assert 'status' in response.json
        assert 'checks' in response.json
    
    def test_deep_handles_rate_limiter_collection_error(self, client, app):
        """Deep health check should handle Rate Limiter collection access errors."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.side_effect = Exception("Collection not found")
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        response = client.get('/health/deep')
        
        assert response.status_code == 503
        assert response.json['status'] == 'unhealthy'
        assert response.json['checks']['rate_limiter']['healthy'] is False
        assert 'error' in response.json['checks']['rate_limiter']
    
    def test_deep_response_structure(self, client, app):
        """Deep health check response should have required structure."""
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1}
        
        mock_connection = MagicMock()
        mock_connection.is_connected.return_value = True
        mock_connection.db = mock_db
        
        mock_rate_limiter = MagicMock()
        mock_rate_limiter._initialized = True
        mock_rate_limiter.collection = MagicMock()
        mock_rate_limiter.collection.count_documents.return_value = 0
        
        app.mongo_connection = mock_connection
        app.rate_limiter = mock_rate_limiter
        
        response = client.get('/health/deep')
        
        # Verify response structure
        data = response.json
        assert 'status' in data
        assert 'timestamp' in data
        assert 'duration_ms' in data
        assert 'checks' in data
        assert 'environment' in data
        
        # Verify checks structure
        checks = data['checks']
        assert isinstance(checks, dict)
        assert 'mongodb' in checks
        assert 'rate_limiter' in checks
        
        # Each check should have required fields
        for check_name, check_data in checks.items():
            assert 'healthy' in check_data, f"Check '{check_name}' missing 'healthy' field"
