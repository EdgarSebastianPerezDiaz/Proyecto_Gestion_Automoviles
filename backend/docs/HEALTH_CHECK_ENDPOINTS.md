# Health Check Endpoints Documentation

## Overview

The Heavy Freight Platform provides three health check endpoints designed for different use cases:

| Endpoint | Purpose | Probe Type | SLA | Used By |
|----------|---------|-----------|-----|---------|
| `/health/live` | Simple liveness probe | N/A | Instant | Pod schedulers, load balancers |
| `/health/ready` | Readiness probe (basic deps) | K8s Readiness | <1s | Kubernetes, orchestrators |
| `/health/deep` | Comprehensive dependency check | Custom | <5s | EventBridge, monitoring systems |

---

## 1. Liveness Probe: `/health/live`

**Purpose:** Determines if the application process is running.

**When to use:** 
- Kubernetes liveness probes
- Container orchestration platforms
- Basic load balancer checks

**Response:**
```bash
curl -s http://localhost:5000/health/live
```

**Success (200 OK):**
```json
{
  "status": "alive",
  "timestamp": "2026-04-04T10:30:45.123456+00:00"
}
```

**Characteristics:**
- ✅ Always responds 200 if app is running
- ✅ ~0ms response time (no external calls)
- ✅ Used to restart unhealthy containers

---

## 2. Readiness Probe: `/health/ready`

**Purpose:** Verifies the application can serve traffic (dependencies are accessible).

**When to use:**
- Kubernetes readiness probes
- Load balancer target group checks
- Pre-deployment health verification

**Response:**
```bash
curl -s http://localhost:5000/health/ready | jq
```

**Success (200 OK):**
```json
{
  "status": "ready",
  "timestamp": "2026-04-04T10:30:45.123456+00:00",
  "checks": {
    "mongodb": {
      "healthy": true,
      "latency_ms": 15.42
    },
    "s3": {
      "healthy": true,
      "configured": true,
      "bucket": "heavy-freight-prod"
    }
  }
}
```

**Not Ready (503 Service Unavailable):**
```json
{
  "status": "not_ready",
  "timestamp": "2026-04-04T10:30:45.123456+00:00",
  "checks": {
    "mongodb": {
      "healthy": false,
      "error": "Connection refused"
    },
    "s3": {
      "healthy": true,
      "configured": false
    }
  }
}
```

**Dependencies Checked:**
- MongoDB: Ping command with 2s timeout
- S3: head_bucket() call (optional if not configured)

---

## 3. Deep Health Check: `/health/deep` ⭐ NEW

**Purpose:** Comprehensive verification of all critical dependencies with detailed diagnostics.

**When to use:**
- **EventBridge keep-warm Lambda** (main use case)
- CloudWatch synthetic monitoring
- Pre-deployment smoke tests
- Monitoring systems (DataDog, New Relic, etc.)
- Incident investigation

**Response:**
```bash
curl -s http://localhost:5000/health/deep | jq
```

### Success Scenario (200 OK - Healthy)

```json
{
  "status": "healthy",
  "timestamp": "2026-04-04T10:30:45.123456+00:00",
  "duration_ms": 245.68,
  "environment": "production",
  "checks": {
    "mongodb": {
      "healthy": true,
      "latency_ms": 42.15
    },
    "secrets_manager": {
      "healthy": true,
      "accessible": true,
      "region": "us-east-1",
      "latency_ms": 125.30
    },
    "rate_limiter": {
      "healthy": true,
      "initialized": true,
      "collection_accessible": true,
      "documents_count": 3,
      "latency_ms": 8.92
    }
  }
}
```

### Degraded Scenario (207 Multi-Status)

```json
{
  "status": "degraded",
  "timestamp": "2026-04-04T10:30:45.123456+00:00",
  "duration_ms": 305.2,
  "environment": "development",
  "checks": {
    "mongodb": {
      "healthy": true,
      "latency_ms": 12.5
    },
    "secrets_manager": {
      "healthy": false,
      "accessible": false,
      "reason": "Not running on Lambda"
    },
    "rate_limiter": {
      "healthy": true,
      "initialized": true,
      "collection_accessible": true,
      "documents_count": 0,
      "latency_ms": 5.2
    }
  }
}
```

### Unhealthy Scenario (503 Service Unavailable)

