# 🧪 VALIDATION TESTS - HTTP API v2 Migration

Post-deployment verification checklist for REST API → HTTP API migration.

---

## 1️⃣ BASIC CONNECTIVITY

### Test: Health Check (Liveness)
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/health/live

Expected:
  HTTP/2 200 OK
  Content-Type: application/json
  {"status": "alive"}
```

### Test: Deep Health Check
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/health/deep

Expected:
  HTTP/2 200 OK
  {
    "status": "healthy",
    "checks": {
      "mongodb": {"status": "healthy", "latency_ms": 12},
      "secrets_manager": {"status": "healthy"},
      "rate_limiter": {"status": "healthy"}
    }
  }
```

---

## 2️⃣ CORS VALIDATION

### Test: Preflight Request (OPTIONS)
```bash
curl -X OPTIONS https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v

Expected Headers in Response:
  ✓ Access-Control-Allow-Origin: https://app.example.com
  ✓ Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
  ✓ Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With, X-Correlation-ID
  ✓ Access-Control-Allow-Credentials: true
  ✓ Access-Control-Max-Age: 600
```

### Test: CORS with Credentials
```bash
curl -X GET https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
  -H "Origin: https://app.example.com" \
  -H "Authorization: Bearer {valid_jwt_token}" \
  -H "Cookie: session=xyz" \
  -v

Expected:
  ✓ Access-Control-Allow-Credentials: true
  ✓ Set-Cookie header present (if applicable)
```

---

## 3️⃣ JWT AUTHENTICATION

### Test: Missing Token (Should be 401)
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips

Expected:
  HTTP/2 401 Unauthorized
  {"error": "Authorization header missing"}
```

### Test: Invalid Token (Should be 401)
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
  -H "Authorization: Bearer invalid_token_xyz"

Expected:
  HTTP/2 401 Unauthorized
  {"error": "Invalid token"}
```

### Test: Valid Token (Should be 200)
```bash
# Generate valid token locally first
TOKEN=$(python -c "from src.schemas.auth import AuthService; print(AuthService.create_token('test-user'))")

curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
  -H "Authorization: Bearer $TOKEN"

Expected:
  HTTP/2 200 OK
  {"trips": [...], "total": n}
```

---

## 4️⃣ QUERY VALIDATION (422 Responses)

### Test: Invalid Page (Should be 422)
```bash
curl -v "https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips?page=0"

Expected:
  HTTP/2 422 Unprocessable Entity
  {
    "error": "Invalid request parameters",
    "errors": [
      {"field": "page", "message": "Input should be greater than or equal to 1"}
    ]
  }
```

### Test: Invalid Limit (Should be 422)
```bash
curl -v "https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips?limit=999"

Expected:
  HTTP/2 422 Unprocessable Entity
  {
    "error": "Invalid request parameters",
    "errors": [
      {"field": "limit", "message": "Input should be less than or equal to 100"}
    ]
  }
```

### Test: Valid Query (Should be 200)
```bash
curl -v "https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips?page=1&limit=20"

Expected:
  HTTP/2 200 OK
  {"trips": [...], "total": n}
```

---

## 5️⃣ CORRELATION ID TRACKING

### Test: Correlation ID in Response Headers
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/health/live \
  -H "X-Correlation-ID: test-123456"

Expected:
  ✓ Response includes header: X-Correlation-ID: test-123456
  ✓ Logs contain: "correlation_id": "test-123456"
```

### Test: Auto-Generated Correlation ID (if not provided)
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/health/live

Expected:
  ✓ Response includes header: X-Correlation-ID: {auto-generated-uuid}
  ✓ CloudWatch logs contain the same UUID
```

---

## 6️⃣ PDF GENERATION

### Test: Generate PDF (if applicable)
```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips/123/generate-pdf \
  -H "Authorization: Bearer $TOKEN" \
  -v

Expected:
  HTTP/2 200 OK
  Content-Type: application/pdf
  Content-Length: {size}
  [binary PDF data]
```

### Test: PDF in S3
```bash
# List files in S3
aws s3 ls s3://heavy-freight-prod-documents-{account-id}/

Expected:
  ✓ PDF files present with timestamps
  ✓ Proper naming convention
```

---

## 7️⃣ CIRCUIT BREAKER & RESILIENCE

### Test: Circuit Breaker Open (Manual)
Simulate MongoDB down by stopping MongoDB temporarily, then:

```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips

Expected (after 5 failures):
  HTTP/2 503 Service Unavailable
  {"error": "Service temporarily unavailable", "status": "error"}
  Response time: ~2ms (fast fail)
```

### Test: Automatic Recovery
After MongoDB is back:
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips

Expected (within 60s of recovery):
  HTTP/2 200 OK
  {"trips": [...]}
  Circuit breaker state: HALF_OPEN → CLOSED
