"""
Trip Statuses API blueprint - REST endpoints for trip statuses.
"""
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from src.services.trip_status_service import (
    TripStatusService,
    TripStatusError,
    TripStatusValidationError,
    TripStatusNotFoundError,
    TripStatusInUseError,
    TripStatusAlreadyExistsError,
)
from src.schemas.trip_status import TripStatusCreate, TripStatusUpdate
from src.api.auth_decorator import require_role
from src.infrastructure.rate_limiter import rate_limit

# Create blueprint instance directly (no factory function)
trip_statuses_bp = Blueprint("trip_statuses", __name__, url_prefix="/api/trip-statuses")

# Store service reference that will be set during app initialization
_service: TripStatusService = None


def set_service(service: TripStatusService):
    """Set TripStatusService instance for this blueprint."""
    global _service
    _service = service


def get_service() -> TripStatusService:
    """Get the TripStatusService instance."""
    if _service is None:
        raise RuntimeError("TripStatusService not initialized")
    return _service


@trip_statuses_bp.route("/", methods=["POST"])
@rate_limit(limit=30, window=60)
@require_role(["admin"])
def create_trip_status():
    """
    Create a new trip status.
    
    Required role: admin
    
    Body:
        - code (str, required): Status code (lowercase alphanumeric + underscore, unique)
        - label (str, required): Status label
        - order (int, optional): Sort order (auto-assigned if not provided)
        - is_terminal (bool, optional): Is terminal status (default: false)
    
    Returns:
        201: Created trip status with _id
        422: Validation error
        409: Status code already exists
        401: Unauthorized
        403: Forbidden
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate using Pydantic
        validated_data = TripStatusCreate(**data)
        status_dict = validated_data.model_dump()
        
        service = get_service()
        trip_status = service.create_trip_status(status_dict)
        return jsonify(trip_status), 201
    except ValidationError as e:
        error_details = []
        for error in e.errors():
            error_details.append({
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "Validation error"),
                "type": error.get("type", "value_error")
            })
        return jsonify({
            "error": "validation_error",
            "details": error_details
        }), 422
    except TripStatusAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except TripStatusError as e:
        return jsonify({"error": str(e)}), 500


@trip_statuses_bp.route("/<status_id>", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def get_trip_status(status_id: str):
    """
    Get a specific trip status by ID.
    
    Required role: admin, dispatcher, warehouse_manager
    
    Args:
        status_id: Trip status ID (ObjectId as string)
    
    Returns:
        200: Trip status object
        404: Trip status not found
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        trip_status = service.get_trip_status(status_id)
        return jsonify(trip_status), 200
    except TripStatusNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except TripStatusError as e:
        return jsonify({"error": str(e)}), 500


@trip_statuses_bp.route("/", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def list_trip_statuses():
    """
    List all trip statuses with pagination.
    
    Required role: admin, dispatcher, warehouse_manager
    
    Query parameters:
        - page (int, optional): Page number for pagination (default: 1)
        - per_page (int, optional): Items per page (default: 10, max: 100)
    
    Returns:
        200: List of trip statuses with pagination info
            {
                "items": [{trip_status_object}],
                "total": int,
                "page": int,
                "per_page": int,
                "total_pages": int
            }
        400: Invalid pagination parameters
        401: Unauthorized
        403: Forbidden
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        
        if page < 1:
            return jsonify({"error": "Page must be greater than 0"}), 400
        if per_page < 1 or per_page > 100:
            return jsonify({"error": "Per page must be between 1 and 100"}), 400
        
        service = get_service()
        trip_statuses = service.list_all_statuses(skip=(page - 1) * per_page, limit=per_page)
        total = service.count_all()
        
        return jsonify({
            "items": trip_statuses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }), 200
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400
    except TripStatusError as e:
        return jsonify({"error": str(e)}), 500


@trip_statuses_bp.route("/code/<code>", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def get_trip_status_by_code(code: str):
    """
    Get trip status by code.
    
    Required role: admin, dispatcher, warehouse_manager
    
    Args:
        code: Status code (e.g., 'scheduled', 'in_transit')
    
    Returns:
        200: Trip status object
        400: Invalid code
        404: Trip status not found
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        trip_status = service.get_trip_status_by_code(code)
        return jsonify(trip_status), 200
    except TripStatusNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except TripStatusValidationError as e:
        return jsonify({"error": str(e)}), 400
    except TripStatusError as e:
        return jsonify({"error": str(e)}), 500


@trip_statuses_bp.route("/non-terminal", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def list_non_terminal_statuses():
    """
    Get all non-terminal trip statuses (trip can continue).
    
    Required role: admin, dispatcher, warehouse_manager
    
    Returns:
        200: List of non-terminal trip statuses
            {"items": [{trip_status_object}]}
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        statuses = service.list_non_terminal_statuses()
        return jsonify({"items": statuses}), 200
    except TripStatusError as e:
        return jsonify({"error": str(e)}), 500


@trip_statuses_bp.route("/<status_id>", methods=["PUT"])
@rate_limit(limit=50, window=60)
@require_role(["admin"])
def update_trip_status(status_id: str):
    """
    Update an existing trip status.
    
    Required role: admin
    
    Args:
        status_id: Trip status ID (ObjectId as string)
        
    Body (all optional):
        - label (str): Status label
        - order (int): Sort order
        - is_terminal (bool): Is terminal status
    
    Returns:
        200: Updated trip status object
        422: Validation error
        404: Trip status not found
        409: Status code already exists for another status
        401: Unauthorized
        403: Forbidden
    """
    try:
        data = request.get_json() or {}
        
        # Validate using Pydantic
        validated_update = TripStatusUpdate(**data)
        update_dict = validated_update.model_dump(exclude_unset=True)
        
        service = get_service()
        trip_status = service.update_trip_status(status_id, update_dict)
        return jsonify(trip_status), 200
    except ValidationError as e:
        error_details = []
        for error in e.errors():
            error_details.append({
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "Validation error"),
                "type": error.get("type", "value_error")
            })
        return jsonify({
            "error": "validation_error",
            "details": error_details
        }), 422
    except TripStatusNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except TripStatusAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except TripStatusError as e:
        return jsonify({"error": str(e)}), 500


@trip_statuses_bp.route("/<status_id>", methods=["DELETE"])
@rate_limit(limit=20, window=60)
@require_role(["admin"])
def delete_trip_status(status_id: str):
    """
    Delete a trip status.
    
    Required role: admin
    
    Args:
        status_id: Trip status ID (ObjectId as string)
    
    Returns:
        204: No content (successfully deleted)
        404: Trip status not found
        409: Trip status is currently in use
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        service.delete_trip_status(status_id)
        return jsonify({}), 204
    except TripStatusNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except TripStatusInUseError as e:
        return jsonify({"error": str(e)}), 409
    except TripStatusError as e:
        return jsonify({"error": str(e)}), 500
