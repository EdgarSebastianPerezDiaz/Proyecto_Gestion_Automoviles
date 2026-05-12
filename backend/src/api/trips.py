"""
Trips API routes - endpoints for trip management.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
from functools import wraps
from datetime import datetime
import logging

from src.services.trip_service import TripService, TripError, TripValidationError, TripNotFoundError
from src.schemas.trip import TripCreate, TripStatusUpdate
from src.schemas.pagination import TripFilters
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.s3_uploader import S3Uploader, S3Error
from src.infrastructure.rate_limiter import rate_limit
from src.api.auth_decorator import require_auth, require_role, require_ownership
from src.domain.exceptions import NotFoundError

logger = logging.getLogger(__name__)


# Create blueprint
trips_bp = Blueprint('trips', __name__, url_prefix='/api/trips')

# Database connection (initialized by main app)
_db_connection: MongoDBConnection = None
_trip_service: TripService = None
_s3_uploader: S3Uploader = None


def init_trips_routes(db_connection: MongoDBConnection):
    """Initialize trips routes with database connection."""
    global _db_connection, _trip_service, _s3_uploader
    _db_connection = db_connection
    _trip_service = TripService(db_connection)
    try:
        _s3_uploader = S3Uploader()
    except S3Error as e:
        logger.warning(f"S3 uploader not initialized: {str(e)}. Presigned URL endpoint will be unavailable.")


def _get_trip_for_ownership(trip_id: str) -> dict:
    """Helper function to get trip for ownership verification."""
    if not _trip_service:
        return None
    try:
        return _trip_service.get_trip(trip_id)
    except Exception:
        # Return None if trip not found or any error occurs
        # The require_ownership decorator will raise NotFoundError which will be caught by error handler
        return None


def handle_service_errors(f):
    """Decorator to handle service exceptions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except TripValidationError as e:
            return jsonify({'error': str(e)}), 400
        except TripNotFoundError as e:
            return jsonify({'error': str(e)}), 404
        except TripError as e:
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    return decorated_function