```

---

## 8️⃣ RATE LIMITING

### Test: Rate Limit Headers
```bash
curl -v https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
  -H "Authorization: Bearer $TOKEN"

Expected Headers in Response:
  ✓ X-RateLimit-Limit: {limit}
  ✓ X-RateLimit-Remaining: {remaining}
  ✓ X-RateLimit-Reset: {timestamp}
```

### Test: Rate Limit Exceeded (429 Too Many Requests)
```bash
# Make many requests in quick succession
for i in {1..101}; do
  curl https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
    -H "Authorization: Bearer $TOKEN"
done

Expected (after limit):
  HTTP/2 429 Too Many Requests
  {"error": "Rate limit exceeded"}
```

---

## 9️⃣ REQUEST SIZE LIMITS

### Test: Valid Payload (< 10 MB)
```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"route": "NYC-LA", "cargo_weight": 5000}' \
  -v

Expected:
  HTTP/2 200 OK or 422 (validation)
```

### Test: Oversized Payload (> 10 MB)
```bash
# Create 11MB file
dd if=/dev/zero of=/tmp/large.bin bs=1M count=11

curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips \
  -H "Authorization: Bearer $TOKEN" \
  --data-binary @/tmp/large.bin \
  -v

Expected:
  HTTP/2 413 Payload Too Large
  Response time: <100ms (fast rejection)
```

---

## 🔟 CLOUDWATCH LOGS

### Test: Logs Structure
```bash
# Go to CloudWatch Logs
# Log group: /aws/http-api/heavy-freight-platform-backend

Expected:
  ✓ All logs in JSON format
  ✓ Include: timestamp, requestId (correlation_id), method, path, status
  ✓ Include: duration, error (if applicable)
  ✓ Queryable via CloudWatch Insights
```

### Test: CloudWatch Insights Query
```sql
fields @timestamp, @message, correlation_id, duration_ms, status_code
| filter status_code >= 400
| stats count() as error_count by status_code
```

Expected:
  ✓ Query returns results
  ✓ Shows error distribution
  ✓ Correlation IDs trackable

---

## 1️⃣1️⃣ PERFORMANCE BASELINE

### Test: Response Time (p50)
```bash
# Load test with 10 concurrent users
ab -n 1000 -c 10 \
  -H "Authorization: Bearer $TOKEN" \
  https://xxxxx.execute-api.us-east-1.amazonaws.com/api/trips

Expected:
  ✓ Mean response time: < 200ms
  ✓ 50% response time (p50): < 150ms
  ✓ Errors: < 0.5%
```

### Test: Response Time (p99)
```bash
# Extract p99 latency from CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=heavy-freight-platform-backend-api-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum

Expected:
  ✓ p99 latency: < 1000ms
  ✓ No timeout errors
```

---

## 1️⃣2️⃣ ERROR RATE

### Test: Overall Error Rate
```bash
# CloudWatch Insights query
fields status_code
| stats count_if(status_code >= 500) as server_errors, count() as total
| fields server_errors/total*100 as error_rate_percent

Expected:
  ✓ Error rate: < 0.5%
  ✓ Most errors are 4xx (client errors), not 5xx
```

---

## 📝 AUTOMATION SCRIPT

Run this after deployment:

```bash
#!/bin/bash

API_URL="https://xxxxx.execute-api.us-east-1.amazonaws.com"
TESTS_PASSED=0
TESTS_FAILED=0

test_endpoint() {
  local name=$1
  local method=$2
  local endpoint=$3
  local expected_status=$4
  
  status=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$API_URL$endpoint")
  
  if [ "$status" == "$expected_status" ]; then
    echo "✓ $name: PASS (HTTP $status)"
    ((TESTS_PASSED++))
  else
    echo "✗ $name: FAIL (Expected $expected_status, got $status)"
    ((TESTS_FAILED++))
  fi
}

# Run tests
test_endpoint "Health (Live)" "GET" "/health/live" "200"
test_endpoint "Health (Deep)" "GET" "/health/deep" "200"
test_endpoint "Missing Auth" "GET" "/api/trips" "401"
test_endpoint "Invalid Query" "GET" "/api/trips?page=0" "422"

# Summary
echo "═══════════════════════════════════════════════════════════"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "═══════════════════════════════════════════════════════════"
```

---

## ✅ SIGN-OFF

After all tests pass, sign off:

```
Migration Date: _____________
Tested By: ___________________
Approval: _____________________

All tests passed: ✓
API is stable: ✓
CORS working: ✓
JWT auth working: ✓
Validation active: ✓
Logs in CloudWatch: ✓
Performance baseline established: ✓

Status: READY FOR PRODUCTION
```

---

**Archive these results for reference**
