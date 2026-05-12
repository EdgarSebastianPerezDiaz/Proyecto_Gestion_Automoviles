"""
Keep-warm Lambda function - prevents cold starts by invoking the API regularly.

This Lambda function is triggered by CloudWatch Events (5 minutes schedule).
It performs a simple HTTP request to the API health endpoint to keep the
Lambda container warm and ready to handle requests.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Keep-warm Lambda handler.
    
    Invokes the health check endpoint to keep the Lambda warm.
    
    Args:
        event: CloudWatch Events schedule event
        context: Lambda context object
        
    Returns:
        Response dict with statusCode and body
    """
    try:
        api_url = os.getenv('API_URL', 'http://localhost:5000')
        health_endpoint = f"{api_url}/health"
        
        # Make HTTP request to health endpoint
        req = urllib.request.Request(health_endpoint)
        req.add_header('User-Agent', 'KeepWarmLambda')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.status
            response_text = response.read().decode('utf-8')
            
            if status_code == 200:
                print(f"✓ Keep-warm request successful. API is warm.")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Lambda keep-warm check completed',
                        'status': 'success',
                        'endpoint': health_endpoint
                    })
                }
            else:
                print(f"✗ Keep-warm request failed with status {status_code}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'message': f'Health check returned {status_code}',
                        'status': 'warning'
                    })
                }
    
    except urllib.error.URLError as e:
        print(f"✗ Network error during keep-warm: {str(e)}")
        return {
            'statusCode': 503,
            'body': json.dumps({
                'message': f'Network error: {str(e)}',
                'status': 'error'
            })
        }
    
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP error during keep-warm: {e.code}")
        return {
            'statusCode': 502,
            'body': json.dumps({
                'message': f'HTTP error {e.code}',
                'status': 'error'
            })
        }
    
    except Exception as e:
        print(f"✗ Unexpected error during keep-warm: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Unexpected error: {str(e)}',
                'status': 'error'
            })
        }
