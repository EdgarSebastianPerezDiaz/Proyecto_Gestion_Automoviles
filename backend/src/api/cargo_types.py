"""
Cargo Types API blueprint - REST endpoints for cargo types.
"""
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from src.services.cargo_type_service import (
    CargoTypeService,
    CargoTypeError,
    CargoTypeValidationError,
    CargoTypeNotFoundError,
    CargoTypeAlreadyExistsError,
)
from src.schemas.cargo_type import CargoTypeCreate, CargoTypeUpdate
from src.api.auth_decorator import require_role
from src.infrastructure.rate_limiter import rate_limit

# Create blueprint instance directly (no factory function)
cargo_types_bp = Blueprint("cargo_types", __name__, url_prefix="/api/cargo-types")

# Store service reference that will be set during app initialization
_service: CargoTypeService = None


def set_service(service: CargoTypeService):
    """Set CargoTypeService instance for this blueprint."""
    global _service
    _service = service


def get_service() -> CargoTypeService:
    """Get the CargoTypeService instance."""
    if _service is None:
        raise RuntimeError("CargoTypeService not initialized")
    return _service


@cargo_types_bp.route("/", methods=["POST"])
@rate_limit(limit=30, window=60)
@require_role(["admin"])
def create_cargo_type():
    """
    Create a new cargo type.
    
    Required role: admin
    
    Body:
        - name (str, required): Cargo type name
        - description (str, optional): Cargo type description
        - price_per_ton (float, required): Price per ton (> 0)
        - requires_special_permit (bool, optional): Requires special permit
    
    Returns:
        201: Created cargo type with _id
        422: Validation error
        409: Cargo type already exists (same name)
        401: Unauthorized
        403: Forbidden
    """
    try:
        data = request.get_json() or {}
        
        # Validate using Pydantic
        validated_data = CargoTypeCreate(**data)
        cargo_dict = validated_data.model_dump()
        
        service = get_service()
        cargo_type = service.create_cargo_type(cargo_dict)
        return jsonify(cargo_type), 201
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
    except CargoTypeAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except CargoTypeError as e:
        return jsonify({"error": str(e)}), 500


@cargo_types_bp.route("/<cargo_id>", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def get_cargo_type(cargo_id: str):
    """
    Get a specific cargo type by ID.
    
    Required role: admin, dispatcher, warehouse_manager
    
    Args:
        cargo_id: Cargo type ID (ObjectId as string)
    
    Returns:
        200: Cargo type object
        404: Cargo type not found
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        cargo_type = service.get_cargo_type(cargo_id)
        return jsonify(cargo_type), 200
    except CargoTypeNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except CargoTypeError as e:
        return jsonify({"error": str(e)}), 500


@cargo_types_bp.route("/", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def list_cargo_types():
    """
    List all active cargo types with pagination.
    
    Required role: admin, dispatcher, warehouse_manager
    
    Query parameters:
        - page (int, optional): Page number for pagination (default: 1)
        - per_page (int, optional): Items per page (default: 10, max: 100)
    
    Returns:
        200: List of cargo types with pagination info
            {
                "items": [{cargo_type_object}],
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
        cargo_types = service.list_active_cargo_types(skip=(page - 1) * per_page, limit=per_page)
        total = service.count_active()
        
        return jsonify({
            "items": cargo_types,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }), 200
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400
    except CargoTypeError as e:
        return jsonify({"error": str(e)}), 500


@cargo_types_bp.route("/search", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def search_cargo_type():
    """
    Search for cargo type by name (case-insensitive, exact match).
    
    Required role: admin, dispatcher, warehouse_manager
    
    Query parameters:
        - q (str, required): Search query (min 2 chars)
    
    Returns:
        200: Cargo type object
        400: Invalid search query
        404: Cargo type not found
        401: Unauthorized
        403: Forbidden
    """
    try:
        query = request.args.get("q", "").strip()
        if not query or len(query) < 2:
            return jsonify({
                "error": "Search query must be at least 2 characters"
            }), 400
        
        service = get_service()
        cargo_type = service.search_cargo_type_by_name(query)
        
        return jsonify(cargo_type), 200
    except CargoTypeNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except CargoTypeValidationError as e:
        return jsonify({"error": str(e)}), 400
    except CargoTypeError as e:
        return jsonify({"error": str(e)}), 500


@cargo_types_bp.route("/<cargo_id>", methods=["PUT"])
@rate_limit(limit=50, window=60)
@require_role(["admin"])
def update_cargo_type(cargo_id: str):
    """
    Update an existing cargo type.
    
    Required role: admin
    
    Args:
        cargo_id: Cargo type ID (ObjectId as string)
        
    Body (all optional):
        - name (str): Cargo type name
        - description (str): Cargo type description
        - price_per_ton (float): Price per ton (> 0)
        - requires_special_permit (bool): Requires special permit
    
    Returns:
        200: Updated cargo type object
        422: Validation error
        404: Cargo type not found
        409: Cargo type name already exists for another cargo
        401: Unauthorized
        403: Forbidden
    """
    try:
        data = request.get_json() or {}
        
        # Validate using Pydantic
        validated_update = CargoTypeUpdate(**data)
        update_dict = validated_update.model_dump(exclude_unset=True)
        
        service = get_service()
        cargo_type = service.update_cargo_type(cargo_id, update_dict)
        return jsonify(cargo_type), 200
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
    except CargoTypeNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except CargoTypeAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except CargoTypeError as e:
        return jsonify({"error": str(e)}), 500


@cargo_types_bp.route("/<cargo_id>", methods=["DELETE"])
@rate_limit(limit=20, window=60)
@require_role(["admin"])
def delete_cargo_type(cargo_id: str):
    """
    Delete (soft delete) a cargo type.
    
    Required role: admin
    
    Args:
        cargo_id: Cargo type ID (ObjectId as string)
    
    Returns:
        204: No content (successfully deleted)
        404: Cargo type not found
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        service.delete_cargo_type(cargo_id)
        return jsonify({}), 204
    except CargoTypeNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except CargoTypeError as e:
        return jsonify({"error": str(e)}), 500