@trips_bp.route('', methods=['POST'])
@rate_limit(limit=30, window=60)
@require_auth
@handle_service_errors
def create_trip():
    """
    Create a new trip with Pydantic validation.
    
    Request body:
    {
        "origin": "Bogotá",
        "destination": "Medellín",
        "departure_date": "2024-01-15T08:00:00Z",
        "arrival_date": "2024-01-15T18:00:00Z",
        "weight_tons": 10.5,
        "total_cost": 1500000,
        "vehicle_id": "...",
        "driver_id": "...",
        "cargo_id": "...",
        "client_id": "...",
        "recipient_id": "...",
        "notes": "Special handling required (optional)"
    }
    
    Returns:
        201: Created trip document
        400: Validation error
        422: Invalid request data
        500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        user_id = g.get('user_id')  # From require_auth decorator
        
        # Validate using Pydantic
        validated_trip = TripCreate(**data)
        trip_dict = validated_trip.model_dump()
        
        trip = _trip_service.create_trip(trip_dict, user_id)
        return jsonify(trip), 201
        
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


@trips_bp.route('/<trip_id>', methods=['GET'])
@require_auth
@require_ownership(lambda trip_id: _get_trip_for_ownership(trip_id))
@handle_service_errors
def get_trip(trip_id):
    """
    Get trip by ID.
    
    Returns:
        200: Trip document
        404: Trip not found
        403: Forbidden (not the owner of the resource)
        500: Server error
    """
    trip = _trip_service.get_trip(trip_id)
    return jsonify(trip), 200


@trips_bp.route('/<trip_id>', methods=['PUT'])
@rate_limit(limit=50, window=60)
@require_auth
@handle_service_errors
@require_ownership(lambda trip_id: _get_trip_for_ownership(trip_id))
def update_trip(trip_id):
    """
    Update trip information.
    
    Request body: Any trip fields to update (origin, destination, notes, etc.)
    
    Returns:
        200: Updated trip document
        404: Trip not found
        403: Forbidden (not the owner)
        500: Server error
    """
    from datetime import datetime, timezone
    from bson.objectid import ObjectId
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Add updated_at timestamp
    data['updated_at'] = datetime.now(timezone.utc)
    
    try:
        # Convert trip_id to ObjectId for database lookup
        object_id = ObjectId(trip_id)
    except Exception:
        return jsonify({'error': f'Invalid trip ID format: {trip_id}'}), 400
    
    # Update the trip
    updated = _trip_service.trip_repo.update_one(
        {'_id': object_id},
        {'$set': data}
    )
    
    if not updated:
        return jsonify({'error': f'Trip {trip_id} not found'}), 404
    
    # Return updated trip
    trip = _trip_service.get_trip(trip_id)
    return jsonify(trip), 200


@trips_bp.route('', methods=['GET'])
@require_auth
@handle_service_errors
def list_trips():
    """
    List trips with optional filters and pagination.
    
    Query parameters:
        page: Page number (1-100, default: 1)
        limit: Items per page (1-100, default: 50)
        q: Search query (1-100 characters, optional)
        status: Trip status filter (pending/in_transit/completed/cancelled, optional)
        client_id: Filter by client MongoDB ObjectId (24 hex chars, optional)
        vehicle_id: Filter by vehicle MongoDB ObjectId (24 hex chars, optional)
        driver_id: Filter by driver MongoDB ObjectId (24 hex chars, optional)
        from_date: Start date (ISO8601 YYYY-MM-DD format, optional)
        to_date: End date (ISO8601 YYYY-MM-DD format, optional)
    
    Returns:
        200: List of trip documents
        422: Invalid query parameters (Pydantic validation error)
        500: Server error
    
    Example:
        GET /api/trips?page=1&limit=50&status=completed&from_date=2026-01-01
    """
    try:
        # Validate and parse query parameters using Pydantic
        filters_obj = TripFilters(**request.args.to_dict())
    except ValidationError as e:
        # Return 422 Unprocessable Entity with validation errors
        error_details = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            error_details.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            "Query parameter validation failed",
            extra={
                "correlation_id": g.correlation_id,
                "errors": error_details,
                "query_params": request.args.to_dict()
            }
        )
        
        return jsonify({
            "status": "error",
            "message": "Invalid query parameters",
            "errors": error_details
        }), 422
    
    # Extract user context
    user_id = g.get('user_id')
    user_role = g.get('user', {}).get('role', 'operator')
    
    # Build database query filters from validated parameters
    db_filters = {}
    
    # Add trip-specific filters if provided
    if filters_obj.status:
        db_filters['status'] = filters_obj.status
    
    if filters_obj.client_id:
        db_filters['client_id'] = filters_obj.client_id
    
    if filters_obj.vehicle_id:
        db_filters['vehicle_id'] = filters_obj.vehicle_id
    
    if filters_obj.driver_id:
        db_filters['driver_id'] = filters_obj.driver_id
    
    if filters_obj.from_date or filters_obj.to_date:
        date_filter = {}
        if filters_obj.from_date:
            date_filter['$gte'] = filters_obj.from_date
        if filters_obj.to_date:
            date_filter['$lte'] = filters_obj.to_date
        
        if date_filter:
            db_filters['date'] = date_filter
    
    # Apply ownership filter for non-admin users
    # NOTE: If you want to support 'show_all' parameter, add it to TripFilters
    # For now, non-admin users always see only their trips
    if user_role != 'admin':
        db_filters['created_by'] = user_id
    
    # Convert page to skip offset (page 1 = skip 0, page 2 = skip limit, etc.)
    skip = (filters_obj.page - 1) * filters_obj.limit
    
    # Fetch trips from service
    trips = _trip_service.list_trips(db_filters, limit=filters_obj.limit, skip=skip)
    
    logger.debug(
        "Trips listed successfully",
        extra={
            "correlation_id": g.correlation_id,
            "count": len(trips) if trips else 0,
            "page": filters_obj.page,
            "limit": filters_obj.limit,
            "filters": db_filters
        }
    )
    
    return jsonify(trips), 200


@trips_bp.route('/<trip_id>/status', methods=['PATCH'])
@rate_limit(limit=50, window=60)
@require_auth
@handle_service_errors
@require_ownership(lambda trip_id: _get_trip_for_ownership(trip_id))
def update_trip_status(trip_id):
    """
    Update trip status with Pydantic validation and automatic side effects.
    
    Request body:
    {
        "status_id": "507f...",  # Trip status ID (MongoDB ObjectId)
        "notes": "Arrived at destination (optional)"
    }
    
    Returns:
        200: Updated trip document
        400: Invalid status code
        404: Trip not found (via NotFoundError handled by error handler)
        403: Forbidden (not the owner)
        422: Invalid request data
        500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        user_id = g.get('user_id')  # From require_auth decorator
        
        # Validate using Pydantic
        validated_update = TripStatusUpdate(**data)
        update_dict = validated_update.model_dump()
        
        trip = _trip_service.update_trip_status(trip_id, update_dict['status_id'], user_id, notes=update_dict.get('notes'))
        return jsonify(trip), 200
        
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


