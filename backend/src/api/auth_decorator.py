"""
Authentication decorator for role-based access control.
"""
from functools import wraps
from typing import List, Callable, Optional

from flask import request, g, jsonify, current_app
from src.domain.exceptions import NotFoundError


def require_auth(f):
    """
    Decorator to require authentication without role checking.
    
    Extracts JWT token from Authorization header, verifies it.
    Attaches user information to request object for use in route handlers.
    
    Args:
        f: Route function to decorate
        
    Returns:
        Decorated function
        
    Usage:
        @app.route('/api/trips')
        @require_auth
        def get_trips():
            user_id = request.user_id
            return jsonify(trips)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header:
            return jsonify({"error": "Missing authorization header"}), 401
        
        # Check Bearer scheme
        try:
            scheme, token = auth_header.split(" ")
            if scheme.lower() != "bearer":
                return jsonify({"error": "Invalid authorization scheme"}), 401
        except ValueError:
            return jsonify({"error": "Invalid authorization header format"}), 401
        
        # Verify token using auth service
        try:
            auth_service = current_app.auth_service
            payload = auth_service.verify_token(token)
        except Exception as e:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Check if token is blacklisted (logged out)
        try:
            auth_service = current_app.auth_service
            if auth_service.is_token_blacklisted(token, 'access'):
                return jsonify({"error": "Token has been invalidated (user logged out)"}), 401
        except Exception as e:
            current_app.logger.warning(f"Error checking token blacklist: {str(e)}")
            # Fail secure - if we can't check blacklist, deny access
            return jsonify({"error": "Unable to verify token status"}), 401
        
        # Attach user info to request for use in route handler
        request.user_id = payload.get("user_id") or payload.get("sub")
        request.user = payload
        g.user = payload
        g.user_id = payload.get("user_id") or payload.get("sub")
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(roles: List[str]):
    """
    Decorator to enforce role-based access control.
    
    Extracts JWT token from Authorization header, verifies it, and checks user role.
    Attaches user information to flask.g for use in route handlers.
    
    Args:
        roles: List of allowed roles (e.g., ["admin", "operator"])
        
    Returns:
        Decorator function
        
    Usage:
        @app.route('/admin/users')
        @require_role(['admin'])
        def admin_users():
            user = g.user
            return jsonify(user)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header:
                return jsonify({"error": "Missing authorization header"}), 401
            
            # Check Bearer scheme
            try:
                scheme, token = auth_header.split(" ")
                if scheme.lower() != "bearer":
                    return jsonify({"error": "Invalid authorization scheme"}), 401
            except ValueError:
                return jsonify({"error": "Invalid authorization header format"}), 401
            
            # Verify token using auth service
            try:
                auth_service = current_app.auth_service
                payload = auth_service.verify_token(token)
            except Exception as e:
                return jsonify({"error": "Invalid or expired token"}), 401
            
            # Check if token is blacklisted (logged out)
            try:
                auth_service = current_app.auth_service
                if auth_service.is_token_blacklisted(token, 'access'):
                    return jsonify({"error": "Token has been invalidated (user logged out)"}), 401
            except Exception as e:
                current_app.logger.warning(f"Error checking token blacklist: {str(e)}")
                # Fail secure - if we can't check blacklist, deny access
                return jsonify({"error": "Unable to verify token status"}), 401
            
            # Check role
            user_role = payload.get("role")
            if user_role not in roles:
                return jsonify({"error": f"Insufficient permissions. Required roles: {roles}"}), 403
            
            # Attach user to g for use in route handler
            g.user = payload
            g.user_id = payload.get("user_id") or payload.get("sub")
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_ownership(resource_getter: Callable, user_field: str = 'created_by'):
    """
    Decorator to enforce resource ownership verification.
    
    Verifies that the current user owns the resource (has matching user_id in the resource's
    user_field). Admins are always allowed access regardless of ownership.
    
    IMPORTANT: Use this decorator AFTER @require_role to ensure authentication is verified first.
    
    Args:
        resource_getter: Callable that receives resource_id from route kwargs and returns the resource.
                        If resource not found, must return None.
                        Example: lambda trip_id: trip_repo.find_by_id(trip_id)
        user_field: Field name in resource document to check against user_id (default: 'created_by')
                   
    Returns:
        Decorator function
        
    Usage:
        @app.route('/api/trips/<trip_id>')
        @require_role(['operator', 'admin'])
        @require_ownership(lambda trip_id: trip_repository.find_by_id(trip_id))
        def get_trip(trip_id):
            trip = trip_repository.find_by_id(trip_id)
            return jsonify(trip)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get the resource_id from kwargs (first string argument is typically the resource ID)
            resource_id = None
            if 'trip_id' in kwargs:
                resource_id = kwargs['trip_id']
            elif 'driver_id' in kwargs:
                resource_id = kwargs['driver_id']
            elif 'vehicle_id' in kwargs:
                resource_id = kwargs['vehicle_id']
            elif 'client_id' in kwargs:
                resource_id = kwargs['client_id']
            else:
                # Try first positional string argument after decorated_function
                for kwarg_value in kwargs.values():
                    if isinstance(kwarg_value, str):
                        resource_id = kwarg_value
                        break
            
            if not resource_id:
                return jsonify({"error": "Resource ID not found in request"}), 400
            
            # Get current user info from g (set by @require_role/@require_auth)
            user_id = g.get('user_id')
            user = g.get('user', {})
            user_role = user.get('role')
            
            if not user_id:
                return jsonify({"error": "User not authenticated"}), 401
            
            # Admins have unrestricted access
            if user_role == 'admin':
                return f(*args, **kwargs)
            
            # Try to fetch the resource
            try:
                resource = resource_getter(resource_id)
            except NotFoundError:
                # Re-raise NotFoundError so it's caught by error handler
                raise
            except Exception as e:
                return jsonify({"error": f"Error accessing resource: {str(e)}"}), 500
            
            # Check if resource exists (404 before ownership check)
            if not resource:
                raise NotFoundError(f"Resource {resource_id} not found")
            
            # Check ownership by comparing user_id with resource's user_field
            resource_user_id = resource.get(user_field)
            
            if resource_user_id != user_id:
                return jsonify({"error": "Access denied to this resource"}), 403
            
            # All checks passed
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
