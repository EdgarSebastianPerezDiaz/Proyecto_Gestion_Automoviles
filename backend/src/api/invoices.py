"""
Invoices API routes - endpoints for invoice management.
"""
from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime
from pydantic import ValidationError

from src.services.invoice_service import InvoiceService, InvoiceError
from src.schemas.invoice import InvoicePaymentUpdate
from src.infrastructure.database import MongoDBConnection
from src.api.auth_decorator import require_auth
from src.infrastructure.rate_limiter import rate_limit


# Create blueprint
invoices_bp = Blueprint('invoices', __name__, url_prefix='/api/invoices')

# Database connection (initialized by main app)
_db_connection: MongoDBConnection = None
_invoice_service: InvoiceService = None


def init_invoices_routes(db_connection: MongoDBConnection):
    """Initialize invoices routes with database connection."""
    global _db_connection, _invoice_service
    _db_connection = db_connection
    _invoice_service = InvoiceService(db_connection)


def handle_service_errors(f):
    """Decorator to handle service exceptions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except InvoiceError as e:
            if 'not found' in str(e).lower():
                return jsonify({'error': str(e)}), 404
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    return decorated_function


@invoices_bp.route('/<invoice_id>', methods=['GET'])
@require_auth
@handle_service_errors
def get_invoice(invoice_id):
    """
    Get invoice by ID.
    
    Returns:
        200: Invoice document
        404: Invoice not found
        500: Server error
    """
    invoice = _invoice_service.get_invoice(invoice_id)
    return jsonify(invoice), 200


@invoices_bp.route('/number/<invoice_number>', methods=['GET'])
@require_auth
@handle_service_errors
def get_invoice_by_number(invoice_number):
    """
    Get invoice by invoice number.
    
    Parameters:
        invoice_number: Invoice number (e.g., INV-000001)
    
    Returns:
        200: Invoice document
        404: Invoice not found
        500: Server error
    """
    invoice = _invoice_service.get_invoice_by_number(invoice_number)
    return jsonify(invoice), 200


@invoices_bp.route('', methods=['GET'])
@require_auth
@handle_service_errors
def list_invoices():
    """
    List invoices with optional filters.
    
    Query parameters:
        client_id: Filter by client ID
        status: Filter by status (generated, sent, etc.)
        payment_status: Filter by payment status (pending, paid)
        limit: Maximum results (default: 100)
        skip: Pagination offset (default: 0)
    
    Returns:
        200: List of invoice documents
        500: Server error
    """
    filters = {}
    
    # Build filter from query params
    if request.args.get('client_id'):
        filters['client_id'] = request.args.get('client_id')
    if request.args.get('status'):
        filters['status'] = request.args.get('status')
    if request.args.get('payment_status'):
        filters['payment_status'] = request.args.get('payment_status')
    
    limit = int(request.args.get('limit', 100))
    skip = int(request.args.get('skip', 0))
    
    invoices = _invoice_service.list_invoices(filters, limit=limit, skip=skip)
    return jsonify(invoices), 200


@invoices_bp.route('/<invoice_id>/payment', methods=['PATCH'])
@rate_limit(limit=50, window=60)
@require_auth
@handle_service_errors
def mark_invoice_as_paid(invoice_id):
    """
    Mark invoice as paid.
    
    Request body:
    {
        "payment_date": "2024-01-20",  # ISO format or datetime
        "reference": "PAY-12345",      # Payment reference (optional)
        "method": "transfer"           # Payment method (optional)
    }
    
    Returns:
        200: Updated invoice document
        422: Validation error
        404: Invoice not found
        500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate using Pydantic
        validated_payment = InvoicePaymentUpdate(**data)
        payment_dict = validated_payment.model_dump(exclude_unset=True)
        
        invoice = _invoice_service.mark_as_paid(invoice_id, payment_dict)
        return jsonify(invoice), 200
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
    except ValueError as e:
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400


@invoices_bp.route('/<invoice_id>/download', methods=['GET'])
@require_auth
@handle_service_errors
def download_invoice(invoice_id):
    """
    Get invoice PDF download URL.
    
    Returns:
        200: PDF URL
        404: Invoice not found
        500: Server error
    """
    invoice = _invoice_service.get_invoice(invoice_id)
    pdf_url = invoice.get('pdf_url')
    
    if not pdf_url:
        return jsonify({'error': 'PDF not yet generated'}), 404
    
    return jsonify({
        'invoice_id': invoice_id,
        'invoice_number': invoice.get('invoice_number'),
        'pdf_url': pdf_url
    }), 200


@invoices_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404
