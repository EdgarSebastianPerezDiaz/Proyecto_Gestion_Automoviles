"""
Final Recipients API blueprint - REST endpoints for final recipient operations.
"""
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from src.services.final_recipient_service import (
    FinalRecipientService,
    FinalRecipientError,
    FinalRecipientValidationError,
    FinalRecipientNotFoundError,
    FinalRecipientAlreadyExistsError,
)
from src.schemas.final_recipient import FinalRecipientCreate, FinalRecipientUpdate
from src.api.auth_decorator import require_role
from src.infrastructure.rate_limiter import rate_limit

# Create blueprint instance directly (no factory function)
final_recipients_bp = Blueprint("final_recipients", __name__, url_prefix="/api/final-recipients")

# Store service reference that will be set during app initialization
_service: FinalRecipientService = None


def set_service(service: FinalRecipientService):
    """Set FinalRecipientService instance for this blueprint."""
    global _service
    _service = service


def get_service() -> FinalRecipientService:
    """Get the FinalRecipientService instance."""
    if _service is None:
        raise RuntimeError("FinalRecipientService not initialized")
    return _service


@final_recipients_bp.route("/", methods=["POST"])
@rate_limit(limit=30, window=60)
@require_role(["admin"])
def create_recipient():
    """
    Create a new final recipient.
    
    Required role: admin
    
    Body:
        - name (str, required): Recipient name
        - address (str, required): Recipient address
        - city (str, required): City
        - contact_name (str, optional): Contact person name
        - phone (str, required): Contact phone
        - email (str, required): Recipient email
    
    Returns:
        201: Created recipient with _id
        422: Validation error
        409: Recipient already exists (same email)
        401: Unauthorized
        403: Forbidden
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate using Pydantic
        validated_data = FinalRecipientCreate(**data)
        recipient_dict = validated_data.model_dump()
        
        service = get_service()
        recipient = service.create_recipient(recipient_dict)
        return jsonify(recipient), 201
        
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
    except FinalRecipientAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except FinalRecipientError as e:
        return jsonify({"error": str(e)}), 500


@final_recipients_bp.route("/<recipient_id>", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def get_recipient(recipient_id: str):
    """
    Get a specific recipient by ID.
    
    Required role: admin, dispatcher, warehouse_manager
    
    Args:
        recipient_id: Recipient ID (ObjectId as string)
    
    Returns:
        200: Recipient object
        404: Recipient not found
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        recipient = service.get_recipient(recipient_id)
        return jsonify(recipient), 200
    except FinalRecipientNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except FinalRecipientError as e:
        return jsonify({"error": str(e)}), 500


@final_recipients_bp.route("/", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def list_recipients():
    """
    List all final recipients with pagination.
    
    Required role: admin, dispatcher, warehouse_manager
    
    Query parameters:
        - page (int, optional): Page number for pagination (default: 1)
        - per_page (int, optional): Items per page (default: 10, max: 100)
    
    Returns:
        200: List of recipients with pagination info
            {
                "items": [{recipient_object}],
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
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        
        if page < 1:
            return jsonify({"error": "Page must be greater than 0"}), 400
        if per_page < 1 or per_page > 100:
            return jsonify({"error": "Per page must be between 1 and 100"}), 400
        
        service = get_service()
        
        # Get paginated items
        skip = (page - 1) * per_page
        recipients = service.list_recipients(skip=skip, limit=per_page)
        
        # Get total count
        total = service.count_active()
        
        # Calculate total pages
        total_pages = (total + per_page - 1) // per_page
        
        return jsonify({
            "items": recipients,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }), 200
    except FinalRecipientError as e:
        return jsonify({"error": str(e)}), 500


@final_recipients_bp.route("/search", methods=["GET"])
@require_role(["admin", "dispatcher", "warehouse_manager"])
def search_recipients():
    """
    Search recipients by name or email (case-insensitive, partial match).
    
    Required role: admin, dispatcher, warehouse_manager
    
    Query parameters:
        - q (str, required): Search query (min 2 chars)
        - limit (int, optional): Max results (default: 10, max: 100)
    
    Returns:
        200: List of matching recipients
            {"items": [{recipient_object}]}
        400: Invalid search query
        401: Unauthorized
        403: Forbidden
    """
    try:
        query = request.args.get("q", "").strip()
        if not query or len(query) < 2:
            return jsonify({
                "error": "Search query must be at least 2 characters"
            }), 400
        
        limit = int(request.args.get("limit", 10))
        if limit < 1 or limit > 100:
            return jsonify({"error": "Limit must be between 1 and 100"}), 400
        
        service = get_service()
        recipients = service.search_recipients_by_name(query, limit)
        return jsonify({"items": recipients}), 200
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
    except FinalRecipientError as e:
        return jsonify({"error": str(e)}), 500


@final_recipients_bp.route("/<recipient_id>", methods=["PUT"])
@rate_limit(limit=50, window=60)
@require_role(["admin"])
def update_recipient(recipient_id: str):
    """
    Update an existing recipient.
    
    Required role: admin
    
    Args:
        recipient_id: Recipient ID (ObjectId as string)
        
    Body (all optional):
        - name (str): Recipient name
        - address (str): Recipient address
        - city (str): City
        - contact_name (str): Contact person name
        - phone (str): Contact phone
        - email (str): Recipient email
    
    Returns:
        200: Updated recipient object
        422: Validation error
        404: Recipient not found
        409: Email already exists for another recipient
        401: Unauthorized
        403: Forbidden
    """
    try:
        data = request.get_json() or {}
        
        # Validate using Pydantic
        validated_update = FinalRecipientUpdate(**data)
        update_dict = validated_update.model_dump(exclude_unset=True)
        
        service = get_service()
        recipient = service.update_recipient(recipient_id, update_dict)
        return jsonify(recipient), 200
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
    except FinalRecipientNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except FinalRecipientAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except FinalRecipientError as e:
        return jsonify({"error": str(e)}), 500


@final_recipients_bp.route("/<recipient_id>", methods=["DELETE"])
@rate_limit(limit=20, window=60)
@require_role(["admin"])
def delete_recipient(recipient_id: str):
    """
    Delete (soft delete) a final recipient.
    
    Required role: admin
    
    Args:
        recipient_id: Recipient ID (ObjectId as string)
    
    Returns:
        204: No content (successfully deleted)
        404: Recipient not found
        401: Unauthorized
        403: Forbidden
    """
    try:
        service = get_service()
        service.delete_recipient(recipient_id)
        return jsonify({}), 204
    except FinalRecipientNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except FinalRecipientError as e:
        return jsonify({"error": str(e)}), 500