```json
{
  "status": "unhealthy",
  "timestamp": "2026-04-04T10:30:45.123456+00:00",
  "duration_ms": 1250.5,
  "environment": "production",
  "checks": {
    "mongodb": {
      "healthy": false,
      "error": "Connection timeout after 2000ms"
    },
    "secrets_manager": {
      "healthy": false,
      "accessible": true,
      "error": "Access Denied - IAM role lacks Secrets Manager permission",
      "error_code": "AccessDenied",
      "region": "us-east-1",
      "criticality": "high"
    },
    "rate_limiter": {
      "healthy": false,
      "initialized": true,
      "collection_accessible": false,
      "error": "Rate limiter collection access failed: Connection refused"
    }
  }
}
```

### Dependencies Checked

#### 1. MongoDB (Critical)
```python
{
  "healthy": bool,                # Can we connect and ping?
  "latency_ms": float,            # Response time in milliseconds
  "error": str  # (optional) Error message
}
```
- **Check:** MongoDB ping command with 2s timeout
- **Timeout:** 2 seconds
- **Criticality:** CRITICAL - App cannot function without it

#### 2. AWS Secrets Manager (Critical in Production)
```python
{
  "healthy": bool,                # Can we access Secrets Manager?
  "accessible": bool,             # Are we in an environment that uses it?
  "reason": str,  # (optional) Why not accessible (e.g., "Not running on Lambda")
  "region": str,  # (optional) AWS region
  "latency_ms": float,            # Response time in milliseconds
  "error_code": str,  # (optional) AWS error code (e.g., AccessDenied)
  "criticality": str  # (optional) "high"/"low" - impact if failing
}
```
- **Check:** boto3 list_secrets() call (minimal IAM permission)
- **Timeout:** 5 seconds
- **Criticality:** HIGH in production, LOW in development
- **Scenarios:**
  - Local environment: `"accessible": false` (not on Lambda)
  - Lambda without boto3: `"accessible": false` (missing SDK)
  - Lambda with no IAM: `"error_code": "AccessDenied"`
  - Lambda with invalid credentials: `"error_code": "InvalidSignatureException"`

#### 3. Rate Limiter (Critical)
```python
{
  "healthy": bool,                # Is rate limiter working?
  "initialized": bool,            # Was it instantiated?
  "collection_accessible": bool,  # Can we access MongoDB collection?
  "documents_count": int,         # (optional) Number of rate limit entries
  "latency_ms": float,            # Response time in milliseconds
  "error": str  # (optional) Error message
}
```
- **Check:** count_documents() on `rate_limits` MongoDB collection
- **Timeout:** Part of MongoDB 2s timeout
- **Criticality:** CRITICAL - API requires rate limiting

---

## Integration with EventBridge Keep-Warm Lambda

### Scenario
EventBridge triggers a Lambda function every 5 minutes to call `/health/deep` and ensure the application is truly functional (not just responding to requests).

### Example Lambda Handler

```python
import json
import boto3
import urllib3

http = urllib3.PoolManager()

def lambda_handler(event, context):
    """
    Keep-warm endpoint health check.
    Called by EventBridge every 5 minutes.
    """
    
    api_url = os.getenv('API_BASE_URL', 'https://api.heavy-freight.com')
    health_endpoint = f"{api_url}/health/deep"
    
    try:
        # Call the deep health check
        response = http.request('GET', health_endpoint, timeout=10.0)
        data = json.loads(response.data.decode())
        
        status = data.get('status')
        checks = data.get('checks', {})
        
        # Determine if we should alert
        if status == 'healthy':
            print(f"✅ Health check passed: {status}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'System is healthy'})
            }
        
        elif status == 'degraded':
            print(f"⚠️  Health check degraded: {status}")
            # Log for investigation but don't alert
            # (optional services may be unavailable in dev environment)
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'System degraded but operational'})
            }
        
        else:  # unhealthy (503)
            print(f"❌ Health check failed: {status}")
            print(f"Checks: {json.dumps(checks, indent=2)}")
            
            # Send alert to SNS
            sns_client = boto3.client('sns')
            sns_client.publish(
                TopicArn=os.getenv('ALERT_SNS_TOPIC'),
                Subject='🚨 Heavy Freight API Health Check Failed',
                Message=f"Status: {status}\n\n{json.dumps(checks, indent=2)}"
            )
            
            return {
                'statusCode': 503,
                'body': json.dumps({'message': 'System unhealthy'})
            }
    
    except urllib3.exceptions.TimeoutError:
        print("❌ Health check timed out")
        # Send alert
        return {'statusCode': 504, 'body': json.dumps({'message': 'Timeout'})}
    
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        # Send alert
        return {'statusCode': 500, 'body': json.dumps({'message': str(e)})}
```

