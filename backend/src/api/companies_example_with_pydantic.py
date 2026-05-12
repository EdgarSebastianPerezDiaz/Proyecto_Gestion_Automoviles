"""
EXAMPLE: How to use Pydantic schemas in Flask endpoints.

This file demonstrates the recommended pattern for integrating Pydantic
schemas into Flask API endpoints. Copy this pattern to other endpoints.

Key Benefits:
- Automatic request validation
- Type checking
- Custom validators run automatically
- Clear error messages
- Self-documenting API
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
from src.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyListResponse,
)
from src.api.auth_decorator import require_role


def create_companies_blueprint_example(company_service: CompanyService) -> Blueprint:
    """
    Example: Companies blueprint with Pydantic schema integration.
    
    This shows the recommended pattern for using Pydantic schemas.
    """
    bp = Blueprint("companies_example", __name__, url_prefix="/api/companies-v2")
    
    @bp.route("/", methods=["POST"])
    @require_role(["admin"])
    def create_company():
        """
        Create a new company - WITH PYDANTIC VALIDATION.
        
        BEFORE (without validation):
            data = request.get_json()
            company = company_service.create_company(data)
        
        AFTER (with Pydantic validation):
            data = request.get_json()
            validated_data = CompanyCreate(**data)  # Validates here!
            company = company_service.create_company(validated_data.dict())
        
        Benefits:
        - Email is automatically normalized (lowercased)
        - NIT is validated and formatted to XXXXXXXXX-Y
        - All required fields are checked
        - Clear error messages for invalid data
        - Type hints for IDE support
        
        Request Body:
        {
            "nit": "123.456.789-0",  # Will be normalized to "123456789-0"
            "legal_name": "Company Name",
            "address": "Address",
            "city": "City",
            "phone": "+57 1 234 5678",
            "email": "CONTACT@COMPANY.COM",  # Will be lowercased
            "trade_name": "Optional trade name",
            "contact_name": "Contact person"
        }
        
        Returns:
            201: Created company
            {
                "_id": "507f...",
                "nit": "123456789-0",
                "legal_name": "Company Name",
                "email": "contact@company.com",
                "is_active": true,
                "created_at": "2024-01-15T...",
                "updated_at": "2024-01-15T..."
            }
            
            400: Validation error
            {
                "error": "validation_error",
                "details": [
                    {
                        "loc": ["nit"],
                        "msg": "Invalid NIT format: ABC123",
                        "type": "value_error"
                    }
                ]
            }
        """
        try:
            # 1. Get raw JSON from request
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            
            # 2. Validate and normalize using Pydantic
            # This will raise ValidationError if invalid
            validated_company = CompanyCreate(**data)
            
            # 3. Convert to dict for service layer
            company_dict = validated_company.model_dump()
            
            # 4. Pass validated data to service
            company = company_service.create_company(company_dict)
            
            # 5. Return response
            return jsonify(company), 201
            
        except ValidationError as e:
            # Pydantic validation error - return 400
            return jsonify({
                "error": "validation_error",
                "details": e.errors()
            }), 400
            
        except CompanyAlreadyExistsError as e:
            return jsonify({"error": str(e)}), 409
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/<company_id>", methods=["PUT"])
    @require_role(["admin"])
    def update_company(company_id: str):
        """
        Update a company - WITH PYDANTIC VALIDATION.
        
        Benefits:
        - Only provided fields are validated and updated
        - Email is normalized if provided
        - Invalid updates are rejected immediately
        - Clear error messages
        
        Request Body (all fields optional):
        {
            "legal_name": "New Name",
            "phone": "New Phone",
            "email": "NEW@EMAIL.COM"
        }
        
        Returns:
            200: Updated company
            400: Validation error
            404: Company not found
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            
            # Validate update data using Pydantic
            # CompanyUpdate ensures at least one field is provided
            validated_update = CompanyUpdate(**data)
            
            # Convert to dict
            update_dict = validated_update.model_dump(exclude_unset=True)
            
            # Pass to service
            company = company_service.update_company(company_id, update_dict)
            
            return jsonify(company), 200
            
        except ValidationError as e:
            return jsonify({
                "error": "validation_error",
                "details": e.errors()
            }), 400
            
        except CompanyNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except CompanyError as e:
            return jsonify({"error": str(e)}), 500
    
    return bp


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================

"""
HOW TO INTEGRATE PYDANTIC INTO EXISTING ENDPOINTS:

1. IMPORT SCHEMAS:
   from src.schemas.company import CompanyCreate, CompanyUpdate

2. IN CREATE ENDPOINT:
   - Get JSON: data = request.get_json()
   - Validate: validated = CompanyCreate(**data)
   - Convert: dict_data = validated.model_dump()
   - Use: service.create(dict_data)
   - Catch ValidationError for invalid data

3. IN UPDATE ENDPOINT:
   - Get JSON: data = request.get_json()
   - Validate: validated = CompanyUpdate(**data)
   - Convert: dict_data = validated.model_dump(exclude_unset=True)
   - Use: service.update(id, dict_data)
   - Note: exclude_unset=True only includes provided fields

4. IN RESPONSES:
   - Use response.model_dump() or .model_validate()
   - For lists: [item.model_dump() for item in items]

5. ERROR HANDLING:
   try:
       validated = Schema(**data)
   except ValidationError as e:
       return jsonify({"error": e.errors()}), 400

VALIDATION HAPPENS AUTOMATICALLY:
- Email is lowercased
- NIT is formatted to XXXXXXXXX-Y
- Whitespace is stripped
- Types are checked
- Custom validators run
- Helpful error messages returned

EXAMPLE SCHEMAS:

# Create (all required fields):
class CompanyCreate(BaseModel):
    nit: str
    legal_name: str
    email: EmailStr
    # validators...

# Update (all optional fields):
class CompanyUpdate(BaseModel):
    nit: Optional[str]
    legal_name: Optional[str]
    email: Optional[EmailStr]
    # validators...

# Response (includes IDs and metadata):
class CompanyResponse(BaseModel):
    _id: str
    nit: str
    legal_name: str
    email: str
    created_at: datetime
    updated_at: datetime

TESTING:

# Valid request:
response = client.post('/api/companies', json={
    'nit': '1234567890',
    'legal_name': 'Company',
    'email': 'test@test.com',
    'address': 'Address',
    'city': 'City',
    'phone': '1234567'
})
assert response.status_code == 201

# Invalid NIT:
response = client.post('/api/companies', json={
    'nit': 'INVALID',  # Will be rejected!
    'legal_name': 'Company',
    'email': 'test@test.com',
    'address': 'Address',
    'city': 'City',
    'phone': '1234567'
})
assert response.status_code == 400
assert 'Invalid NIT format' in response.json['error']['details'][0]['msg']

# Missing field:
response = client.post('/api/companies', json={
    'legal_name': 'Company'
    # nit is missing!
})
assert response.status_code == 400
"""
