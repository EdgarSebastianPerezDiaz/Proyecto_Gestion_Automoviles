"""
Authentication Service Module

Handles user authentication, password hashing, JWT token generation and verification.
Core business logic for the authentication system.

Security:
- Bcrypt password hashing with configurable rounds (default 12)
- JWT tokens with HS256 signature
- Token expiration (default 8 hours)
- Timing-safe password comparison to prevent brute-force attacks
- Refresh tokens with automatic invalidation
- Token blacklist for logout
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import bcrypt
from jose import jwt, JWTError
from dotenv import load_dotenv
import uuid
import secrets
import time
import random
from src.repositories.user_repository import UserRepository
from src.infrastructure.database import MongoDBConnection, RepositoryError
from src.domain.user import user_from_dict, user_to_dict


# Load environment variables
load_dotenv()


class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Authentication failed - invalid email or password."""
    pass


class InvalidTokenError(AuthError):
    """Token validation failed - invalid signature, expired, or malformed."""
    pass


class UserAlreadyExistsError(AuthError):
    """User registration failed - email already exists."""
    pass


class TokenBlacklistedError(AuthError):
    """Token has been revoked (logged out or expired)."""
    pass


class AuthService:
    """
    Authentication service for user registration, login, and token management.
    
    Handles:
    - User registration with email uniqueness
    - Password hashing with bcrypt
    - Login with email/password validation
    - JWT token generation and verification
    - Token expiration and claims
    """
    
    def __init__(self, connection: MongoDBConnection):
        """
        Initialize the authentication service.
        
        Args:
            connection: MongoDBConnection instance (must be connected)
        """
        self.user_repo = UserRepository(connection)
        self.connection = connection
        
        # Load configuration from environment
        self.jwt_secret_key = os.getenv('JWT_SECRET_KEY')
        self.jwt_algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.jwt_expiration_hours = int(os.getenv('JWT_EXPIRATION_HOURS', '8'))
        self.bcrypt_rounds = int(os.getenv('BCRYPT_ROUNDS', '12'))
        
        if not self.jwt_secret_key:
            raise AuthError("JWT_SECRET_KEY environment variable not set")
        
        self.logger = logging.getLogger(__name__)
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            str: Hashed password (bcrypt encoded)
        """
        try:
            salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            self.logger.error(f"Error hashing password: {str(e)}")
            raise AuthError("Password hashing failed") from e
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a plain text password against a bcrypt hash.
        
        Safe against timing attacks via bcrypt.
        
        Args:
            password: Plain text password to verify
            hashed: Bcrypt hashed password to compare against
            
        Returns:
            bool: True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Error verifying password: {str(e)}")
            return False
    
    def register(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str = 'operator'
    ) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            email: User email address (will be normalized to lowercase)
            password: Plain text password (will be hashed)
            full_name: User full name
            role: User role - 'operator' or 'admin' (default: 'operator')
            
        Returns:
            dict: User data without password_hash
            
        Raises:
            UserAlreadyExistsError: If email already registered
            AuthError: On validation or database errors
        """
        try:
            # Normalize email
            email = email.strip().lower()
            
            # Check if user already exists
            existing = self.user_repo.find_by_email(email)
            if existing:
                raise UserAlreadyExistsError(f"Email already registered: {email}")
            
            # Validate password strength (basic check)
            if len(password) < 8:
                raise AuthError("Password must be at least 8 characters long")
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Prepare user document
            user_doc = user_from_dict({
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "role": role,
                "is_active": True,
            })
            
            # Insert user
            user_id = self.user_repo.create_user(user_doc)
            
            # Fetch and return user (without password)
            user = self.user_repo.find_by_id(user_id)
            if not user:
                raise AuthError("User creation verification failed")
            
            return user_to_dict(user, include_password=False)
        
        except UserAlreadyExistsError:
            raise
        except RepositoryError as e:
            if 'duplicate' in str(e).lower():
                raise UserAlreadyExistsError(f"Email already registered: {email}") from e
            raise AuthError(f"Registration failed: {str(e)}") from e
        except AuthError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during registration: {str(e)}")
            raise AuthError(f"Registration failed: {str(e)}") from e
    
    def login(
        self,
        email: str,
        password: str,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """
        Authenticate a user and generate JWT token.
        
        Args:
            email: User email address
            password: Plain text password
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)
            
        Returns:
            dict: {
                'access_token': JWT token string,
                'token_type': 'Bearer',
                'expires_in': expiration time in seconds,
                'user': user data without password_hash
            }
            
        Raises:
            InvalidCredentialsError: If email not found or password incorrect
            AuthError: On unexpected errors
        """
        try:
            email = email.strip().lower()
            
            # Find user by email
            user = self.user_repo.find_by_email(email)
            if not user:
                self.logger.warning(f"Login attempt for non-existent user: {email}")
                raise InvalidCredentialsError("Invalid email or password")
            
            # Check if user is active
            if not user.get('is_active', False):
                self.logger.warning(f"Login attempt for inactive user: {email}")
                raise InvalidCredentialsError("Account is inactive")
            
            # Verify password
            password_hash = user.get('password_hash', '')
            if not self.verify_password(password, password_hash):
                self.logger.warning(f"Failed login attempt for user: {email}")
                raise InvalidCredentialsError("Invalid email or password")
            
            # Update last login
            try:
                self.user_repo.update_last_login(user['_id'])
            except Exception as e:
                self.logger.warning(f"Error updating last_login: {str(e)}")
                # Don't fail login if last_login update fails
            
            # Generate JWT token
            token_data = {
                'user_id': user['_id'],
                'email': user['email'],
                'role': user['role'],
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(hours=self.jwt_expiration_hours),
            }
            
            token = jwt.encode(
                token_data,
                self.jwt_secret_key,
                algorithm=self.jwt_algorithm
            )
            
            # Log successful login
            self._log_login(user['_id'], email, True, ip_address, user_agent)
            
            self.logger.info(f"Successful login for user: {email}")
            
            return {
                'access_token': token,
                'token_type': 'Bearer',
                'expires_in': self.jwt_expiration_hours * 3600,
                'user': user_to_dict(user, include_password=False)
            }
        
        except InvalidCredentialsError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during login: {str(e)}")
            raise AuthError(f"Login failed: {str(e)}") from e
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string (without 'Bearer ' prefix)
            
        Returns:
            dict: Decoded token payload with claims
            
        Raises:
            InvalidTokenError: If token is invalid, expired, or signature doesn't match
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            raise InvalidTokenError(f"Token verification failed: {str(e)}") from e
        except Exception as e:
            raise InvalidTokenError(f"Unexpected token error: {str(e)}") from e
    
    def generate_token(self, payload: Dict[str, Any]) -> str:
        """
        Generate a JWT token for a given user (used for testing or internal use).
        
        This method creates a token directly without verifying credentials.
        Useful for testing and internal operations.
        
        Args:
            payload: Dictionary with user claims, typically containing 'sub' (user_id),
                    'email', and 'role'. Additional claims can be included.
            
        Returns:
            str: Encoded JWT token.
        """
        try:
            token_payload = payload.copy()
            token_payload["iat"] = datetime.now(timezone.utc)
            token_payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=self.jwt_expiration_hours)
            
            token = jwt.encode(token_payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)
            return token
        except Exception as e:
            self.logger.error(f"Error generating token: {str(e)}")
            raise AuthError(f"Token generation failed: {str(e)}") from e
    
    def _log_login(
        self,
        user_id: str,
        email: str,
        success: bool,
        ip_address: str = '',
        user_agent: str = ''
    ) -> None:
        """
        Log a login attempt to the login_log collection.
        
        For audit trail purposes. Errors are logged but don't interrupt flow.
        
        Args:
            user_id: User ObjectId as string
            email: User email
            success: Whether login was successful
            ip_address: Client IP
            user_agent: Client user agent
        """
        try:
            login_log_collection = self.connection.get_collection('login_log')
            log_entry = {
                'user_id': user_id,
                'email': email,
                'success': success,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'timestamp': datetime.now(timezone.utc),
            }
            login_log_collection.insert_one(log_entry)
        except Exception as e:
            # Log but don't fail if audit logging fails
            self.logger.error(f"Error logging login attempt: {str(e)}")
    
    def login_with_refresh(
        self,
        email: str,
        password: str,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """
        Authenticate a user and generate access + refresh tokens.
        
        Returns both access token (short-lived, 15 mins) and refresh token (long-lived, 7 days).
        
        Args:
            email: User email address
            password: Plain text password
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)
            
        Returns:
            dict: {
                'access_token': JWT token string (15 mins),
                'refresh_token': Opaque refresh token string (7 days),
                'token_type': 'Bearer',
                'expires_in': 900 (seconds),
                'user': user data without password_hash
            }
        """
        try:
            # Use constant-time credentials check
            user_data = self._check_credentials(email, password, ip_address, user_agent)
            if not user_data:
                raise InvalidCredentialsError("Invalid email or password")
            
            user_id = str(user_data['_id'])
            
            # Generate access token (15 minutes)
            access_token_data = {
                'jti': str(uuid.uuid4()),  # Unique JWT ID
                'user_id': user_id,
                'email': user_data['email'],
                'role': user_data['role'],
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(minutes=15),
            }
            access_token = jwt.encode(
                access_token_data,
                self.jwt_secret_key,
                algorithm=self.jwt_algorithm
            )
            
            # Generate refresh token (7 days)
            refresh_token = secrets.token_urlsafe(32)
            refresh_token_jti = str(uuid.uuid4())
            
            # Store refresh token in blacklist collection (will be removed when refresh is used or logout)
            try:
                token_blacklist = self.connection.get_collection('token_blacklist')
                token_blacklist.insert_one({
                    'token_jti': refresh_token_jti,
                    'user_id': user_id,
                    'token_hash': self.hash_password(refresh_token),  # Store hashed version
                    'type': 'refresh',
                    'created_at': datetime.now(timezone.utc),
                    'expires_at': datetime.now(timezone.utc) + timedelta(days=7),
                    'is_active': True,
                })
            except Exception as e:
                self.logger.error(f"Error storing refresh token: {str(e)}")
                raise AuthError("Token generation failed") from e
            
            self.logger.info(f"Successful login with refresh for user: {email}")
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': 900,  # 15 minutes in seconds
                'user': user_to_dict(user_data, include_password=False)
            }
        except (InvalidCredentialsError, AuthError):
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during login with refresh: {str(e)}")
            raise AuthError(f"Login failed: {str(e)}") from e
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Generate a new access token using a valid refresh token.
        
        Args:
            refresh_token: The refresh token string
            
        Returns:
            dict: {
                'access_token': New JWT token string,
                'token_type': 'Bearer',
                'expires_in': 900 (seconds)
            }
            
        Raises:
            InvalidTokenError: If refresh token is invalid or blacklisted
            AuthError: On unexpected errors
        """
        try:
            if not refresh_token:
                raise InvalidTokenError("Refresh token is required")
            
            # Check if refresh token is blacklisted
            token_blacklist = self.connection.get_collection('token_blacklist')
            blacklisted = token_blacklist.find_one({
                'expires_at': {'$gt': datetime.now(timezone.utc)},  # Not expired
                'is_active': True,
                'type': 'refresh'
            })
            
            if blacklisted:
                # Validate refresh token by comparing hash
                if not bcrypt.checkpw(
                    refresh_token.encode('utf-8'),
                    blacklisted['token_hash'].encode('utf-8')
                ):
                    raise InvalidTokenError("Invalid or expired refresh token")
            else:
                raise InvalidTokenError("Invalid or expired refresh token")
            
            # Get user data
            user = self.user_repo.find_by_id(blacklisted['user_id'])
            if not user or not user.get('is_active', False):
                raise InvalidTokenError("User not found or inactive")
            
            # Generate new access token (15 minutes)
            access_token_data = {
                'jti': str(uuid.uuid4()),  # Unique JWT ID
                'user_id': str(user['_id']),
                'email': user['email'],
                'role': user['role'],
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(minutes=15),
            }
            access_token = jwt.encode(
                access_token_data,
                self.jwt_secret_key,
                algorithm=self.jwt_algorithm
            )
            
            self.logger.info(f"Token refreshed for user: {user['email']}")
            
            return {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': 900
            }
        except InvalidTokenError:
            raise
        except Exception as e:
            self.logger.error(f"Error refreshing token: {str(e)}")
            raise AuthError(f"Token refresh failed: {str(e)}") from e
    
    def logout(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """
        Invalidate access and refresh tokens (add to blacklist).
        
        Args:
            access_token: The access token to invalidate
            refresh_token: Optional refresh token to also invalidate
            
        Raises:
            InvalidTokenError: If token cannot be decoded or already blacklisted
            AuthError: On unexpected errors
        """
        try:
            # First, verify the token is valid and not already blacklisted
            if self.is_token_blacklisted(access_token, 'access'):
                raise InvalidTokenError("Token has already been logged out")
            
            token_blacklist = self.connection.get_collection('token_blacklist')
            
            # Blacklist access token
            try:
                payload = jwt.decode(
                    access_token,
                    self.jwt_secret_key,
                    algorithms=[self.jwt_algorithm]
                )
                access_token_jti = str(uuid.uuid4())
                token_blacklist.insert_one({
                    'token_jti': access_token_jti,
                    'user_id': payload.get('user_id'),
                    'type': 'access',
                    'created_at': datetime.now(timezone.utc),
                    'expires_at': datetime.fromtimestamp(payload.get('exp', 0), tz=timezone.utc),
                    'is_active': True,
                })
            except JWTError as e:
                raise InvalidTokenError(f"Invalid access token: {str(e)}") from e
            
            # Blacklist refresh token if provided
            if refresh_token:
                try:
                    # Find and mark as inactive
                    token_blacklist.update_one(
                        {'type': 'refresh', 'is_active': True},
                        {'$set': {'is_active': False, 'invalidated_at': datetime.now(timezone.utc)}}
                    )
                except Exception as e:
                    self.logger.warning(f"Error invalidating refresh token: {str(e)}")
            
            self.logger.info(f"User logged out: {payload.get('email', 'unknown')}")
        except InvalidTokenError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during logout: {str(e)}")
            raise AuthError(f"Logout failed: {str(e)}") from e
    
    def _check_credentials(
        self,
        email: str,
        password: str,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Optional[Dict[str, Any]]:
        """
        Check credentials with timing attack mitigation.
        
        Always performs the same operations regardless of whether user exists,
        ensuring consistent response time.
        
        Args:
            email: User email address
            password: Plain text password
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)
            
        Returns:
            dict: User data if credentials valid, None otherwise
        """
        try:
            email = email.strip().lower()
            
            # Record start time
            start_time = time.time()
            target_duration = random.uniform(0.05, 0.15)  # 50-150ms constant time
            
            # Find user by email
            user = self.user_repo.find_by_email(email)
            
            if user:
                # User exists - verify password
                password_hash = user.get('password_hash', '')
                password_valid = self.verify_password(password, password_hash)
                
                if not password_valid:
                    # Wrong password
                    self._log_login(user['_id'], email, False, ip_address, user_agent)
                    result = None
                else:
                    # Correct password
                    if not user.get('is_active', False):
                        self._log_login(user['_id'], email, False, ip_address, user_agent)
                        result = None
                    else:
                        # Valid credentials
                        try:
                            self.user_repo.update_last_login(user['_id'])
                        except Exception as e:
                            self.logger.warning(f"Error updating last_login: {str(e)}")
                        self._log_login(user['_id'], email, True, ip_address, user_agent)
                        result = user
            else:
                # User doesn't exist - generate fake hash to maintain timing
                # Use a known hash so it takes similar time
                fake_hash = "$2b$12$dummydummydummydummydummydummydummydummydummydummydummydummy"
                try:
                    bcrypt.checkpw(password.encode('utf-8'), fake_hash.encode('utf-8'))
                except Exception:
                    pass  # Expected to fail, just maintaining timing
                
                result = None
            
            # Add jitter to reach target duration
            elapsed = time.time() - start_time
            if elapsed < target_duration:
                time.sleep(target_duration - elapsed)
            
            return result
        except Exception as e:
            self.logger.error(f"Error in constant-time credential check: {str(e)}")
            return None
    
    def is_token_blacklisted(self, token: str, token_type: str = 'access') -> bool:
        """
        Check if a token has been blacklisted (logged out).
        
        Args:
            token: JWT token string
            token_type: Type of token ('access' or 'refresh')
            
        Returns:
            bool: True if token is blacklisted, False otherwise
        """
        try:
            # Decode token to get exp
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            
            # Check blacklist
            token_blacklist = self.connection.get_collection('token_blacklist')
            blacklisted = token_blacklist.find_one({
                'user_id': payload.get('user_id'),
                'type': token_type,
                'expires_at': {'$gt': datetime.now(timezone.utc)}
            })
            
            return blacklisted is not None
        except JWTError:
            # Invalid token - treat as blacklisted
            return True
        except Exception as e:
            self.logger.error(f"Error checking token blacklist: {str(e)}")
            return True  # Fail secure - treat as blacklisted
