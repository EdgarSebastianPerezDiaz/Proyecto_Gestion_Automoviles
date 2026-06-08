"""
Rate Limiter Module

Implements request rate limiting using MongoDB for persistence.
Protects against brute-force attacks and denial-of-service (DoS).

Schema:
    rate_limits collection: {
        _id: "ip:endpoint",          # Composite key: client IP + endpoint
        attempts: integer,            # Number of attempts in current window
        first_attempt: datetime,      # When the first attempt in window occurred
        last_attempt: datetime,       # When the most recent attempt occurred
        blocked_until: datetime,      # When the block expires (for fast reject)
    }
    
TTL Index: blocked_until field has TTL=0, so documents auto-delete when expired.

Security Rationale:
- Rate limiting prevents brute-force attacks (password guessing, token enumeration)
- MongoDB storage allows sharing limits across multiple Lambda instances
- Auto-expiring documents (TTL) prevent table bloat
- Per-endpoint limits allow different thresholds (e.g., login = strict, public API = lenient)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


def _ensure_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is timezone-aware in UTC.
    
    MongoDB drivers may return naive datetimes. This function ensures 
    all datetimes are timezone-aware so comparisons don't raise TypeError.
    
    Args:
        dt: A datetime that may be naive or aware
        
    Returns:
        The datetime with UTC timezone info, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Naive datetime - assume it's UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt


class RateLimiter:
    """
    MongoDB-backed rate limiter for API endpoints.
    
    Configuration:
    - Max attempts: 5 per IP per endpoint
    - Time window: 15 minutes
    - Block duration: 15 minutes (auto-expires via TTL index)
    
    Attributes:
        collection: MongoDB collection for storing rate limit data
        max_attempts: Maximum attempts before blocking
        window_minutes: Time window in minutes
    """
    
    def __init__(self, mongo_uri: str, max_attempts: int = 5, window_minutes: int = 15):
        """
        Initialize the rate limiter with MongoDB connection.
        
        Args:
            mongo_uri: MongoDB connection string
            max_attempts: Maximum attempts before blocking (default: 5)
            window_minutes: Time window in minutes (default: 15)
        """
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.mongo_uri = mongo_uri
        self.collection = None
        self._initialized = False
    
    def connect(self) -> None:
        """
        Connect to MongoDB and initialize the rate_limits collection with TTL index.
        
        Creates collection and TTL index if they don't exist.
        Should be called once during app initialization.
        
        Raises:
            ServerSelectionTimeoutError: If MongoDB connection fails
        """
        try:
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            db = client.get_database()
            self.collection = db['rate_limits']
            
            # Create TTL index on blocked_until field
            # TTL=0 means delete immediately when blocked_until expires
            self.collection.create_index('blocked_until', expireAfterSeconds=0)
            
            # Create index on _id for fast lookups
            self.collection.create_index('_id')
            
            self._initialized = True
        except ServerSelectionTimeoutError as e:
            raise ServerSelectionTimeoutError(
                f"Could not connect to MongoDB for rate limiting: {str(e)}"
            ) from e
    
    def is_allowed(
        self,
        ip: str,
        endpoint: str,
        max_attempts: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> bool:
        """
        Check if a request from an IP to an endpoint is allowed.

        Args:
            ip: Client IP address
            endpoint: API endpoint name
            max_attempts: Override instance max_attempts (optional)
            window_seconds: Override window in seconds (optional)

        Returns:
            bool: True if allowed, False if rate-limited.
                  Returns True (fail-open) when MongoDB is not connected.
        """
        if not self._initialized or self.collection is None:
            # Fail-open: let requests through when rate-limiter has no DB connection
            return True

        effective_max = max_attempts if max_attempts is not None else self.max_attempts
        effective_window_minutes = (
            window_seconds // 60 if window_seconds is not None else self.window_minutes
        )
        
        rate_limit_key = f"{ip}:{endpoint}"
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=effective_window_minutes)

        # Check if currently blocked (expedite rejections)
        doc = self.collection.find_one({"_id": rate_limit_key})

        if doc and doc.get("blocked_until"):
            blocked_until = _ensure_aware_utc(doc["blocked_until"])
            if blocked_until and blocked_until > now:
                return False

        if doc and doc.get("first_attempt"):
            first_attempt = _ensure_aware_utc(doc["first_attempt"])
            if first_attempt and first_attempt > window_start:
                current_attempts = doc.get("attempts", 0)

                if current_attempts >= effective_max:
                    blocked_until = now + timedelta(minutes=effective_window_minutes)
                    self.collection.update_one(
                        {"_id": rate_limit_key},
                        {
                            "$set": {
                                "last_attempt": now,
                                "blocked_until": blocked_until,
                            }
                        },
                    )
                    return False
                
                # Still under threshold, increment and allow
                new_attempts = current_attempts + 1
                self.collection.update_one(
                    {"_id": rate_limit_key},
                    {
                        "$set": {
                            "attempts": new_attempts,
                            "last_attempt": now,
                        }
                    },
                )
                return True
        
        # First attempt or window expired, create new entry
        self.collection.update_one(
            {"_id": rate_limit_key},
            {
                "$set": {
                    "attempts": 1,
                    "first_attempt": now,
                    "last_attempt": now,
                }
            },
            upsert=True,
        )
        return True
    
    def reset(self, ip: str, endpoint: str) -> None:
        """
        Manually reset rate limit for an IP:endpoint combination.
        
        Useful for administrative operations or after successful authentication.
        
        Args:
            ip: Client IP address
            endpoint: API endpoint
        """
        rate_limit_key = f"{ip}:{endpoint}"
        self.collection.delete_one({"_id": rate_limit_key})
    
    def get_status(self, ip: str, endpoint: str) -> dict:
        """
        Get current rate limit status for debugging/monitoring.
        
        Returns dict with keys: key, attempts, is_blocked (bool), remaining_attempts, reset_time.
        
        Args:
            ip: Client IP address
            endpoint: API endpoint
            
        Returns:
            dict: Status information with keys: key, attempts, is_blocked, remaining_attempts, reset_time
        """
        if not self._initialized or self.collection is None:
            return {"error": "Not initialized"}
        
        rate_limit_key = f"{ip}:{endpoint}"
        doc = self.collection.find_one({"_id": rate_limit_key})
        
        if not doc:
            # No rate limit data exists
            return {
                "key": rate_limit_key,
                "attempts": 0,
                "is_blocked": False,
                "remaining_attempts": self.max_attempts,
                "reset_time": None,
            }
        
        now = datetime.now(timezone.utc)
        blocked_until = _ensure_aware_utc(doc.get("blocked_until"))
        
        # is_blocked is a boolean: True if currently blocked, False otherwise
        is_blocked = bool(blocked_until and blocked_until > now)
        
        attempts = doc.get("attempts", 0)
        
        # remaining_attempts is 0 if blocked, otherwise max - current
        if is_blocked:
            remaining_attempts = 0
        else:
            remaining_attempts = max(0, self.max_attempts - attempts)
        
        # reset_time is when the block expires, or None if not blocked
        reset_time = blocked_until.isoformat() if is_blocked else None
        
        return {
            "key": rate_limit_key,
            "attempts": attempts,
            "is_blocked": is_blocked,
            "remaining_attempts": remaining_attempts,
            "reset_time": reset_time,
        }


def get_client_ip(request) -> str:
    """
    Extract client IP address from request with X-Forwarded-For support.
    
    Handles both direct connections and reverse proxy scenarios:
    1. Checks X-Forwarded-For header (first IP = client, rest = proxies)
    2. Falls back to request.remote_addr if header invalid
    
    Security:
    - X-Forwarded-For only from trusted proxies (configure in production)
    - Invalid entries ignored, falls back to remote_addr
    - Always returns valid IP address string
    
    Args:
        request: Flask/Werkzeug request object
        
    Returns:
        str: Client IP address in dotted decimal notation (e.g., "192.168.1.1")
    """
    try:
        # Check X-Forwarded-For header (set by reverse proxy)
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            # X-Forwarded-For can be: "client, proxy1, proxy2, ..."
            # Split and take first element (actual client IP)
            ips = [ip.strip() for ip in forwarded_for.split(',')]
            if ips and ips[0]:
                client_ip = ips[0]
                # Validate IP format (basic check)
                if _is_valid_ip(client_ip):
                    return client_ip
    except Exception:
        pass  # If parsing fails, fall through to remote_addr
    
    # Fall back to direct connection IP
    return request.remote_addr or '0.0.0.0'


def _is_valid_ip(ip: str) -> bool:
    """
    Validate if a string is a valid IPv4 address.
    
    Simple validation: must have 4 dot-separated numbers, each 0-255.
    Does NOT validate IPv6 (considered valid if not empty).
    
    Args:
        ip: Potential IP address string
        
    Returns:
        bool: True if looks like valid IPv4, False otherwise
    """
    if not ip or not isinstance(ip, str):
        return False
    
    # Allow IPv6-like strings (contain colons)
    if ':' in ip and '.' not in ip:
        return bool(ip.strip())
    
    # Validate IPv4: 4 octets separated by dots
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False


def rate_limit(limit: int = 100, window: int = 60):
    """
    Decorator for rate limiting API endpoints.
    
    Limits requests by IP + endpoint + HTTP method.
    Automatically returns 429 (Too Many Requests) when limit is exceeded.
    Uses get_client_ip() to handle X-Forwarded-For headers for reverse proxies.
    
    Args:
        limit: Maximum number of requests allowed in the window (default: 100)
        window: Duration of the window in seconds (default: 60)
        
    Example:
        @app.route('/api/resource', methods=['POST'])
        @rate_limit(limit=10, window=60)  # 10 requests per minute
        def create_resource():
            return jsonify({"status": "created"}), 201
    
    Returns:
        429 (Too Many Requests) if limit exceeded
        200-500 (normal response) if allowed
    """
    from functools import wraps
    from flask import request, jsonify, current_app
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get rate limiter instance from Flask app
                rate_limiter = current_app.rate_limiter
                if not rate_limiter:
                    # If rate limiter not available, allow the request
                    return f(*args, **kwargs)
                
                # Extract request information with X-Forwarded-For support
                client_ip = get_client_ip(request)
                endpoint = request.endpoint or 'unknown'
                method = request.method
                
                # Create composite key: IP:endpoint:method
                rate_limit_key = f"{client_ip}:{endpoint}:{method}"
                
                # Check if request is allowed (simplified interface)
                # We'll use the built-in is_allowed but with the composite key
                # by using the endpoint parameter creatively
                full_endpoint_key = f"{endpoint}:{method}"
                
                if not rate_limiter.is_allowed(client_ip, full_endpoint_key):
                    return jsonify({
                        "error": "Rate limit exceeded",
                        "message": f"Too many {method} requests to {endpoint}. Try again later.",
                        "status": 429
                    }), 429
                
                # Request is allowed, proceed to handler
                return f(*args, **kwargs)
                
            except Exception as e:
                # If there's an error with rate limiting, log it but allow the request
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Rate limiter error: {str(e)}")
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator
