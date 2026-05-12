"""
Trip Document Reconciler Lambda

Scheduled function that runs every hour to reconcile trips in 'in_transit' status
that are missing PDF documents (order or manifest).

This function:
1. Finds trips in 'in_transit' status with missing documents
2. Regenerates missing PDFs
3. Uploads them to S3
4. Updates trip documents
5. Logs actions to audit trail
6. Publishes errors to SNS

Execution: Every hour via EventBridge schedule
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import boto3
from botocore.exceptions import ClientError

# Custom imports
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.pdf_generator import (
    generate_orden_cargue,
    generate_manifesto,
    PDFGenerationError
)
from src.infrastructure.s3_uploader import S3Uploader, S3Error
from src.services.audit_service import AuditService, _serialize_document

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
BATCH_SIZE = 50  # Process up to 50 trips per invocation
RETRY_ATTEMPTS = 2


class ReconciliationError(Exception):
    """Base exception for reconciliation errors."""
    pass


def _get_trip_status_id(connection: MongoDBConnection, status_code: str) -> Optional[str]:
    """
    Get the ObjectId of a trip status by its code.
    
    Args:
        connection: MongoDB connection
        status_code: Status code (e.g., 'in_transit')
        
    Returns:
        ObjectId as string, or None if not found
    """
    try:
        trip_statuses_coll = connection.get_collection('trip_statuses')
        status_doc = trip_statuses_coll.find_one({'code': status_code})
        
        if status_doc:
            return str(status_doc['_id'])
        
        logger.warning(f"Trip status '{status_code}' not found in database")
        return None
    
    except Exception as e:
        logger.error(f"Error finding trip status: {str(e)}")
        return None


def _get_enriched_trip_data(connection: MongoDBConnection, trip: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich trip data with related entities (vehicle, driver, cargo, client, recipient).
    
    Args:
        connection: MongoDB connection
        trip: Trip document
        
    Returns:
        Enriched trip document
    """
    enriched = dict(trip)
    
    # Collections
    vehicles_coll = connection.get_collection('vehicles')
    drivers_coll = connection.get_collection('drivers')
    cargo_types_coll = connection.get_collection('cargo_types')
    clients_coll = connection.get_collection('clients')
    recipients_coll = connection.get_collection('final_recipients')
    
    # Enrich with relationships
    try:
        if trip.get('vehicle_id'):
            vehicle = vehicles_coll.find_one({'_id': trip['vehicle_id']})
            if vehicle:
                enriched['vehicle'] = vehicle
        
        if trip.get('driver_id'):
            driver = drivers_coll.find_one({'_id': trip['driver_id']})
            if driver:
                enriched['driver'] = driver
        
        if trip.get('cargo_id'):
            cargo = cargo_types_coll.find_one({'_id': trip['cargo_id']})
            if cargo:
                enriched['cargo'] = cargo
        
        if trip.get('client_id'):
            client = clients_coll.find_one({'_id': trip['client_id']})
            if client:
                enriched['client'] = client
        
        if trip.get('recipient_id'):
            recipient = recipients_coll.find_one({'_id': trip['recipient_id']})
            if recipient:
                enriched['recipient'] = recipient
    
    except Exception as e:
        logger.warning(f"Error enriching trip {trip.get('_id')}: {str(e)}")
    
    return enriched


def _find_trips_with_missing_documents(
    connection: MongoDBConnection,
    in_transit_status_id: str,
    limit: int = BATCH_SIZE
) -> List[Dict[str, Any]]:
    """
    Find trips in 'in_transit' status missing order or manifest PDF.
    
    Args:
        connection: MongoDB connection
        in_transit_status_id: ObjectId of 'in_transit' status
        limit: Maximum trips to process
        
    Returns:
        List of trip documents with missing documents
    """
    try:
        trips_coll = connection.get_collection('trips')
        
        # Find trips in in_transit that are missing documents
        query = {
            'status_id': in_transit_status_id,
            '$or': [
                {'documents.order_pdf': {'$exists': False}},
                {'documents.order_pdf': None},
                {'documents.manifest_pdf': {'$exists': False}},
                {'documents.manifest_pdf': None}
            ]
        }
        
        trips = list(trips_coll.find(query).limit(limit))
        logger.info(f"Found {len(trips)} trips with missing documents")
        
        return trips
    
    except Exception as e:
        logger.error(f"Error finding trips with missing documents: {str(e)}")
        return []


