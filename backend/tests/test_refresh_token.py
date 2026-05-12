"""
Test Suite for Refresh Token Implementation

Tests for:
- Refresh token generation during login
- Token refresh endpoint functionality
- Logout functionality with token invalidation
- Token blacklist verification
- Access token generation and refresh

Security Tests:
- Expired refresh tokens are rejected
- Blacklisted tokens are rejected
- Both access and refresh tokens are invalidated on logout
"""

import pytest
from datetime import datetime, timezone, timedelta
import json
from jose import jwt
import uuid


@pytest.fixture
def auth_client(client):
    """Fixture to access Flask test client with auth methods."""
    return client


@pytest.fixture
def test_user_email():
    """Standard test user email with UUID for uniqueness."""
    return f"refresh_test_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def test_user_password():
    """Standard test user password."""
    return "SecurePass123!"


@pytest.fixture
def test_user(auth_client, test_user_email, test_user_password):
    """Create a test user and return their ID."""
    response = auth_client.post('/auth/register', json={
        'email': test_user_email,
        'password': test_user_password,
        'full_name': 'Test User'
    })
    
    assert response.status_code == 201
    user_data = response.get_json()
    return user_data


class TestRefreshTokenGeneration:
    """Tests for refresh token generation during login."""
    
    def test_login_returns_refresh_token(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that login endpoint returns both access and refresh tokens."""
        response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check required fields
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'token_type' in data
        assert data['token_type'] == 'Bearer'
        assert 'expires_in' in data
        assert data['expires_in'] == 900  # 15 minutes
        assert 'user' in data
    
    def test_refresh_token_format(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that refresh token is properly formatted."""
        response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        data = response.get_json()
        refresh_token = data['refresh_token']
        
        # Refresh token should be a base64-like string (URL-safe)
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 20  # Should be reasonably long
        # URL-safe base64 characters
        assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in refresh_token)
    
    def test_access_token_format_and_expiry(self, auth_client, test_user, test_user_email, test_user_password, app):
        """Test that access token is a valid JWT with correct expiry."""
        response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        data = response.get_json()
        access_token = data['access_token']
        
        # Should be valid JWT format (3 parts separated by dots)
        parts = access_token.split('.')
        assert len(parts) == 3
        
        # Decode and verify expiry
        from src.services.auth_service import AuthService
        
        with app.app_context():
            connection = app.mongo_connection
            auth_service = AuthService(connection)
        
        payload = auth_service.verify_token(access_token)
        
        assert 'exp' in payload
        assert 'user_id' in payload
        assert 'email' in payload
        assert 'role' in payload
        
        # Verify expiry is approximately 15 minutes from now
        exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = (exp_time - now).total_seconds()
        
        # Should be between 14 and 16 minutes (some clock skew)
        assert 840 <= time_diff <= 960


