"""
Clients API endpoints - REST interface for client operations.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
from typing import Tuple

from src.services.client_service import (
    ClientService,
    ClientError,
    ClientValidationError,
    ClientNotFoundError,
    ClientAlreadyExistsError,
)
from src.schemas.client import ClientCreate, ClientUpdate
from src.api.auth_decorator import require_auth, require_role, require_ownership
from src.infrastructure.rate_limiter import rate_limit


def create_clients_blueprint(client_service: ClientService) -> Blueprint:
    """
    Create clients blueprint with all endpoints.
    
    Args:
        client_service: ClientService instance for business logic
        
    Returns:
        Flask Blueprint with clients endpoints
    """
    bp = Blueprint("clients", __name__, url_prefix="/api/clients")
    
    # Helper function for ownership verification
    def _get_client_for_ownership(client_id: str):
        """Helper to fetch client for ownership check."""
        try:
            return client_service.get_client(client_id)
        except Exception:
            return None
    
    @bp.route("/", methods=["POST"])
    @rate_limit(limit=30, window=60)
    @require_role(["admin", "operator"])
    def create_client() -> Tuple[dict, int]:
        """
        Create a new client with Pydantic validation.
        
        Request body:
        {
            "name": "Client Name",
            "phone": "+57...",
            "email": "contact@example.com",
            "address": "Street Address",
            "city": "City Name",
            "contact_person": "Contact Name (optional)"
        }
        
        Returns:
            201 Created with client data
            400 Bad Request if validation fails
            409 Conflict if client already exists
            422 Unprocessable Entity if invalid data
        """
        try:
            data = request.get_json() or {}
            user_id = g.get('user_id')
            
            # Validate using Pydantic
            validated_client = ClientCreate(**data)
            client_dict = validated_client.model_dump()
            
            client = client_service.create_client(client_dict, user_id=user_id)
            return jsonify(client), 201
            
        except ValidationError as e:
            # Pydantic validation error
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
        except ClientValidationError as e:
            return jsonify({"error": str(e)}), 400
        except ClientAlreadyExistsError as e:
            return jsonify({"error": str(e)}), 409
        except ClientError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    @bp.route("/", methods=["GET"])
    @require_role(["admin", "operator"])
    def list_clients() -> Tuple[dict, int]:
        """
        List clients.
        
        Query parameters:
        - active_only: boolean (default: true)
        - limit: integer (default: 100, max: 500)
        - skip: integer (default: 0)
        - all: for admins, show all clients (default: false)
        
        Returns:
            200 OK with list of clients
        """
        try:
            user_id = g.get('user_id')
            user_role = g.get('user', {}).get('role', 'operator')
            
            limit = request.args.get("limit", 100, type=int)
            skip = request.args.get("skip", 0, type=int)
            active_only = request.args.get("active_only", True, type=lambda x: x.lower() == "true")
            show_all = request.args.get("all", "false").lower() == "true"
            
            # Validate pagination
            limit = min(limit, 500)
            limit = max(limit, 1)
            skip = max(skip, 0)
            
            # For operators, filter by user (unless admin with ?all=true)
            clients = client_service.list_clients(
                active_only=active_only,
                limit=limit,
                skip=skip,
                user_id=user_id if (user_role != 'admin' or not show_all) else None
            )
            
            return jsonify({
                "clients": clients,
                "count": len(clients),
                "limit": limit,
                "skip": skip,
            }), 200
        except ClientError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    @bp.route("/<client_id>", methods=["GET"])
    @require_auth
    @require_role(["admin", "operator"])
    @require_ownership(lambda client_id: _get_client_for_ownership(client_id))
    def get_client(client_id: str) -> Tuple[dict, int]:
        """
        Get a client by ID.
        
        Required role: admin, operator
        Ownership: Must own the client or be admin
        
        Returns:
            200 OK with client data
            401 Unauthorized
            403 Forbidden (not the owner)
            404 Not Found if client doesn't exist
        """
        try:
            client = client_service.get_client(client_id)
            
            if not client:
                return jsonify({"error": f"Client {client_id} not found"}), 404
            
            return jsonify(client), 200
        except ClientError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    @bp.route("/by-nit/<nit>", methods=["GET"])
    @require_role(["admin", "operator"])
    def get_client_by_nit(nit: str) -> Tuple[dict, int]:
        """
        Get a client by NIT.
        
        Returns:
            200 OK with client data
            404 Not Found if client doesn't exist
        """
        try:
            client = client_service.get_client_by_nit(nit)
            
            if not client:
                return jsonify({"error": f"Client with NIT {nit} not found"}), 404
            
            return jsonify(client), 200
        except ClientError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    @bp.route("/<client_id>", methods=["PUT"])
    @rate_limit(limit=50, window=60)
    @require_role(["admin", "operator"])
    @require_ownership(lambda client_id: _get_client_for_ownership(client_id))
    def update_client(client_id: str) -> Tuple[dict, int]:
        """
        Update a client with Pydantic validation.
        
        Required role: admin, operator
        Ownership: Must own the client or be admin
        
        Request body:
        {
            "name": "New Name",
            "email": "new@example.com",
            ...
        }
        
        Returns:
            200 OK with updated client data
            400 Bad Request if validation fails
            404 Not Found if client doesn't exist
            409 Conflict if duplicate NIT/email
            422 Unprocessable Entity if invalid data
        """
        try:
            data = request.get_json() or {}
            
            # Validate using Pydantic
            validated_update = ClientUpdate(**data)
            update_dict = validated_update.model_dump(exclude_unset=True)
            
            client = client_service.update_client(client_id, update_dict)
            return jsonify(client), 200
            
        except ValidationError as e:
            # Pydantic validation error
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
        except ClientValidationError as e:
            return jsonify({"error": str(e)}), 400
        except ClientNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except ClientAlreadyExistsError as e:
            return jsonify({"error": str(e)}), 409
        except ClientError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    @bp.route("/<client_id>", methods=["DELETE"])
    @rate_limit(limit=20, window=60)
    @require_role(["admin", "operator"])
    @require_ownership(lambda client_id: _get_client_for_ownership(client_id))
    def delete_client(client_id: str) -> Tuple[None, int]:
        """
        Delete a client (soft delete).
        
        Required role: admin, operator
        Ownership: Must own the client or be admin
        
        Returns:
            204 No Content if successful
            404 Not Found if client doesn't exist
        """
        try:
            success = client_service.delete_client(client_id)
            
            if not success:
                return jsonify({"error": f"Client {client_id} not found"}), 404
            
            return "", 204
        except ClientError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    return bp
