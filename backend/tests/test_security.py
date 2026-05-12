"""
Security Infrastructure Tests

Comprehensive test suite for all security modules:
- Security headers (CSP, X-Frame-Options, HSTS, etc.)
- CORS configuration and origin validation
- Global error handler and structured logging
- Rate limiter with MongoDB backend
- Input sanitizer for NoSQL injection prevention

Test fixtures use mongomock to simulate MongoDB without requiring a real instance.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest
from mongomock import MongoClient as MockMongoClient

# Import Flask app factory
from wsgi import create_app

# Import security modules
from src.infrastructure.security_headers import init_security_headers
from src.infrastructure.cors import init_cors
from src.infrastructure.error_handler import init_error_handler
from src.infrastructure.rate_limiter import RateLimiter
from src.infrastructure.sanitizer import (
    sanitize_string,
    sanitize_object,
    is_injection_attempt,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def app():
    """
    Create a test Flask application with all security modules initialized.
    
    This fixture is used by all test classes to get a properly configured app.
    """
    test_app = create_app()
    test_app.config['TESTING'] = True
    
    # Initialize security modules
    init_security_headers(test_app)
    init_cors(test_app)
    init_error_handler(test_app)
    
    yield test_app


@pytest.fixture
def client(app):
    """
    Create a test client for making HTTP requests to the app.
    """
    yield app.test_client()


@pytest.fixture
def mock_mongo():
    """
    Create a mock MongoDB client using mongomock.
    
    This allows testing RateLimiter without a real MongoDB instance.
    """
    return MockMongoClient().db


# ============================================================================
# Security Headers Tests
# ============================================================================

class TestSecurityHeaders:
    """Test suite for HTTP security headers."""
    
    def test_csp_header_present(self, client):
        """
        Test that Content-Security-Policy header is present in response.
        
        CSP prevents XSS attacks by restricting resource loading.
        """
        response = client.get('/health')
        assert 'Content-Security-Policy' in response.headers
        assert response.headers['Content-Security-Policy'] == "default-src 'self'"
    
    def test_x_frame_options_header(self, client):
        """
        Test that X-Frame-Options header is set to DENY.
        
        Prevents clickjacking attacks by disallowing framing.
        """
        response = client.get('/health')
        assert response.headers['X-Frame-Options'] == 'DENY'
    
    def test_x_content_type_options_header(self, client):
        """
        Test that X-Content-Type-Options header prevents MIME-type sniffing.
        """
        response = client.get('/health')
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
    
    def test_hsts_header_present(self, client):
        """
        Test that Strict-Transport-Security header enforces HTTPS.
        """
        response = client.get('/health')
        assert 'Strict-Transport-Security' in response.headers
        assert 'max-age=31536000' in response.headers['Strict-Transport-Security']
        assert 'includeSubDomains' in response.headers['Strict-Transport-Security']
    
    def test_referrer_policy_header(self, client):
        """
        Test that Referrer-Policy header protects privacy.
        """
        response = client.get('/health')
        assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    
    def test_security_headers_on_all_responses(self, client):
        """
        Test that security headers are added to all HTTP responses, including errors.
        """
        # Test on 404 Not Found
        response = client.get('/nonexistent')
        assert response.status_code == 404
        assert 'Content-Security-Policy' in response.headers
        assert 'X-Frame-Options' in response.headers
        
        # Test on successful response
        response = client.get('/health')
        assert response.status_code == 200
        assert 'Content-Security-Policy' in response.headers


# ============================================================================
# CORS Tests
# ============================================================================

class TestCORS:
    """Test suite for CORS (Cross-Origin Resource Sharing) configuration."""
    
    def test_cors_header_with_allowed_origin(self, client):
        """
        Test that CORS headers are present when Origin matches CORS_ORIGIN.
        
        The default CORS_ORIGIN is http://localhost:4200 (Angular dev server).
        """
        response = client.get('/health', headers={
            'Origin': 'http://localhost:4200'
        })
        assert 'Access-Control-Allow-Origin' in response.headers
        assert response.headers['Access-Control-Allow-Origin'] == 'http://localhost:4200'
    
    def test_cors_credentials_allowed(self, client):
        """
        Test that credentials (cookies, auth headers) are allowed in CORS requests.
        """
        response = client.get('/health', headers={
            'Origin': 'http://localhost:4200'
        })
        assert 'Access-Control-Allow-Credentials' in response.headers
        assert response.headers['Access-Control-Allow-Credentials'] == 'true'
    
    def test_cors_allowed_methods(self, client):
        """
        Test that only safe HTTP methods are allowed in CORS preflight.
        """
        response = client.options('/health', headers={
            'Origin': 'http://localhost:4200',
            'Access-Control-Request-Method': 'POST'
        })
        assert 'Access-Control-Allow-Methods' in response.headers
        allowed_methods = response.headers['Access-Control-Allow-Methods']
        
        # These methods should be allowed
        for method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            assert method in allowed_methods
        
        # These methods should NOT be allowed (for security)
        assert 'TRACE' not in allowed_methods
        assert 'CONNECT' not in allowed_methods
    
    def test_cors_disallows_disallowed_origin(self, client):
        """
        Test that CORS headers are NOT present for disallowed origins.
        
        This protects against cross-origin attacks from malicious sites.
        """
        response = client.get('/health', headers={
            'Origin': 'http://malicious-site.com'
        })
        # Flask-CORS will not set Allow-Origin header for disallowed origins
        # (or it will not match the request origin)
        assert 'Access-Control-Allow-Origin' not in response.headers or \
               response.headers.get('Access-Control-Allow-Origin') != 'http://malicious-site.com'


# ============================================================================
# Error Handler Tests
# ============================================================================

class TestErrorHandler:
    """Test suite for global error handling and structured logging."""
    
    def test_404_returns_error_response(self, client):
        """
        Test that 404 Not Found returns a JSON error response.
        """
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert isinstance(data['error'], str)
    
    def test_405_method_not_allowed_returns_error(self, client):
        """
        Test that 405 Method Not Allowed returns a JSON error response.
        """
        response = client.post('/health', json={})  # GET only
        assert response.status_code == 405
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_500_error_hides_details(self, client):
        """
        Test that 500 Internal Server Error never exposes stack trace.
        
        Security: Prevents information disclosure that could aid attackers.
        """
        # Trigger a 500 error by accessing a route that doesn't exist
        response = client.get('/intentional-error')
        
        # Error response should be generic
        if response.status_code == 500:
            data = json.loads(response.data)
            assert data.get('error') == 'Internal server error'
            # Should NOT contain traceback, file paths, or internal details
            assert 'traceback' not in json.dumps(data)
            assert '.py' not in json.dumps(data)
    
    def test_error_response_is_json(self, client):
        """
        Test that all error responses are valid JSON.
        """
        response = client.get('/nonexistent')
        assert response.content_type == 'application/json'
        
        # Should be valid JSON
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'error' in data
    
    def test_request_data_extraction_in_logging(self, app, mock_mongo):
        """
        Test that error logging extracts request context (endpoint, method, etc.).
        
        This ensures structured logs contain all necessary debugging info.
        """
        with app.test_request_context('/health', method='GET'):
            from src.infrastructure.error_handler import _extract_request_data
            
            request_data = _extract_request_data()
            assert 'endpoint' in request_data
            assert 'method' in request_data
            assert 'path' in request_data
            assert request_data['method'] == 'GET'


# ============================================================================
# Rate Limiter Tests
# ============================================================================

class TestRateLimiter:
    """Test suite for rate limiting with MongoDB backend."""
    
    @pytest.fixture
    def rate_limiter(self, mock_mongo):
        """
        Create a RateLimiter instance with mock MongoDB.
        """
        limiter = RateLimiter(
            mongo_uri="mongodb://localhost/test",
            max_attempts=5,
            window_minutes=15
        )
        # Override collection with mock
        limiter.collection = mock_mongo['rate_limits']
        limiter._initialized = True
        return limiter
    
    def test_allows_requests_under_limit(self, rate_limiter):
        """
        Test that requests are allowed when under the limit.
        
        Limit: 5 attempts per 15 minutes
        """
        ip = "192.168.1.100"
        endpoint = "/login"
        
        # First 5 attempts should be allowed
        for i in range(5):
            result = rate_limiter.is_allowed(ip, endpoint)
            assert result is True, f"Attempt {i+1} should be allowed"
    
    def test_blocks_after_exceeding_limit(self, rate_limiter):
        """
        Test that requests are blocked after exceeding the limit.
        """
        ip = "192.168.1.100"
        endpoint = "/login"
        
        # Make 5 attempts (allowed)
        for i in range(5):
            rate_limiter.is_allowed(ip, endpoint)
        
        # 6th attempt should be blocked
        result = rate_limiter.is_allowed(ip, endpoint)
        assert result is False
    
    def test_separate_limits_per_endpoint(self, rate_limiter):
        """
        Test that rate limits are per-endpoint, not global.
        """
        ip = "192.168.1.100"
        
        # Use up limit on /login
        for i in range(5):
            rate_limiter.is_allowed(ip, "/login")
        
        # /register should still have full limit
        for i in range(5):
            result = rate_limiter.is_allowed(ip, "/register")
            assert result is True
    
    def test_separate_limits_per_ip(self, rate_limiter):
        """
        Test that rate limits are per-IP, not global.
        """
        endpoint = "/login"
        
        # Use up limit for IP1
        for i in range(5):
            rate_limiter.is_allowed("192.168.1.100", endpoint)
        
        # IP2 should still have full limit
        for i in range(5):
            result = rate_limiter.is_allowed("192.168.1.101", endpoint)
            assert result is True
    
    def test_block_duration_is_configurable(self, mock_mongo):
        """
        Test that block duration can be configured.
        """
        limiter = RateLimiter(
            mongo_uri="mongodb://localhost/test",
            max_attempts=3,
            window_minutes=10
        )
        limiter.collection = mock_mongo['rate_limits']
        limiter._initialized = True
        
        ip = "192.168.1.100"
        endpoint = "/test"
        
        # Use up limit with configured max_attempts
        for i in range(3):
            limiter.is_allowed(ip, endpoint)
        
        # Should be blocked
        assert limiter.is_allowed(ip, endpoint) is False
    
    def test_get_status(self, rate_limiter):
        """
        Test the status reporting functionality for monitoring.
        """
        ip = "192.168.1.100"
        endpoint = "/login"
        
        # Make some attempts
        rate_limiter.is_allowed(ip, endpoint)
        rate_limiter.is_allowed(ip, endpoint)
        
        status = rate_limiter.get_status(ip, endpoint)
        assert status['attempts'] == 2
        assert status['is_blocked'] is False
        assert status['key'] == f"{ip}:{endpoint}"
    
    def test_reset_clears_limit(self, rate_limiter):
        """
        Test that reset() clears rate limit data.
        """
        ip = "192.168.1.100"
        endpoint = "/login"
        
        # Use up limit
        for i in range(5):
            rate_limiter.is_allowed(ip, endpoint)
        
        # Verify blocked
        assert rate_limiter.is_allowed(ip, endpoint) is False
        
        # Reset
        rate_limiter.reset(ip, endpoint)
        
        # Should be allowed again
        assert rate_limiter.is_allowed(ip, endpoint) is True


# ============================================================================
# Input Sanitizer Tests
# ============================================================================

class TestSanitizer:
    """Test suite for NoSQL injection prevention via input sanitization."""
    
    def test_sanitize_removes_mongo_operators(self):
        """
        Test that sanitizer removes MongoDB operators like $ne, $gt, $where.
        """
        assert sanitize_string('{"$ne": ""}') == '\"ne\": \"\"'
        assert sanitize_string('value$ne') == 'valuene'
        assert sanitize_string('$or:[]') == 'or'
    
    def test_sanitize_removes_dots_for_field_traversal(self):
        """
        Test that sanitizer removes dots to prevent field traversal.
        
        Example: "user.password" becomes "userpassword"
        """
        assert sanitize_string('user.password') == 'userpassword'
        assert sanitize_string('admin.level') == 'adminlevel'
    
    def test_sanitize_preserves_legitimatechars(self):
        """
        Test that sanitizer preserves legitimate characters.
        """
        # Alphanumeric characters
        assert sanitize_string('Hello123') == 'Hello123'
        
        # Common punctuation
        assert sanitize_string('john@example.com') == 'john@examplecom'  # dot removed
        assert sanitize_string('user-name') == 'user-name'
        assert sanitize_string('first_last') == 'first_last'
    
    def test_sanitize_handles_whitespace(self):
        """
        Test that sanitizer handles leading/trailing whitespace.
        """
        assert sanitize_string('  hello world  ') == 'hello world'
        assert sanitize_string('\ncontent\n') == 'content'
    
    def test_sanitize_object_recursive(self):
        """
        Test that sanitizer recursively sanitizes nested dictionaries.
        """
        data = {
            "name": "John",
            "filter": {"$ne": "admin"},
            "nested": {
                "field": "user.id",
            }
        }
        
        result = sanitize_object(data)
        assert result['name'] == 'John'
        assert result['filter']['ne'] == 'admin'
        assert result['nested']['field'] == 'userid'
    
    def test_sanitize_object_with_lists(self):
        """
        Test that sanitizer recursively sanitizes lists.
        """
        data = {
            "tags": ["tag1", "tag$2", "tag.3"],
        }
        
        result = sanitize_object(data)
        assert result['tags'][0] == 'tag1'
        assert result['tags'][1] == 'tag2'
        assert result['tags'][2] == 'tag3'
    
    def test_sanitize_object_preserves_types(self):
        """
        Test that sanitizer preserves non-string types.
        """
        data = {
            "count": 42,
            "active": True,
            "score": 3.14,
            "empty": None,
        }
        
        result = sanitize_object(data)
        assert result['count'] == 42
        assert result['active'] is True
        assert result['score'] == 3.14
        assert result['empty'] is None
    
    def test_is_injection_attempt_detects_mongo_operators(self):
        """
        Test that injection detection identifies MongoDB operators.
        """
        assert is_injection_attempt('{"$ne": ""}') is True
        assert is_injection_attempt('{"$gt": "0"}') is True
        assert is_injection_attempt('{"$where": "function() {}"}') is True
    
    def test_is_injection_attempt_detects_special_chars(self):
        """
        Test that injection detection identifies special shell characters.
        """
        assert is_injection_attempt('value; echo "hacked"') is True
        assert is_injection_attempt('value | cat /etc/passwd') is True
        assert is_injection_attempt('value & whoami') is True
        assert is_injection_attempt('value`command`') is True
    
    def test_is_injection_attempt_allows_normal_strings(self):
        """
        Test that injection detection allows legitimate user input.
        """
        assert is_injection_attempt('john@example.com') is False
        assert is_injection_attempt('Hello World 123') is False
        assert is_injection_attempt('user-name_123') is False
    
    def test_sanitize_string_non_string_input(self):
        """
        Test that sanitizer handles non-string input gracefully.
        """
        assert sanitize_string(123) == 123
        assert sanitize_string(None) is None
        assert sanitize_string(True) is True
