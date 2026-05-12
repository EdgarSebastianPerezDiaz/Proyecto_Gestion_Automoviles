"""
Vehicles API blueprint - REST endpoints for vehicle operations.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
from src.services.vehicle_service import (
    VehicleService,
    VehicleError,
    VehicleValidationError,
    VehicleNotFoundError,
    VehicleAlreadyExistsError,
)
from src.schemas.vehicle import VehicleCreate, VehicleUpdate
from src.api.auth_decorator import require_role, require_ownership
from src.infrastructure.rate_limiter import rate_limit


def create_vehicles_blueprint(vehicle_service: VehicleService) -> Blueprint:
    """
    Create vehicles blueprint with all endpoints.
    
    Args:
        vehicle_service: VehicleService instance for business logic
        
    Returns:
        Flask Blueprint with vehicle endpoints
    """
    bp = Blueprint("vehicles", __name__, url_prefix="/api/vehicles")
    
    # Helper function for ownership verification
    def _get_vehicle_for_ownership(vehicle_id: str):
        """Helper to fetch vehicle for ownership check."""
        try:
            return vehicle_service.get_vehicle(vehicle_id)
        except Exception:
            return None
    
    @bp.route("/", methods=["POST"])
    @rate_limit(limit=30, window=60)
    @require_role(["admin", "operator"])
    def create_vehicle():
        """
        Create a new vehicle with Pydantic validation.
        
        Required role: admin
        
        Body:
            - plate (str, required): Vehicle plate (uppercase alphanumeric)
            - vehicle_type (str, required): Type (truck, trailer, van, platform, tanker, refrigerated)
            - brand (str, required): Vehicle manufacturer
            - model_year (int, required): Year of manufacture
            - capacity_tons (float, required): Cargo capacity in metric tons
            - volume_m3 (float, optional): Cargo volume in cubic meters
            - company_id (str, required): Company owning the vehicle
            - soat_expiry (datetime, optional): SOAT Insurance expiry date
            - tech_review_expiry (datetime, optional): Technical review expiry date
        
        Returns:
            201: Created vehicle with _id, created_at, updated_at
            400: Validation error
            409: Vehicle already exists (same plate)
            401: Unauthorized (missing/invalid token)
            403: Forbidden (insufficient permissions)
            422: Invalid request data
        """
        try:
            user_id = g.get('user_id')
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            
            # Validate using Pydantic
            validated_vehicle = VehicleCreate(**data)
            vehicle_dict = validated_vehicle.model_dump()
            
            vehicle = vehicle_service.create_vehicle(vehicle_dict, user_id=user_id)
            return jsonify(vehicle), 201
            
        except ValidationError as e:
            # Pydantic validation error
            return jsonify({
                "error": "validation_error",
                "details": e.errors()
            }), 422
        except VehicleValidationError as e:
            return jsonify({"error": str(e)}), 400
        except VehicleAlreadyExistsError as e:
            return jsonify({"error": str(e)}), 409
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/", methods=["GET"])
    @require_role(["admin", "operator"])
    def list_vehicles():
        """
        List vehicles with optional filtering.
        
        Required role: admin, operator
        
        Query parameters:
            - active_only (bool, default true): Return only active vehicles
            - status (str, optional): Filter by status (available, in_trip, inactive)
            - limit (int, default 100, max 1000): Maximum results
            - skip (int, default 0): Pagination offset
            - all (bool, optional): For admins, show all vehicles (default: false)
        
        Returns:
            200: List of vehicles
            400: Invalid query parameters
            401: Unauthorized
            403: Forbidden
        """
        try:
            user_id = g.get('user_id')
            user_role = g.get('user', {}).get('role', 'operator')
            
            # Parse query parameters
            active_only = request.args.get("active_only", "true").lower() == "true"
            status_filter = request.args.get("status")
            show_all = request.args.get("all", "false").lower() == "true"
            
            limit = request.args.get("limit", "100")
            try:
                limit = int(limit)
                if limit < 1 or limit > 1000:
                    return jsonify({"error": "limit must be between 1 and 1000"}), 400
            except ValueError:
                return jsonify({"error": "limit must be an integer"}), 400
            
            skip = request.args.get("skip", "0")
            try:
                skip = int(skip)
                if skip < 0:
                    return jsonify({"error": "skip must be >= 0"}), 400
            except ValueError:
                return jsonify({"error": "skip must be an integer"}), 400
            
            # For operators, filter by user (unless admin with ?all=true)
            vehicles = vehicle_service.list_vehicles(
                active_only=active_only,
                status_filter=status_filter,
                limit=limit,
                skip=skip,
                user_id=user_id if (user_role != 'admin' or not show_all) else None
            )
            
            return jsonify({
                "vehicles": vehicles,
                "count": len(vehicles),
                "limit": limit,
                "skip": skip
            }), 200
            
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/by-plate/<plate>", methods=["GET"])
    @require_role(["admin", "operator"])
    def get_vehicle_by_plate(plate):
        """
        Get a vehicle by plate number.
        
        Required role: admin, operator
        
        Returns:
            200: Vehicle document
            404: Vehicle not found
            401: Unauthorized
            403: Forbidden
        """
        try:
            vehicle = vehicle_service.get_vehicle_by_plate(plate)
            if not vehicle:
                return jsonify({"error": f"Vehicle with plate {plate} not found"}), 404
            
            return jsonify(vehicle), 200
            
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/available", methods=["GET"])
    @require_role(["admin", "operator"])
    def list_available():
        """
        List all available vehicles.
        
        Required role: admin, operator
        
        Returns:
            200: List of available vehicles
            401: Unauthorized
            403: Forbidden
        """
        try:
            vehicles = vehicle_service.list_vehicles(
                active_only=True,
                status_filter="available"
            )
            
            return jsonify({
                "vehicles": vehicles,
                "count": len(vehicles)
            }), 200
            
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/expiring-documents", methods=["GET"])
    @require_role(["admin", "operator"])
    def get_expiring_documents():
        """
        Get vehicles with expiring SOAT and/or technical review documents.
        
        Required role: admin, operator
        
        Query parameters:
            - soat_days (int, default 30): Days threshold for SOAT expiry
            - tech_days (int, default 30): Days threshold for tech review expiry
        
        Returns:
            200: Object with soat_expiring and tech_review_expiring lists
            400: Invalid query parameters
            401: Unauthorized
            403: Forbidden
        """
        try:
            # Parse query parameters
            soat_days = request.args.get("soat_days", "30")
            tech_days = request.args.get("tech_days", "30")
            
            try:
                soat_days = int(soat_days)
                if soat_days < 1:
                    return jsonify({"error": "soat_days must be >= 1"}), 400
            except ValueError:
                return jsonify({"error": "soat_days must be an integer"}), 400
            
            try:
                tech_days = int(tech_days)
                if tech_days < 1:
                    return jsonify({"error": "tech_days must be >= 1"}), 400
            except ValueError:
                return jsonify({"error": "tech_days must be an integer"}), 400
            
            result = vehicle_service.get_expiring_documents(
                soat_days=soat_days,
                tech_days=tech_days
            )
            
            return jsonify(result), 200
            
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    # Generic /<vehicle_id> route MUST be AFTER specific routes like /by-plate, /available, /expiring-documents
    @bp.route("/<vehicle_id>", methods=["GET"])
    @require_role(["admin", "operator"])
    @require_ownership(lambda vehicle_id: _get_vehicle_for_ownership(vehicle_id))
    def get_vehicle(vehicle_id):
        """
        Get a specific vehicle by ID.
        
        Required role: admin, operator
        Ownership: Must own the vehicle or be admin
        
        Returns:
            200: Vehicle document
            401: Unauthorized
            403: Forbidden (not the owner)
            404: Vehicle not found
        """
        try:
            vehicle = vehicle_service.get_vehicle(vehicle_id)
            if not vehicle:
                return jsonify({"error": f"Vehicle {vehicle_id} not found"}), 404
            
            return jsonify(vehicle), 200
            
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/<vehicle_id>", methods=["PUT"])
    @rate_limit(limit=50, window=60)
    @require_role(["admin", "operator"])
    @require_ownership(lambda vehicle_id: _get_vehicle_for_ownership(vehicle_id))
    def update_vehicle(vehicle_id):
        """
        Update vehicle data with Pydantic validation.
        
        Required role: admin, operator
        Ownership: Must own the vehicle or be admin
        
        Body:
            - plate (str, optional): Vehicle plate
            - vehicle_type (str, optional): Vehicle type
            - brand (str, optional): Manufacturer
            - model_year (int, optional): Year
            - capacity_tons (float, optional): Capacity
            - volume_m3 (float, optional): Volume
            - soat_expiry (datetime, optional): SOAT expiry
            - tech_review_expiry (datetime, optional): Tech review expiry
        
        Returns:
            200: Updated vehicle
            400: Validation error
            404: Vehicle not found
            409: Duplicate plate
            401: Unauthorized
            403: Forbidden
            422: Invalid request data
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            
            # Validate using Pydantic
            validated_update = VehicleUpdate(**data)
            update_dict = validated_update.model_dump(exclude_unset=True)
            
            updated = vehicle_service.update_vehicle(vehicle_id, update_dict)
            return jsonify(updated), 200
            
        except ValidationError as e:
            # Pydantic validation error
            return jsonify({
                "error": "validation_error",
                "details": e.errors()
            }), 422
        except VehicleValidationError as e:
            return jsonify({"error": str(e)}), 400
        except VehicleNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except VehicleAlreadyExistsError as e:
            return jsonify({"error": str(e)}), 409
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/<vehicle_id>", methods=["DELETE"])
    @rate_limit(limit=20, window=60)
    @require_role(["admin", "operator"])
    @require_ownership(lambda vehicle_id: _get_vehicle_for_ownership(vehicle_id))
    def delete_vehicle(vehicle_id):
        """
        Delete a vehicle (soft delete).
        
        Required role: admin, operator
        Ownership: Must own the vehicle or be admin
        
        Returns:
            204: No content (success)
            404: Vehicle not found
            401: Unauthorized
            403: Forbidden
        """
        try:
            success = vehicle_service.delete_vehicle(vehicle_id)
            if not success:
                return jsonify({"error": f"Vehicle {vehicle_id} not found"}), 404
            
            return "", 204
            
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/<vehicle_id>/status", methods=["PATCH"])
    @rate_limit(limit=50, window=60)
    @require_role(["admin", "operator"])
    @require_ownership(lambda vehicle_id: _get_vehicle_for_ownership(vehicle_id))
    def update_status(vehicle_id):
        """
        Update vehicle status.
        
        Required role: admin, operator
        Ownership: Must own the vehicle or be admin
        
        Body:
            - status (str, required): New status (available, in_trip, inactive)
        
        Returns:
            200: Updated vehicle
            400: Validation error (invalid status)
            404: Vehicle not found
            401: Unauthorized
            403: Forbidden (not the owner)
        """
        try:
            data = request.get_json()
            if not data or "status" not in data:
                return jsonify({"error": "status field is required"}), 400
            
            updated = vehicle_service.update_vehicle_status(vehicle_id, data["status"])
            return jsonify(updated), 200
            
        except VehicleValidationError as e:
            return jsonify({"error": str(e)}), 400
        except VehicleNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except VehicleError as e:
            return jsonify({"error": str(e)}), 500
    
    return bp
