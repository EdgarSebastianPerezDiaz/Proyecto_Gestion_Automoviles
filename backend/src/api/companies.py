"""
Companies API blueprint - REST endpoints for company operations.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
from src.services.company_service import (
    CompanyService,
    CompanyError,
    CompanyValidationError,
    CompanyNotFoundError,
    CompanyAlreadyExistsError,
)
from src.schemas.company import CompanyCreate, CompanyUpdate
from src.api.auth_decorator import require_role
from src.infrastructure.rate_limiter import rate_limit


def create_companies_blueprint(company_service: CompanyService) -> Blueprint:
    """
    Create companies blueprint with all endpoints.
    
    Args:
        company_service: CompanyService instance for business logic
        
    Returns:
        Flask Blueprint with company endpoints
    """
    bp = Blueprint("companies", __name__, url_prefix="/api/companies")
    
    @bp.route("/", methods=["POST"])
    @rate_limit(limit=30, window=60)
    @require_role(["admin"])
    def create_company():
        """
        Create a new company.
        
        Required role: admin
        
        Body:
            - nit (str, required): Company NIT (e.g., "123456789-0")
            - legal_name (str, required): Company legal name
            - trade_name (str, optional): Company trade name
            - address (str, required): Company address
            - city (str, required): City
            - phone (str, required): Contact phone
            - email (str, required): Company email
            - contact_name (str, optional): Contact person name
        
        Returns:
            201: Created company with _id, created_at, updated_at
            422: Validation error
            409: Company already exists (same NIT or email)
            401: Unauthorized (missing/invalid token)
            403: Forbidden (insufficient permissions)
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            
            # Validate using Pydantic
            validated_data = CompanyCreate(**data)
            company_dict = validated_data.model_dump()
            
            company = company_service.create_company(company_dict)
            return jsonify(company), 201
            
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
        except CompanyAlreadyExistsError as e:
            return jsonify({"error": str(e)}), 409
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/", methods=["GET"])
    @require_role(["admin", "operator"])
    def list_companies():
        """
        List companies with optional filtering.
        
        Required role: admin, operator
        
        Query parameters:
            - active_only (bool, default true): Return only active companies
            - limit (int, default 100, max 1000): Maximum results
            - skip (int, default 0): Pagination offset
        
        Returns:
            200: List of companies
            400: Invalid query parameters
            401: Unauthorized
            403: Forbidden
        """
        try:
            # Parse query parameters
            active_only = request.args.get("active_only", "true").lower() == "true"
            
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
                    return jsonify({"error": "skip cannot be negative"}), 400
            except ValueError:
                return jsonify({"error": "skip must be an integer"}), 400
            
            companies = company_service.list_companies(
                active_only=active_only,
                limit=limit,
                skip=skip
            )
            return jsonify({
                "data": companies,
                "count": len(companies),
                "limit": limit,
                "skip": skip,
            }), 200
            
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/<company_id>", methods=["GET"])
    @require_role(["admin", "operator"])
    def get_company(company_id: str):
        """
        Get company by ID.
        
        Required role: admin, operator
        
        Returns:
            200: Company details
            404: Company not found
            401: Unauthorized
            403: Forbidden
        """
        try:
            company = company_service.get_company(company_id)
            return jsonify(company), 200
        except CompanyNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/by-nit/<nit>", methods=["GET"])
    @require_role(["admin", "operator"])
    def get_company_by_nit(nit: str):
        """
        Get company by NIT.
        
        Required role: admin, operator
        
        Args:
            nit: Company NIT (with or without formatting)
        
        Returns:
            200: Company details
            404: Company not found
            401: Unauthorized
            403: Forbidden
        """
        try:
            company = company_service.get_company_by_nit(nit)
            if not company:
                return jsonify({"error": f"Company with NIT {nit} not found"}), 404
            return jsonify(company), 200
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/<company_id>", methods=["PUT"])
    @rate_limit(limit=50, window=60)
    @require_role(["admin"])
    def update_company(company_id: str):
        """
        Update company data.
        
        Required role: admin
        
        Body:
            Any updatable fields: legal_name, trade_name, address, city, phone,
            email, contact_name, nit, is_active, etc.
        
        Returns:
            200: Updated company
            422: Validation error
            404: Company not found
            409: Conflict (e.g., NIT already in use)
            401: Unauthorized
            403: Forbidden
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            
            # Validate using Pydantic
            validated_update = CompanyUpdate(**data)
            update_dict = validated_update.model_dump(exclude_unset=True)
            
            company = company_service.update_company(company_id, update_dict)
            return jsonify(company), 200
            
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
        except CompanyNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except CompanyValidationError as e:
            return jsonify({"error": str(e)}), 409
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/<company_id>", methods=["DELETE"])
    @rate_limit(limit=20, window=60)
    @require_role(["admin"])
    def delete_company(company_id: str):
        """
        Soft delete a company (mark as inactive).
        
        Required role: admin
        
        Returns:
            204: No content (success)
            404: Company not found
            401: Unauthorized
            403: Forbidden
        """
        try:
            company_service.delete_company(company_id)
            return "", 204
        except CompanyNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    return bp