### EventBridge Rule Configuration

```yaml
# serverless.yml
events:
  - http:
      path: health/deep
      method: get
      cors: true

# Or in AWS CloudFormation/CDK:
Rule:
  Name: KeepWarmHealthCheck
  ScheduleExpression: "rate(5 minutes)"
  State: ENABLED
  Targets:
    - Arn: arn:aws:lambda:us-east-1:ACCOUNT:function:keep-warm-checker
      RoleArn: arn:aws:iam::ACCOUNT:role/EventBridgeRole
```

---

## Monitoring Integration Examples

### CloudWatch Synthetic Monitoring

```python
# CloudWatch Canary
import urllib3

http = urllib3.PoolManager()

def handler():
    response = http.request(
        'GET', 
        'https://your-api.execute-api.us-east-1.amazonaws.com/health/deep',
        timeout=10.0
    )
    
    assert response.status == 200, f"Expected 200, got {response.status}"
    data = json.loads(response.data)
    assert data['status'] == 'healthy', f"Expected healthy, got {data['status']}"
    
    # Check specific dependencies
    checks = data.get('checks', {})
    assert checks['mongodb']['healthy'], "MongoDB is down"
    assert checks['rate_limiter']['healthy'], "Rate limiter is down"
```

### DataDog Custom Health Check

```yaml
# datadog-agent/conf.d/http_check.d/config.yaml
init_config:

instances:
  - name: Heavy Freight API Deep Health
    url: "https://your-api.execute-api.us-east-1.amazonaws.com/health/deep"
    method: GET
    timeout: 10
    ssl_verify: true
    http_response_status_code: 200
    
    # Alert on specific conditions
    tags:
      - service:api
      - env:production
      - type:health-check
```

---

## HTTP Status Code Reference

| Status | Meaning | When | Action |
|--------|---------|------|--------|
| **200 OK** | All systems operational | All checks pass | Continue normal operation |
| **207 Multi-Status** | Partial degradation | Some checks fail (non-critical) | Log for investigation, continue operation |
| **503 Service Unavailable** | Critical failure | One or more critical checks fail | Alert, escalate incident |

---

## Response Time Targets

```
/health/live    → <10ms   (no external calls)
/health/ready   → <1s     (2s MongoDB timeout max)
/health/deep    → <5s     (2s MongoDB + 5s Secrets Manager timeout)
```

---

## Troubleshooting

### MongoDB Connection Fails
```json
{
  "status": "unhealthy",
  "checks": {
    "mongodb": {
      "healthy": false,
      "error": "Connection refused"
    }
  }
}
```
**Action:** 
- Check MongoDB service is running: `mongosh admin --eval "db.runCommand('ping')"`
- Verify MONGO_URI environment variable
- Check network connectivity and firewall rules

### Secrets Manager Access Denied
```json
{
  "checks": {
    "secrets_manager": {
      "healthy": false,
      "error": "Access Denied - IAM role lacks Secrets Manager permission",
      "error_code": "AccessDenied"
    }
  }
}
```
**Action:**
- Add IAM policy to Lambda execution role:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:*:*:secret:heavy-freight/*"
    }
  ]
}
```

### Rate Limiter Collection Not Found
```json
{
  "checks": {
    "rate_limiter": {
      "healthy": false,
      "error": "Rate limiter collection access failed: namespace does not exist"
    }
  }
}
```
**Action:**
- Ensure MongoDB initialization has completed
- Check rate_limits collection exists: `db.rate_limits.stats()`
- Restart application to trigger rate limiter initialization

---

## Best Practices

1. **Monitoring:** Set up alerts for `/health/deep` returning anything other than `200`
2. **Keep-Warm:** Use EventBridge to call `/health/deep` every 5 minutes
3. **Logging:** Monitor endpoint logs for patterns in failures
4. **Thresholds:** Track latency_ms to detect performance degradation
5. **Development:** Use `/health/live` during development (simplest check)
6. **Production:** Use `/health/deep` with EventBridge for comprehensive monitoring
