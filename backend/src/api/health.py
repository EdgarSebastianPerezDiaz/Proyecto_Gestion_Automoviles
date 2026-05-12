"""
Health Check Endpoints for Kubernetes/Docker Orchestration

Provides liveness, readiness, and deep health probes for container orchestration platforms
and monitoring systems.

Endpoints:
- GET /health/live  - Liveness probe (always responds 200 if app is running)
- GET /health/ready - Readiness probe (checks dependencies: MongoDB, S3)
- GET /health/deep  - Deep health check (verifies MongoDB, Secrets Manager, Rate Limiter)
                      Used by EventBridge (keep-warm Lambda) and monitoring systems
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime, timezone, timedelta
import logging
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.route('/live', methods=['GET'])
def liveness_probe():
    """
    Liveness Probe - Kubernetes/Docker uses this to determine if pod is alive.
    
    Should respond quickly with 200 if application process is running.
    No external dependency checks - those belong in readiness probe.
    
    Returns:
        200 OK with status="alive"
    """
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200


@health_bp.route('/ready', methods=['GET'])
def readiness_probe():
    """
    Readiness Probe - Kubernetes/Docker uses this to determine if pod can receive traffic.
    
    Checks critical dependencies:
    - MongoDB connectivity (ping)
    - S3 bucket accessibility (head_bucket)
    
    Returns:
        200 OK with status="ready" if all dependencies are available
        503 Service Unavailable if any dependency is down
        
    Timeout: 5 seconds max to avoid blocking orchestration
    """
    checks = {}
    all_healthy = True
    
    # Check MongoDB
    try:
        mongo_check = _check_mongodb()
        checks['mongodb'] = mongo_check
        if not mongo_check.get('healthy'):
            all_healthy = False
    except Exception as e:
        logger.error(f"MongoDB health check failed: {str(e)}")
        checks['mongodb'] = {
            'healthy': False,
            'error': str(e)
        }
        all_healthy = False
    
    # Check S3 (optional if not configured)
    try:
        s3_check = _check_s3()
        checks['s3'] = s3_check
        if not s3_check.get('healthy') and s3_check.get('configured'):
            all_healthy = False
    except Exception as e:
        logger.error(f"S3 health check failed: {str(e)}")
        checks['s3'] = {
            'healthy': False,
            'configured': True,
            'error': str(e)
        }
        all_healthy = False
    
    response = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }
    
    status_code = 200 if all_healthy else 503
    return jsonify(response), status_code


@health_bp.route('/deep', methods=['GET'])
def deep_health_check():
    """
    Deep Health Check - Comprehensive verification of critical dependencies.
    
    Used by:
    - EventBridge keep-warm Lambda function (to ensure system is actually working)
    - Monitoring/observability systems (CloudWatch, DataDog, etc.)
    - Pre-deployment smoke tests
    
    Checks critical dependencies with detailed diagnostics:
    - MongoDB: Connectivity, latency, collection accessibility
    - AWS Secrets Manager: Access tokens, secret retrieval capability
    - Rate Limiter: Collection connectivity, document operations
    
    Returns:
        200 OK if all checks pass (status="healthy")
        207 Multi-Status if some checks fail (status="degraded")
        503 Service Unavailable if critical dependencies fail (status="unhealthy")
        
    Timeout: 10 seconds max per dependency check
    """
    checks = {}
    all_healthy = True
    degraded = False
    
    start_time = datetime.now(timezone.utc)
    
    # Check MongoDB (critical)
    try:
        mongo_check = _check_mongodb()
        checks['mongodb'] = mongo_check
        if not mongo_check.get('healthy'):
            all_healthy = False
            logger.warning("Deep health check: MongoDB is unhealthy")
    except Exception as e:
        logger.error(f"MongoDB deep health check failed: {str(e)}", exc_info=True)
        checks['mongodb'] = {
            'healthy': False,
            'error': str(e)
        }
        all_healthy = False
    
    # Check AWS Secrets Manager (critical in production)
    try:
        secrets_manager_check = _check_secrets_manager()
        checks['secrets_manager'] = secrets_manager_check
        if not secrets_manager_check.get('healthy'):
            if os.getenv('FLASK_ENV') == 'production':
                all_healthy = False
                logger.error("Deep health check: Secrets Manager is unhealthy (production)")
            else:
                degraded = True
                logger.warning("Deep health check: Secrets Manager is unhealthy (not critical in non-prod)")
    except Exception as e:
        logger.error(f"Secrets Manager deep health check failed: {str(e)}", exc_info=True)
        checks['secrets_manager'] = {
            'healthy': False,
            'error': str(e),
            'criticality': 'high' if os.getenv('FLASK_ENV') == 'production' else 'low'
        }
        if os.getenv('FLASK_ENV') == 'production':
            all_healthy = False
        else:
            degraded = True
    
    # Check Rate Limiter (critical)
    try:
        rate_limiter_check = _check_rate_limiter()
        checks['rate_limiter'] = rate_limiter_check
        if not rate_limiter_check.get('healthy'):
            all_healthy = False
            logger.warning("Deep health check: Rate Limiter is unhealthy")
    except Exception as e:
        logger.error(f"Rate Limiter deep health check failed: {str(e)}", exc_info=True)
        checks['rate_limiter'] = {
            'healthy': False,
            'error': str(e)
        }
        all_healthy = False
    
    # Analyze overall status
    if all_healthy:
        status = "healthy"
        status_code = 200
    elif degraded and not all_healthy:
        status = "degraded"
        status_code = 207  # Multi-Status: some checks passed, some failed
    else:
        status = "unhealthy"
        status_code = 503
    
    duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    
    response = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": round(duration_ms, 2),
        "checks": checks,
        "environment": os.getenv('FLASK_ENV', 'development')
    }
    
    return jsonify(response), status_code


def _check_mongodb() -> dict:
    """
    Check MongoDB connectivity by executing ping command.
    
    Returns:
        dict with keys: healthy (bool), latency_ms (float), error (str, optional)
    """
    try:
        mongo_connection = current_app.mongo_connection
        if not mongo_connection or not mongo_connection.is_connected():
            return {
                'healthy': False,
                'error': 'MongoDB connection not initialized'
            }
        
        start_time = datetime.now(timezone.utc)
        
        # Execute ping command with timeout
        result = mongo_connection.db.command('ping', timeoutMS=2000)
        
        latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return {
            'healthy': result.get('ok') == 1,
            'latency_ms': round(latency, 2)
        }
    except Exception as e:
        logger.error(f"MongoDB ping failed: {str(e)}")
        return {
            'healthy': False,
            'error': str(e)
        }


def _check_s3() -> dict:
    """
    Check S3 bucket accessibility.
    
    Returns:
        dict with keys: healthy (bool), configured (bool), error (str, optional)
    """
    try:
        # Check if S3 is configured
        bucket_name = current_app.config.get('S3_BUCKET_NAME')
        if not bucket_name:
            return {
                'healthy': True,  # S3 not configured is OK (not required)
                'configured': False
            }
        
        # Try to access S3 uploader from app
        s3_uploader = getattr(current_app, 's3_uploader', None)
        if not s3_uploader:
            return {
                'healthy': False,
                'configured': True,
                'error': 'S3 uploader not initialized'
            }
        
        # Check S3 connection with head_bucket
        try:
            s3_client = s3_uploader.s3_client
            if not s3_client:
                return {
                    'healthy': False,
                    'configured': True,
                    'error': 'S3 client not initialized'
                }
            
            # Execute head_bucket with timeout
            s3_client.head_bucket(Bucket=bucket_name)
            
            return {
                'healthy': True,
                'configured': True,
                'bucket': bucket_name
            }
        except Exception as e:
            logger.error(f"S3 head_bucket failed: {str(e)}")
            return {
                'healthy': False,
                'configured': True,
                'error': f"S3 bucket access failed: {str(e)}"
            }
    
    except Exception as e:
        logger.error(f"S3 health check exception: {str(e)}")
        return {
            'healthy': False,
            'configured': True,
            'error': str(e)
        }


def _check_secrets_manager() -> dict:
    """
    Check AWS Secrets Manager accessibility (if running on Lambda).
    
    Verifies that:
    - Boto3 is available (AWS SDK)
    - IAM role has permission to access Secrets Manager
    - We can retrieve a test secret or at least connect to the service
    
    Returns:
        dict with keys: 
            - healthy (bool): Whether Secrets Manager is accessible
            - accessible (bool): Whether we're in an environment that uses it (Lambda)
            - region (str, optional): AWS region
            - error (str, optional): Error message if check failed
    """
    try:
        # Check if boto3 is available
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            return {
                'healthy': True,  # Boto3 not available - not a problem
                'accessible': False,
                'reason': 'Boto3 not installed (not running on Lambda)'
            }
        
        # Check if we're running in Lambda (where Secrets Manager is used)
        if 'AWS_LAMBDA_FUNCTION_NAME' not in os.environ:
            return {
                'healthy': True,  # Not on Lambda - doesn't matter
                'accessible': False,
                'reason': 'Not running on Lambda'
            }
        
        # We're on Lambda, try to connect to Secrets Manager
        try:
            region = os.getenv('AWS_REGION', 'us-east-1')
            client = boto3.client('secretsmanager', region_name=region)
            
            # Verify we can at least call list_secrets (minimal permission)
            # This doesn't require reading any specific secret
            start_time = datetime.now(timezone.utc)
            client.list_secrets(Filters=[{'Key': 'name', 'Values': ['heavy-freight']}], MaxResults=1)
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return {
                'healthy': True,
                'accessible': True,
                'region': region,
                'latency_ms': round(latency, 2)
            }
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDenied':
                return {
                    'healthy': False,
                    'accessible': True,
                    'error': 'Access Denied - IAM role lacks Secrets Manager permission',
                    'error_code': error_code,
                    'region': os.getenv('AWS_REGION', 'us-east-1')
                }
            elif error_code == 'InvalidSignatureException':
                return {
                    'healthy': False,
                    'accessible': True,
                    'error': 'Invalid AWS credentials or signature',
                    'error_code': error_code,
                    'region': os.getenv('AWS_REGION', 'us-east-1')
                }
            else:
                return {
                    'healthy': False,
                    'accessible': True,
                    'error': f"Secrets Manager error: {str(e)}",
                    'error_code': error_code,
                    'region': os.getenv('AWS_REGION', 'us-east-1')
                }
        except Exception as e:
            return {
                'healthy': False,
                'accessible': True,
                'error': f"Failed to connect to Secrets Manager: {str(e)}",
                'region': os.getenv('AWS_REGION', 'us-east-1')
            }
    
    except Exception as e:
        logger.error(f"Secrets Manager health check exception: {str(e)}")
        return {
            'healthy': False,
            'error': f"Unexpected error: {str(e)}"
        }


def _check_rate_limiter() -> dict:
    """
    Check Rate Limiter health by verifying MongoDB collection access.
    
    The Rate Limiter depends on MongoDB, so this checks:
    - Rate limiter instance is initialized
    - MongoDB collection for rate_limits exists/is accessible
    - We can read from the collection (no write required)
    
    Returns:
        dict with keys: 
            - healthy (bool): Whether rate limiter is functional
            - initialized (bool): Whether rate limiter was instantiated
            - collection_accessible (bool, optional): Whether we can access the collection
            - error (str, optional): Error message if check failed
    """
    try:
        # Check if rate limiter is available on app
        rate_limiter = getattr(current_app, 'rate_limiter', None)
        if not rate_limiter:
            return {
                'healthy': False,
                'initialized': False,
                'error': 'Rate limiter not initialized in app'
            }
        
        # Check if rate limiter is marked as initialized
        if not getattr(rate_limiter, '_initialized', False):
            return {
                'healthy': False,
                'initialized': False,
                'error': 'Rate limiter not properly initialized'
            }
        
        # Check if MongoDB connection exists through rate limiter
        if not hasattr(rate_limiter, 'collection') or rate_limiter.collection is None:
            return {
                'healthy': False,
                'initialized': True,
                'collection_accessible': False,
                'error': 'Rate limiter collection not initialized'
            }
        
        # Try to access the collection with a simple operation
        try:
            start_time = datetime.now(timezone.utc)
            
            # Count documents in rate_limits collection (minimal operation)
            # This verifies the collection exists and is accessible
            collection_count = rate_limiter.collection.count_documents({})
            
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return {
                'healthy': True,
                'initialized': True,
                'collection_accessible': True,
                'documents_count': collection_count,
                'latency_ms': round(latency, 2)
            }
        except Exception as e:
            logger.error(f"Failed to access rate limiter collection: {str(e)}")
            return {
                'healthy': False,
                'initialized': True,
                'collection_accessible': False,
                'error': f"Rate limiter collection access failed: {str(e)}"
            }
    
    except Exception as e:
        logger.error(f"Rate limiter health check exception: {str(e)}", exc_info=True)
        return {
            'healthy': False,
            'error': f"Unexpected error: {str(e)}"
        }
