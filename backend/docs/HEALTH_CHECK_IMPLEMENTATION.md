# /health/deep Endpoint Implementation Summary

## What Was Created ✅

### 1. New Endpoint: `/health/deep`
**Location:** `src/api/health.py`

Comprehensive health check endpoint that verifies all critical dependencies:
- **MongoDB**: Connectivity, latency, ping command
- **AWS Secrets Manager**: Access permissions, service availability (Lambda only)
- **Rate Limiter**: Collection accessibility, document operations

**HTTP Status Codes:**
- `200 OK` - All systems healthy
- `207 Multi-Status` - Partial degradation (non-critical services down)
- `503 Service Unavailable` - Critical dependencies down

### 2. Documentation
**Location:** `docs/HEALTH_CHECK_ENDPOINTS.md`

Complete guide covering:
- Overview of all three health check endpoints
- Usage examples with curl
- Response format examples (success, degraded, unhealthy)
- Monitoring integration patterns (CloudWatch, DataDog)
- Troubleshooting guide
- Best practices

### 3. EventBridge Keep-Warm Lambda
**Location:** `scripts/keep_warm_lambda_health_check.py`

Lambda function that:
- Calls `/health/deep` every 5 minutes (via EventBridge)
- Analyzes response and sends alerts on failure
- Publishes metrics to CloudWatch
- Keeps Lambda container warm (prevents cold starts)
- Includes error handling and logging

### 4. Test Suite
**Location:** `tests/test_health_checks.py`

Comprehensive tests for `/health/deep`:
- ✅ Healthy status (200 OK)
- ✅ Degraded status (207 Multi-Status)
- ✅ Unhealthy status (503 Service Unavailable)
- ✅ Individual dependency checks
- ✅ Metrics and duration tracking
- ✅ Error handling
- ✅ No authentication required
- ✅ Response structure validation

### 5. Serverless Configuration Example
**Location:** `serverless-health-check-config.yml`

Example configuration for:
- Keep-warm Lambda function
- EventBridge scheduling
- SNS topic for alerts
- CloudWatch alarms and dashboard
- IAM permissions
- Environment variables

---

## Response Format

### Success (200 OK)

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

### Degraded (207 Multi-Status)

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

### Unhealthy (503 Service Unavailable)

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

---

## How to Use

### 1. Test Locally

```bash
# Terminal 1: Start the app
cd backend
python -m pytest tests/test_health_checks.py::TestDeepHealthCheck -v

# Or run the Flask app
export FLASK_ENV=development
python -c "from wsgi import create_app; app = create_app(); app.run()"

# Terminal 2: Test the endpoint
curl -s http://localhost:5000/health/deep | jq

# Test specific cases
curl -s http://localhost:5000/health/live | jq
curl -s http://localhost:5000/health/ready | jq
curl -s http://localhost:5000/health/deep | jq
```

### 2. Deploy to AWS

#### Option A: Using Serverless Framework

```bash
# Copy the configuration
cp serverless-health-check-config.yml serverless.yml

# Deploy
serverless deploy --stage production --region us-east-1

# Get the endpoint URL
serverless info --stage production
```

#### Option B: Manual Deployment

```bash
# 1. Create SNS topic for alerts
aws sns create-topic --name heavy-freight-health-check-alerts-production

# 2. Create Lambda function for keep-warm
aws lambda create-function \
  --function-name keep-warm-health-check \
  --runtime python3.11 \
  --handler scripts.keep_warm_lambda_health_check.lambda_handler \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --environment "Variables={API_BASE_URL=https://your-api.com,ALERT_SNS_TOPIC=arn:aws:sns:us-east-1:ACCOUNT:topic}"

# 3. Create EventBridge rule
aws events put-rule \
  --name keep-warm-health-check \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED

# 4. Add Lambda as target
aws events put-targets \
  --rule keep-warm-health-check \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:keep-warm-health-check"

# 5. Grant Lambda permission
aws lambda add-permission \
  --function-name keep-warm-health-check \
  --principal events.amazonaws.com \
  --action lambda:InvokeFunction \
  --source-arn arn:aws:events:us-east-1:ACCOUNT:rule/keep-warm-health-check
```

### 3. Monitor in CloudWatch

```bash
# View health check metrics
aws cloudwatch get-metric-statistics \
  --namespace HeavyFreight/HealthCheck \
  --metric-name HealthStatus \
  --start-time 2026-04-03T00:00:00Z \
  --end-time 2026-04-04T00:00:00Z \
  --period 300 \
  --statistics Average

# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name heavy-freight-health \
  --dashboard-body file://dashboard-config.json
```