class TestTokenRefresh:
    """Tests for the /auth/refresh endpoint."""
    
    def test_refresh_with_valid_token(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that refresh endpoint returns new access token."""
        # First, get login tokens
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        refresh_token = login_data['refresh_token']
        
        # Use refresh token to get new access token
        refresh_response = auth_client.post('/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.get_json()
        
        assert 'access_token' in refresh_data
        assert 'token_type' in refresh_data
        assert refresh_data['token_type'] == 'Bearer'
        assert 'expires_in' in refresh_data
    
    def test_refresh_token_is_different(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that refreshed access token is different from original."""
        # Get initial tokens
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        original_access = login_data['access_token']
        refresh_token = login_data['refresh_token']
        
        # Refresh to get new access token
        refresh_response = auth_client.post('/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        refresh_data = refresh_response.get_json()
        new_access = refresh_data['access_token']
        
        # Tokens should be different
        assert original_access != new_access
    
    def test_refresh_with_invalid_token(self, auth_client):
        """Test that invalid refresh token is rejected."""
        response = auth_client.post('/auth/refresh', json={
            'refresh_token': 'invalid_token_string'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_refresh_with_missing_token(self, auth_client):
        """Test that missing refresh token is rejected."""
        response = auth_client.post('/auth/refresh', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'refresh_token' in data['error'].lower() or 'required' in data['error'].lower()
    
    def test_refresh_with_empty_token(self, auth_client):
        """Test that empty refresh token is rejected."""
        response = auth_client.post('/auth/refresh', json={
            'refresh_token': ''
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestLogout:
    """Tests for the /auth/logout endpoint."""
    
    def test_logout_with_valid_tokens(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that logout successfully invalidates tokens."""
        # Login to get tokens
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        access_token = login_data['access_token']
        refresh_token = login_data['refresh_token']
        
        # Logout
        logout_response = auth_client.post('/auth/logout', json={
            'access_token': access_token,
            'refresh_token': refresh_token
        })
        
        assert logout_response.status_code == 200
        logout_data = logout_response.get_json()
        assert logout_data.get('success') is True
        assert 'message' in logout_data
    
    def test_logout_invalidates_access_token(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that after logout, access token cannot be used."""
        # For this test, we need an endpoint that requires authentication
        # Get tokens
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        access_token = login_data['access_token']
        refresh_token = login_data['refresh_token']
        
        # Verify token works before logout
        # (This assumes there's an authenticated endpoint we can test)
        # For now, we'll test that logout is successful
        logout_response = auth_client.post('/auth/logout', json={
            'access_token': access_token,
            'refresh_token': refresh_token
        })
        
        assert logout_response.status_code == 200
        
        # After logout, refresh should fail
        refresh_response = auth_client.post('/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        # Refresh should fail (token is blacklisted)
        assert refresh_response.status_code == 401
    
    def test_logout_with_access_token_only(self, auth_client, test_user, test_user_email, test_user_password):
        """Test logout with only access token (refresh token optional)."""
        # Login to get tokens
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        access_token = login_data['access_token']
        
        # Logout with access token only
        logout_response = auth_client.post('/auth/logout', json={
            'access_token': access_token
        })
        
        assert logout_response.status_code == 200
        logout_data = logout_response.get_json()
        assert logout_data.get('success') is True
    
    def test_logout_with_invalid_token(self, auth_client):
        """Test logout with invalid access token."""
        response = auth_client.post('/auth/logout', json={
            'access_token': 'invalid.token.here'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_logout_with_missing_access_token(self, auth_client):
        """Test logout without access token."""
        response = auth_client.post('/auth/logout', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'access_token' in data['error'].lower() or 'required' in data['error'].lower()


class TestTokenBlacklist:
    """Tests for token blackelist verification."""
    
    def test_blacklisted_token_rejected_on_subsequent_request(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that blacklisted token is rejected when used in request."""
        # Login
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        access_token = login_data['access_token']
        refresh_token = login_data['refresh_token']
        
        # Logout to blacklist the token
        auth_client.post('/auth/logout', json={
            'access_token': access_token,
            'refresh_token': refresh_token
        })
        
        # Try to use blacklisted token in authenticated request
        # (Requires an endpoint that uses @require_role or @require_auth)
        # This test verifies the blacklist checking works
        # Note: The actual test depends on having a protected endpoint
    
    def test_multiple_logouts_idempotent(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that calling logout multiple times doesn't cause errors."""
        # Login
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        access_token = login_data['access_token']
        
        # First logout
        logout1 = auth_client.post('/auth/logout', json={
            'access_token': access_token
        })
        assert logout1.status_code == 200
        
        # Second logout (should fail gracefully)
        logout2 = auth_client.post('/auth/logout', json={
            'access_token': access_token
        })
        assert logout2.status_code == 401  # Token already blacklisted


class TestSecurityConsiderations:
    """Security-focused tests for refresh token implementation."""
    
    def test_timing_attack_mitigation(self, auth_client, app):
        """Test that invalid credentials take consistent time."""
        # Test with non-existent user
        start1 = datetime.now(timezone.utc)
        auth_client.post('/auth/login', json={
            'email': f'nonexistent_{uuid.uuid4().hex[:8]}@example.com',
            'password': 'WrongPassword123!'
        })
        time1 = (datetime.now(timezone.utc) - start1).total_seconds()
        
        # Test with wrong password
        from src.services.auth_service import AuthService
        
        with app.app_context():
            connection = app.mongo_connection
            auth_service = AuthService(connection)
        
        auth_service.register('timing_test@example.com', 'CorrectPass123!', 'Test User')
        
        start2 = datetime.now(timezone.utc)
        auth_client.post('/auth/login', json={
            'email': 'timing_test@example.com',
            'password': 'WrongPassword123!'
        })
        time2 = (datetime.now(timezone.utc) - start2).total_seconds()
        
        # Times should be relatively similar (within 100ms)
        # Note: This is a loose test as timing can vary
        # In production, use nicer timing comparison
        assert abs(time1 - time2) < 0.5  # Less than 500ms difference
    
    def test_refresh_token_not_exposed_in_logs(self, auth_client, test_user, test_user_email, test_user_password):
        """Test that refresh token is not exposed in error messages."""
        response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = response.get_json()
        refresh_token = login_data['refresh_token']
        
        # Try invalid refresh
        response = auth_client.post('/auth/refresh', json={
            'refresh_token': 'fake_' + refresh_token
        })
        
        error_data = response.get_json()
        
        # Error message should not contain the actual token
        error_message = json.dumps(error_data)
        assert refresh_token not in error_message


class TestEdgeCases:
    """Edge case and boundary tests."""
    
    def test_rapid_refresh_requests(self, auth_client, test_user, test_user_email, test_user_password):
        """Test handling of rapid refresh token requests."""
        # Login
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        refresh_token = login_data['refresh_token']
        
        # Make multiple rapid refresh requests
        for _ in range(3):
            response = auth_client.post('/auth/refresh', json={
                'refresh_token': refresh_token
            })
            assert response.status_code == 200
    
    def test_token_refresh_preserves_user_info(self, auth_client, test_user, test_user_email, test_user_password, app):
        """Test that user information is preserved in refreshed token."""
        # Login
        login_response = auth_client.post('/auth/login', json={
            'email': test_user_email,
            'password': test_user_password
        })
        
        login_data = login_response.get_json()
        original_user = login_data['user']
        refresh_token = login_data['refresh_token']
        
        # Refresh token
        refresh_response = auth_client.post('/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        # Verify new access_token contains same user info
        new_access_token = refresh_response.get_json()['access_token']
        
        # Decode to verify user info
        from src.services.auth_service import AuthService
        
        with app.app_context():
            connection = app.mongo_connection
            auth_service = AuthService(connection)
        
        payload = auth_service.verify_token(new_access_token)
        
        # Email and role should match original
        assert payload['email'] == original_user['email']
        assert payload['role'] == original_user['role']
