"""
EventBridge Keep-Warm Lambda Handler

This Lambda function is triggered by EventBridge every 5 minutes to:
1. Call the /health/deep endpoint to verify the application is truly functional
2. Parse and analyze the response
3. Alert if any critical dependencies are down
4. Keep the Lambda container warm (prevent cold starts)

Usage:
- Deploy as a Lambda function
- Trigger with EventBridge rule: "rate(5 minutes)"
- Set SNS topic ARN for alerts via environment variable

Environment Variables:
    API_BASE_URL: Base URL of the Heavy Freight API (e.g., https://api.example.com)
    ALERT_SNS_TOPIC: SNS topic ARN for failure alerts
    ALERT_EMAIL: Email to receive alerts (used if SNS_TOPIC not available)
"""

import json
import os
import urllib3
import boto3
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize HTTP client
http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2.0, read=10.0))

# AWS clients
sns_client = boto3.client('sns')
cloudwatch_client = boto3.client('cloudwatch')


def lambda_handler(event, context) -> Dict[str, Any]:
    """
    EventBridge keep-warm handler.
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Dict with statusCode and response body
    """
    
    api_base_url = os.getenv('API_BASE_URL', 'https://api.example.com')
    health_endpoint = f"{api_base_url}/health/deep"
    
    print(f"[{datetime.utcnow().isoformat()}] Starting keep-warm health check")
    print(f"Health endpoint: {health_endpoint}")
    
    try:
        # Call the deep health check endpoint
        response = http.request('GET', health_endpoint, timeout=10.0)
        data = json.loads(response.data.decode('utf-8'))
        
        status = data.get('status', 'unknown')
        checks = data.get('checks', {})
        duration_ms = data.get('duration_ms', -1)
        
        print(f"Health check response: status={status}, duration={duration_ms}ms")
        print(f"Checks: {json.dumps(checks, indent=2)}")
        
        # Publish metrics to CloudWatch
        _publish_metrics(status, checks, duration_ms)
        
        # Analyze the response
        if status == 'healthy':
            print("✅ All systems operational")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'System is healthy',
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        elif status == 'degraded':
            print("⚠️  System degraded but operational")
            # Log for investigation but don't alert (non-prod or optional services)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'System degraded but operational',
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        else:  # unhealthy (503) or unknown
            print(f"❌ Health check failed with status: {status}")
            
            # Send alert
            failed_checks = {k: v for k, v in checks.items() if not v.get('healthy', False)}
            _send_alert('Health Check Failed', response_data=data, failed_checks=failed_checks)
            
            return {
                'statusCode': 503,
                'body': json.dumps({
                    'message': 'System unhealthy',
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat(),
                    'failed_checks': failed_checks
                })
            }
    
    except urllib3.exceptions.TimeoutError:
        print("❌ Health check timed out after 10 seconds")
        _send_alert('Health Check Timeout', reason='Request timed out after 10 seconds')
        return {
            'statusCode': 504,
            'body': json.dumps({
                'message': 'Health check timeout',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except urllib3.exceptions.HTTPError as e:
        print(f"❌ HTTP error during health check: {str(e)}")
        _send_alert('Health Check HTTP Error', reason=str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'HTTP error: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse health check response: {str(e)}")
        _send_alert('Health Check Parse Error', reason='Invalid JSON response')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Invalid response format',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        _send_alert('Health Check Error', reason=str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Error: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def _publish_metrics(status: str, checks: Dict[str, Any], duration_ms: float) -> None:
    """
    Publish health check metrics to CloudWatch.
    
    Args:
        status: Overall health status (healthy, degraded, unhealthy)
        checks: Dictionary of individual check results
        duration_ms: Total duration of health check in milliseconds
    """
    try:
        namespace = 'HeavyFreight/HealthCheck'
        
        # Map status to numeric value for metrics
        status_value = {
            'healthy': 1,
            'degraded': 0.5,
            'unhealthy': 0
        }.get(status, -1)
        
        metrics_data = [
            {
                'MetricName': 'HealthStatus',
                'Value': status_value,
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'HealthCheckDuration',
                'Value': duration_ms,
                'Unit': 'Milliseconds',
                'Timestamp': datetime.utcnow()
            }
        ]
        
        # Add metric for each dependency check
        for check_name, check_data in checks.items():
            if isinstance(check_data, dict) and 'healthy' in check_data:
                metrics_data.append({
                    'MetricName': f'{check_name.replace("_", "").title()}Status',
                    'Value': 1 if check_data['healthy'] else 0,
                    'Unit': 'None',
                    'Timestamp': datetime.utcnow()
                })
        
        # Publish to CloudWatch
        cloudwatch_client.put_metric_data(
            Namespace=namespace,
            MetricData=metrics_data
        )
        
        print(f"Published {len(metrics_data)} metrics to CloudWatch")
    
    except Exception as e:
        print(f"Warning: Failed to publish metrics: {str(e)}")


def _send_alert(title: str, reason: Optional[str] = None, 
                response_data: Optional[Dict] = None, 
                failed_checks: Optional[Dict] = None) -> None:
    """
    Send alert via SNS or simple notification.
    
    Args:
        title: Alert title
        reason: Brief reason for alert
        response_data: Full health check response
        failed_checks: Dictionary of failed checks
    """
    try:
        sns_topic = os.getenv('ALERT_SNS_TOPIC')
        if not sns_topic:
            print(f"Warning: ALERT_SNS_TOPIC not set, alert not sent")
            return
        
        # Build alert message
        message = f"""
🚨 Heavy Freight API Alert

**{title}**

Timestamp: {datetime.utcnow().isoformat()}

Environment: {os.getenv('FLASK_ENV', 'production')}
API Endpoint: {os.getenv('API_BASE_URL', 'unknown')}
"""
        
        if reason:
            message += f"\nReason: {reason}\n"
        
        if failed_checks:
            message += "\nFailed Checks:\n"
            for check_name, check_data in failed_checks.items():
                error = check_data.get('error', 'Unknown error')
                message += f"  - {check_name}: {error}\n"
        
        if response_data and 'checks' in response_data:
            message += "\nFull Details:\n"
            message += json.dumps(response_data, indent=2)
        
        # Send via SNS
        sns_client.publish(
            TopicArn=sns_topic,
            Subject=f'[ALERT] {title}',
            Message=message
        )
        
        print(f"Alert sent to SNS topic: {sns_topic}")
    
    except Exception as e:
        print(f"Error sending alert: {str(e)}")


# Lambda Insights Extension Configuration (optional, requires Layer)
# Add the Lambda Insights layer to get enhanced monitoring:
# arn:aws:lambda:region:580254703988:layer:LambdaInsightsExtension:version