def _generate_and_upload_document(
    trip: Dict[str, Any],
    document_type: str,
    s3_uploader: S3Uploader,
    enriched_trip: Dict[str, Any]
) -> Optional[str]:
    """
    Generate and upload a missing PDF document.
    
    Args:
        trip: Trip document
        document_type: 'order' or 'manifest'
        s3_uploader: S3Uploader instance
        enriched_trip: Enriched trip data for PDF generation
        
    Returns:
        S3 presigned URL, or None if generation/upload failed
    """
    try:
        trip_id = str(trip['_id'])
        
        # Generate PDF based on type
        if document_type == 'order':
            pdf_bytes = generate_orden_cargue(enriched_trip)
            file_key = f"documents/orders/orden-{trip_id}.pdf"
        elif document_type == 'manifest':
            pdf_bytes = generate_manifesto(enriched_trip)
            file_key = f"documents/manifests/manifesto-{trip_id}.pdf"
        else:
            logger.error(f"Unknown document type: {document_type}")
            return None
        
        # Upload to S3
        url = s3_uploader.upload_pdf(pdf_bytes, file_key)
        logger.info(f"Generated and uploaded {document_type} PDF for trip {trip_id} to {file_key}")
        
        return url
    
    except PDFGenerationError as e:
        logger.error(f"PDF generation error for trip {trip.get('_id')} ({document_type}): {str(e)}")
        return None
    except S3Error as e:
        logger.error(f"S3 upload error for trip {trip.get('_id')} ({document_type}): {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error generating/uploading {document_type} for trip {trip.get('_id')}: {str(e)}")
        return None


