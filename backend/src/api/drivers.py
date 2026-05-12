"""
Drivers API Blueprint

REST API endpoints for driver management.
Includes CRUD operations, license status checks, and role-based access control.
"""

from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
from src.services.driver_service import (
    DriverService,
    DriverValidationError,
    DriverNotFoundError,
    DriverAlreadyExistsError,
)
from src.schemas.driver import DriverCreate, DriverUpdate
from src.infrastructure.rate_limiter import rate_limit
from src.api.auth_decorator import require_role, require_ownership


def create_drivers_blueprint(driver_service: DriverService) -> Blueprint:
    """
    Create drivers API blueprint.
    
    Args:
        driver_service: DriverService instance for business logic
        
    Returns:
        Configured Flask Blueprint
    """
    bp = Blueprint('drivers', __name__, url_prefix='/api/drivers')
    
    # Helper function for ownership verification
    def _get_driver_for_ownership(driver_id: str):
        """Helper to fetch driver for ownership check."""
        try:
            return driver_service.get_driver(driver_id)
        except Exception:
            return None
    
    @bp.route('/', methods=['POST'])
    @rate_limit(limit=30, window=60)
    @require_role(['admin', 'operator'])
    def create_driver():
        """
        Create a new driver with Pydantic validation.
        
        Required role: admin, operator
        
        Returns:
            201: Created driver document
            400: Validation error
            401: Unauthorized
            403: Forbidden
            409: Driver already exists
            422: Invalid request data
        """
        data = request.get_json()
        user_id = g.get('user_id')
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        try:
            # Validate using Pydantic
            validated_driver = DriverCreate(**data)
            driver_dict = validated_driver.model_dump()
            
            driver = driver_service.create_driver(driver_dict, user_id=user_id)
            return jsonify(driver), 201
            
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                error_details.append({
                    'loc': list(error.get('loc', [])),
                    'msg': error.get('msg', 'Validation error'),
                    'type': error.get('type', 'value_error')
                })
            return jsonify({
                'error': 'validation_error',
                'details': error_details
            }), 422
        except DriverValidationError as e:
            return jsonify({'error': str(e)}), 400
        except DriverAlreadyExistsError as e:
            return jsonify({'error': str(e)}), 409
    
    @bp.route('/', methods=['GET'])
    @require_role(['admin', 'operator'])
    def list_drivers():
        """
        List drivers with pagination and filtering.
        
        Query parameters:
            - active_only (bool): Only active drivers (default: true)
            - include_expired (bool): Include expired licenses (default: false)
            - limit (int): Results per page (default: 100, max: 1000)
            - skip (int): Results to skip (default: 0)
        
        Required role: admin, operator
        
        Returns:
            200: List of drivers
            400: Invalid parameters
            401: Unauthorized
            403: Forbidden
        """
        try:
            active_only = request.args.get('active_only', 'true').lower() == 'true'
            include_expired = request.args.get('include_expired', 'false').lower() == 'true'
            limit = int(request.args.get('limit', 100))
            skip = int(request.args.get('skip', 0))
            
            # Validate parameters
            if limit < 1 or limit > 1000:
                return jsonify({'error': 'limit must be between 1 and 1000'}), 400
            if skip < 0:
                return jsonify({'error': 'skip must be >= 0'}), 400
            
            drivers = driver_service.list_drivers(
                active_only=active_only,
                include_expired=include_expired,
                limit=limit,
                skip=skip
            )
            
            return jsonify({'drivers': drivers, 'count': len(drivers)}), 200
        except ValueError as e:
            return jsonify({'error': 'Invalid parameters'}), 400
    
    @bp.route('/<driver_id>', methods=['GET'])
    @require_role(['admin', 'operator'])
    @require_ownership(lambda driver_id: _get_driver_for_ownership(driver_id))
    def get_driver(driver_id):
        """
        Get driver by ID.
        
        Required role: admin, operator
        Ownership: Must own the driver or be admin
        
        Returns:
            200: Driver document
            401: Unauthorized
            403: Forbidden (not the owner)
            404: Driver not found
        """
        driver = driver_service.get_driver(driver_id)
        
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        return jsonify(driver), 200
    
    @bp.route('/by-id-number/<id_number>', methods=['GET'])
    @require_role(['admin', 'operator'])
    def get_driver_by_id_number(id_number):
        """
        Get driver by cédula (ID number).
        
        Convenience endpoint for lookups.
        
        Required role: admin, operator
        
        Returns:
            200: Driver document
            401: Unauthorized
            403: Forbidden
            404: Driver not found
        """
        driver = driver_service.get_driver_by_id_number(id_number)
        
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        return jsonify(driver), 200
    
    @bp.route('/expiring-soon', methods=['GET'])
    @require_role(['admin', 'operator'])
    def get_expiring_soon():
        """
        Get drivers with licenses expiring within 30 days.
        
        Query parameters:
            - days (int): Threshold in days (default: 30)
        
        Required role: admin, operator
        
        Returns:
            200: List of drivers with expiring licenses
            401: Unauthorized
            403: Forbidden
        """
        try:
            days = int(request.args.get('days', 30))
            drivers = driver_service.get_expiring_soon(days_threshold=days)
            return jsonify({'drivers': drivers, 'count': len(drivers)}), 200
        except ValueError:
            return jsonify({'error': 'Invalid days parameter'}), 400
    
    @bp.route('/<driver_id>', methods=['PUT'])
    @rate_limit(limit=50, window=60)
    @require_role(['admin', 'operator'])
    @require_ownership(lambda driver_id: _get_driver_for_ownership(driver_id))
    def update_driver(driver_id):
        """
        Update driver information with Pydantic validation.
        
        Required role: admin, operator
        Ownership: Must own the driver or be admin
        
        Returns:
            200: Updated driver document
            400: Validation error
            401: Unauthorized
            403: Forbidden (not the owner)
            404: Driver not found
            409: ID number conflict
            422: Invalid request data
        """
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        try:
            # Validate using Pydantic
            validated_update = DriverUpdate(**data)
            update_dict = validated_update.model_dump(exclude_unset=True)
            
            driver = driver_service.update_driver(driver_id, update_dict)
            return jsonify(driver), 200
            
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                error_details.append({
                    'loc': list(error.get('loc', [])),
                    'msg': error.get('msg', 'Validation error'),
                    'type': error.get('type', 'value_error')
                })
            return jsonify({
                'error': 'validation_error',
                'details': error_details
            }), 422
        except DriverNotFoundError as e:
            return jsonify({'error': str(e)}), 404
        except DriverValidationError as e:
            return jsonify({'error': str(e)}), 400
        except DriverAlreadyExistsError as e:
            return jsonify({'error': str(e)}), 409
    
    @bp.route('/<driver_id>', methods=['DELETE'])
    @rate_limit(limit=20, window=60)
    @require_role(['admin', 'operator'])
    @require_ownership(lambda driver_id: _get_driver_for_ownership(driver_id))
    def delete_driver(driver_id):
        """
        Delete driver (soft delete - sets is_active=False).
        
        Required role: admin, operator
        Ownership: Must own the driver or be admin
        
        Returns:
            204: Deleted successfully
            401: Unauthorized
            403: Forbidden (not the owner)
            404: Driver not found
        """
        try:
            driver_service.delete_driver(driver_id)
            return '', 204
        except DriverNotFoundError as e:
            return jsonify({'error': str(e)}), 404
    
    @bp.route('/<driver_id>/renew-license', methods=['PATCH'])
    @rate_limit(limit=50, window=60)
    @require_role(['admin'])
    def renew_license(driver_id):
        """
        Renew driver license by updating expiry date.
        
        Expected JSON body:
            {
                "license_expiry": "2027-04-03T00:00:00"
            }
        
        Required role: admin
        
        Returns:
            200: Updated driver document
            400: Validation error
            401: Unauthorized
            403: Forbidden
            404: Driver not found
        """
        data = request.get_json()
        
        if not data or 'license_expiry' not in data:
            return jsonify({'error': 'license_expiry is required'}), 400
        
        try:
            driver = driver_service.update_driver(
                driver_id,
                {'license_expiry': data['license_expiry']}
            )
            return jsonify(driver), 200
        except DriverNotFoundError as e:
            return jsonify({'error': str(e)}), 404
        except DriverValidationError as e:
            return jsonify({'error': str(e)}), 400
    
    return bp