@trips_bp.route('/<trip_id>/documents', methods=['GET'])
@require_auth
@handle_service_errors
def get_trip_documents(trip_id):
    """
    Get presigned URLs for all documents of a trip.
    
    Generates fresh presigned URLs (1-hour expiration) for direct S3 downloads.
    Accessible by admin and operator roles.
    
    Returns:
        200: Dictionary of presigned document URLs
        {
            "trip_id": "...",
            "documents": {
                "order_pdf": "https://s3.../documents/orden-tripid.pdf?X-Amz-Algorithm=...",
                "manifest_pdf": "https://s3.../documents/manifesto-tripid.pdf?X-Amz-Algorithm=...",
                ...
            },
            "expires_in_seconds": 3600
        }
        404: Trip not found or has no documents
        500: Server error (S3 unavailable)
    """
    # Verify trip exists
    trip = _trip_service.get_trip(trip_id)
    documents = trip.get('documents', {})
    
    if not documents:
        return jsonify({
            'error': 'Trip has no documents',
            'trip_id': trip_id
        }), 404
    
    # Check if S3 uploader is available
    if not _s3_uploader:
        return jsonify({
            'error': 'Document download service is unavailable',
            'trip_id': trip_id
        }), 503
    
    # Map document keys to S3 key patterns
    # The mapping is: document_key → (filename_prefix)
    doc_mapping = {
        'order_pdf': ('orden', 'Orden de Cargue'),
        'manifest_pdf': ('manifesto', 'Manifiesto'),
        'cumplido_pdf': ('cumplido', 'Cumplido'),
        'invoice_pdf': ('invoice', 'Factura')
    }
    
    presigned_documents = {}
    
    try:
        for doc_key, (filename_prefix, doc_name) in doc_mapping.items():
            # Only generate presigned URL if document exists in trip
            if doc_key in documents:
                try:
                    # Reconstruct S3 key based on pattern: documents/{prefix}-{tripid}.pdf
                    s3_key = f"documents/{filename_prefix}-{trip_id}.pdf"
                    
                    # Generate fresh presigned URL (1 hour expiration)
                    presigned_url = _s3_uploader.generate_presigned_url(s3_key, expiration=3600)
                    
                    presigned_documents[doc_key] = {
                        'url': presigned_url,
                        'name': doc_name,
                        'type': 'application/pdf'
                    }
                    
                except S3Error as e:
                    logger.warning(f"Failed to generate presigned URL for {doc_key}: {str(e)}")
                    # If one document fails, still return others
                    presigned_documents[doc_key] = {
                        'error': 'Failed to generate presigned URL',
                        'name': doc_name
                    }
        
        if not presigned_documents:
            return jsonify({
                'error': 'Could not generate presigned URLs for any documents',
                'trip_id': trip_id
            }), 500
        
        return jsonify({
            'trip_id': trip_id,
            'documents': presigned_documents,
            'expires_in_seconds': 3600
        }), 200
        
    except S3Error as e:
        logger.error(f"S3 error generating presigned URLs for trip {trip_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to generate presigned URLs',
            'trip_id': trip_id
        }), 500


@trips_bp.route('/<trip_id>/download/<document_type>', methods=['GET'])
@require_auth
def download_trip_document(trip_id, document_type):
    """
    Redirect to presigned URL for document download.
    
    This endpoint fetches a fresh presigned URL and redirects the user to S3.
    Useful for implementing download links in the frontend.
    
    Args:
        trip_id: Trip ID
        document_type: Type of document (order, manifest, cumplido, invoice)
        
    Returns:
        302: Redirect to presigned S3 URL
        400: Invalid document type
        404: Trip or document not found
        500: Server error
    """
    from flask import redirect
    
    # Verify trip exists
    try:
        trip = _trip_service.get_trip(trip_id)
    except TripNotFoundError:
        return jsonify({'error': f'Trip not found: {trip_id}'}), 404
    
    documents = trip.get('documents', {})
    
    # Map document types to S3 key patterns
    doc_type_map = {
        'order': ('orden', 'order_pdf'),
        'manifest': ('manifesto', 'manifest_pdf'),
        'cumplido': ('cumplido', 'cumplido_pdf'),
        'invoice': ('invoice', 'invoice_pdf')
    }
    
    if document_type not in doc_type_map:
        return jsonify({'error': f'Invalid document type: {document_type}'}), 400
    
    filename_prefix, doc_key = doc_type_map[document_type]
    
    if doc_key not in documents:
        return jsonify({'error': f'Document not found: {document_type}'}), 404
    
    if not _s3_uploader:
        return jsonify({'error': 'Document download service is unavailable'}), 503
    
    try:
        # Generate presigned URL
        s3_key = f"documents/{filename_prefix}-{trip_id}.pdf"
        presigned_url = _s3_uploader.generate_presigned_url(s3_key, expiration=3600)
        
        # Redirect to the presigned URL
        return redirect(presigned_url, code=302)
        
    except S3Error as e:
        logger.error(f"Failed to generate presigned URL for {document_type}: {str(e)}")
        return jsonify({'error': 'Failed to generate document URL'}), 500


@trips_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404