def _reconcile_trip(
    trip: Dict[str, Any],
    connection: MongoDBConnection,
    s3_uploader: S3Uploader,
    audit_service: AuditService
) -> Dict[str, Any]:
    """
    Reconcile a single trip by generating missing documents.
    
    Args:
        trip: Trip document
        connection: MongoDB connection
        s3_uploader: S3Uploader instance
        audit_service: AuditService instance
        
    Returns:
        Dict with reconciliation results
    """
    trip_id = str(trip['_id'])
    result = {
        'trip_id': trip_id,
        'status': 'pending',
        'missing_docs': [],
        'repaired_docs': [],
        'errors': []
    }
    
    try:
        # Enrich trip with relationships
        enriched_trip = _get_enriched_trip_data(connection, trip)
        
        # Get previous state for audit
        previous_state = dict(trip)
        
        # Check what's missing
        documents = trip.get('documents', {})
        if not documents.get('order_pdf'):
            result['missing_docs'].append('order_pdf')
        if not documents.get('manifest_pdf'):
            result['missing_docs'].append('manifest_pdf')
        
        if not result['missing_docs']:
            result['status'] = 'no_repair_needed'
            return result
        
        # Generate and upload missing documents
        new_documents = dict(documents)
        
        if 'order_pdf' in result['missing_docs']:
            order_url = _generate_and_upload_document(trip, 'order', s3_uploader, enriched_trip)
            if order_url:
                new_documents['order_pdf'] = order_url
                result['repaired_docs'].append('order_pdf')
            else:
                result['errors'].append('Failed to generate order PDF')
        
        if 'manifest_pdf' in result['missing_docs']:
            manifest_url = _generate_and_upload_document(trip, 'manifest', s3_uploader, enriched_trip)
            if manifest_url:
                new_documents['manifest_pdf'] = manifest_url
                result['repaired_docs'].append('manifest_pdf')
            else:
                result['errors'].append('Failed to generate manifest PDF')
        
        # Update trip in database if documents were repaired
        if result['repaired_docs']:
            trips_coll = connection.get_collection('trips')
            trips_coll.update_one(
                {'_id': trip['_id']},
                {'$set': {'documents': new_documents, 'updated_at': datetime.now(timezone.utc)}}
            )
            
            # Get updated trip for audit
            updated_trip = trips_coll.find_one({'_id': trip['_id']})
            
            # Log to audit trail
            try:
                audit_service.log_action(
                    collection_name='trips',
                    document_id=trip_id,
                    action='FIX',
                    user_id=None,  # System operation
                    previous_state=previous_state,
                    new_state=updated_trip,
                    details={
                        'reason': 'automatic_document_reconciliation',
                        'repaired_documents': result['repaired_docs']
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log audit entry for trip {trip_id}: {str(e)}")
            
            result['status'] = 'repaired'
        elif result['errors']:
            result['status'] = 'repair_failed'
        else:
            result['status'] = 'success'
    
    except Exception as e:
        result['status'] = 'error'
        result['errors'].append(str(e))
        logger.error(f"Unexpected error reconciling trip {trip_id}: {str(e)}", exc_info=True)
    
    return result


def _publish_error_to_sns(
    sns_topic_arn: str,
    trip_id: str,
    missing_docs: List[str],
    error_message: str,
    reconciliation_results: Dict[str, Any]
) -> None:
    """
    Publish error notification to SNS topic.
    
    Args:
        sns_topic_arn: SNS topic ARN
        trip_id: Trip ID
        missing_docs: List of missing documents
        error_message: Error description
        reconciliation_results: Full reconciliation attempt details
    """
    try:
        message = {
            'trip_id': trip_id,
            'missing_documents': missing_docs,
            'error': error_message,
            'reconciliation_results': reconciliation_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Create SNS client dynamically with region
        sns = boto3.client('sns', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        sns.publish(
            TopicArn=sns_topic_arn,
            Subject=f'Trip Document Reconciliation Failed - Trip {trip_id}',
            Message=json.dumps(message, indent=2, default=str)
        )
        
        logger.info(f"Published error notification to SNS for trip {trip_id}")
    
    except ClientError as e:
        logger.error(f"Failed to publish to SNS: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error publishing to SNS: {str(e)}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for trip document reconciliation.
    
    Args:
        event: Lambda event from EventBridge
        context: Lambda context
        
    Returns:
        Dict with reconciliation summary
    """
    logger.info("Starting trip document reconciliation")
    
    summary = {
        'status': 'success',
        'processed_trips': 0,
        'repaired_trips': 0,
        'failed_repairs': 0,
        'errors': []
    }
    
    connection = None
    
    try:
        # Initialize connections
        connection = MongoDBConnection()
        s3_uploader = S3Uploader()
        audit_service = AuditService(connection)
        
        # Get in_transit status ID
        in_transit_status_id = _get_trip_status_id(connection, 'in_transit')
        if not in_transit_status_id:
            raise ReconciliationError("Could not find 'in_transit' trip status in database")
        
        # Find trips with missing documents
        trips = _find_trips_with_missing_documents(connection, in_transit_status_id)
        
        logger.info(f"Starting reconciliation of {len(trips)} trips")
        
        # Process each trip
        sns_topic_arn = os.getenv('TRIP_RECONCILIATION_ERROR_TOPIC_ARN')
        
        for trip in trips:
            summary['processed_trips'] += 1
            
            result = _reconcile_trip(trip, connection, s3_uploader, audit_service)
            
            logger.info(f"Trip {result['trip_id']} reconciliation: {result['status']}")
            
            if result['status'] == 'repaired':
                summary['repaired_trips'] += 1
            elif result['status'] in ['repair_failed', 'error']:
                summary['failed_repairs'] += 1
                
                # Publish to SNS if configured
                if sns_topic_arn:
                    _publish_error_to_sns(
                        sns_topic_arn,
                        result['trip_id'],
                        result['missing_docs'],
                        f"Repair status: {result['status']}. Errors: {'; '.join(result['errors'])}",
                        result
                    )
        
        logger.info(f"Reconciliation complete: {summary['repaired_trips']} repaired, {summary['failed_repairs']} failed")
    
    except ServerSelectionTimeoutError as e:
        summary['status'] = 'error'
        summary['errors'].append(f"MongoDB connection failed: {str(e)}")
        logger.error(f"MongoDB connection error: {str(e)}")
    
    except ReconciliationError as e:
        summary['status'] = 'error'
        summary['errors'].append(str(e))
        logger.error(f"Reconciliation error: {str(e)}")
    
    except Exception as e:
        summary['status'] = 'error'
        summary['errors'].append(f"Unexpected error: {str(e)}")
        logger.error(f"Unexpected error during reconciliation: {str(e)}", exc_info=True)
    
    finally:
        # Clean up
        if connection:
            try:
                connection.close()
            except:
                pass
    
    logger.info(f"Reconciliation summary: {summary}")
    return summary