### 4. Set Up Alerts

```bash
# Subscribe to SNS topic
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:heavy-freight-health-check-alerts-production \
  --protocol email \
  --notification-endpoint ops-team@heavy-freight.com

# Create CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name health-check-failure \
  --alarm-description "Alert when health check fails" \
  --metric-name HealthStatus \
  --namespace HeavyFreight/HealthCheck \
  --statistic Average \
  --period 300 \
  --threshold 0.5 \
  --comparison-operator LessThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:heavy-freight-health-check-alerts-production
```

---

## Integration Points

### 1. EventBridge (Keep-Warm)
- Triggers Lambda every 5 minutes
- Calls `/health/deep` endpoint
- Sends alerts on failure
- Keeps container warm

### 2. CloudWatch
- Tracks health status over time
- Monitors latency per dependency
- Shows individual system status
- Enables dashboards and analytics

### 3. SNS (Alerts)
- Notifies on critical failures
- Includes detailed error information
- Can route to different teams by severity
- Integrates with PagerDuty, Slack, etc.

### 4. Monitoring Platforms
- DataDog: Custom HTTP checks
- New Relic: Synthetic monitoring
- Grafana: Prometheus endpoint (future)

---

## Dependencies Checked

### 1. MongoDB (CRITICAL)
- **Check Method**: `db.command('ping', timeoutMS=2000)`
- **Timeout**: 2 seconds
- **Impact**: Complete service failure without MongoDB
- **Metrics**: 
  - `healthy`: boolean
  - `latency_ms`: response time
- **Failure Scenarios**:
  - Connection refused
  - Authentication failed
  - Network unreachable
  - Timeout

### 2. AWS Secrets Manager (HIGH in Production)
- **Check Method**: `boto3.client('secretsmanager').list_secrets()`
- **Timeout**: 5 seconds
- **Impact**: Cannot retrieve credentials in production Lambda
- **Metrics**:
  - `healthy`: boolean
  - `accessible`: whether running on Lambda
  - `region`: AWS region
  - `latency_ms`: response time
  - `error_code`: AWS error (AccessDenied, InvalidSignatureException)
- **Failure Scenarios**:
  - IAM policy missing
  - Invalid AWS credentials
  - Service endpoint unreachable
  - Not running on Lambda (acceptable in dev)

### 3. Rate Limiter (CRITICAL)
- **Check Method**: `rate_limiter.collection.count_documents({})`
- **Timeout**: Part of MongoDB timeout
- **Impact**: Cannot enforce rate limits without rate limiter
- **Metrics**:
  - `healthy`: boolean
  - `initialized`: whether rate limiter was set up
  - `collection_accessible`: can access MongoDB collection
  - `documents_count`: number of active rate limit entries
  - `latency_ms`: response time
- **Failure Scenarios**:
  - Collection doesn't exist
  - MongoDB connection problem
  - Insufficient permissions
  - Collection corrupted

---

## Performance Targets

```
/health/live    → <10ms   (no external calls)
/health/ready   → <1s     (MongoDB ping + S3 check)
/health/deep    → <5s     (all 3 dependencies with timeouts)
```

---

## Testing Checklist

- [ ] Run `pytest tests/test_health_checks.py::TestDeepHealthCheck -v`
- [ ] Test with `curl -s http://localhost:5000/health/deep | jq`
- [ ] Verify response includes all three dependencies
- [ ] Check that status codes are correct (200/207/503)
- [ ] Confirm duration_ms is included
- [ ] Test with mocked failures (MongoDB down, etc.)
- [ ] Verify no authentication bypasses are present
- [ ] Check error messages for security issues (no stack traces)

---

## Troubleshooting

### "Rate limiter collection access failed"
→ Check MongoDB connection and rate_limits collection exists

### "Access Denied - IAM role lacks Secrets Manager permission"
→ Add `secretsmanager:GetSecretValue` to Lambda IAM role

### "Connection refused"
→ Check MongoDB is running and accessible on configured URI

### "Health check timeout"
→ Increase timeout in keep-warm Lambda (currently 10s)

### "Not receiving SNS alerts"
→ Check SNS topic ARN is correct and subscription is confirmed

---

## Future Enhancements

- [ ] Add Redis cache health check
- [ ] Add S3 connectivity check to deep endpoint
- [ ] Prometheus metrics export (`/metrics`)
- [ ] GraphQL endpoint for health checks
- [ ] Historical health data in database
- [ ] Predictive alerting based on trends
- [ ] Multi-region health aggregation
