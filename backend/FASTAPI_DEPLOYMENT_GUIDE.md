## FastAPI Migration - Deployment Guide

### 1. MIGRATION STATUS ✅
- **Framework Migration**: Flask 3.0.3 + WSGI ➜ FastAPI 0.110.1 + ASGI
- **Lambda Adapter**: serverless-wsgi 3.1.0 ➜ Mangum 0.21.0
- **Entry Point**: wsgi.py ➜ main.py + lambda_handler.py
- **Configuration**: HTTP API v2 with environment variables
- **Tests**: All 826 tests passing ✅

---

### 2. PRE-DEPLOYMENT REQUIREMENTS

#### 2.1 Install Serverless Framework & Plugins
```bash
npm install -g serverless
npm install serverless-python-requirements --save-dev
```

#### 2.2 AWS Credentials Setup
```bash
# Configure AWS credentials (requires valid AWS account)
aws configure

# Or use environment variables:
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### 2.3 Create .env file (Development Only)
```bash
cd backend
cat > .env << 'EOF'
FLASK_ENV=dev
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/freight-platform?retryWrites=true&w=majority
JWT_SECRET_KEY=your_jwt_secret_key_here
CORS_ORIGIN=http://localhost:4200
AWS_REGION=us-east-1
LOG_LEVEL=INFO
EOF
```

**Note**: MongoDB Atlas M0 (free tier) connection string format:
```
mongodb+srv://username:password@cluster.mongodb.net/freight-platform?retryWrites=true&w=majority
```

---

### 3. LOCAL TESTING (BEFORE DEPLOYMENT)

#### 3.1 Install Development Dependencies
```bash
cd backend
pip install -r requirements-dev.txt
pip install -r requirements.txt
```

#### 3.2 Run Unit Tests
```bash
# Run all 826 tests
pytest -v

# Run tests for specific endpoint
pytest tests/test_health_checks.py -v

# Run with coverage
pytest --cov=src tests/ --cov-report=html
```

#### 3.3 Local FastAPI Development Server
```bash
# Start development server (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Server will be available at: http://localhost:8000
# API docs: http://localhost:8000/docs
# ReDoc docs: http://localhost:8000/redoc
```

#### 3.4 Smoke Test - Health Endpoints
```bash
# Test liveness probe
curl http://localhost:8000/health/live

# Expected response:
# {"status":"ok","message":"Service is alive","timestamp":"2026-06-08T10:00:00Z"}

# Test readiness probe
curl http://localhost:8000/health/ready

# Expected response:
# {"status":"ok","message":"All systems ready","timestamp":"2026-06-08T10:00:00Z","checks":{"database":"healthy"}}

# Test deep health check
curl http://localhost:8000/health/deep

# Expected response includes full system status
```

---

### 4. DEPLOYMENT COMMANDS

#### 4.1 Deploy to AWS Lambda (HTTP API v2)

**First Deployment (dev stage)**:
```bash
cd backend

# Install serverless plugin dependencies
npm install

# Deploy to dev stage
serverless deploy --stage dev

# Expected output:
# service: heavy-freight-platform-backend
# stage: dev
# region: us-east-1
# deployed functions:
#   api: heavy-freight-platform-backend-dev-api
# endpoint: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

**Subsequent Deployments**:
```bash
# Quick update (without recreating infrastructure)
serverless deploy function -f api --stage dev
```

**Deploy to Production**:
```bash
# Deploy to prod stage
serverless deploy --stage prod

# Specify custom region
serverless deploy --stage prod --region eu-west-1
```

#### 4.2 View Deployment Logs
```bash
# Show deployment logs in real-time
serverless logs -f api --stage dev --tail

# Show specific number of lines
serverless logs -f api --stage dev -t 50
```

#### 4.3 Remove Deployment
```bash
# Remove all Lambda resources from AWS
serverless remove --stage dev
```

---

### 5. SMOKE TEST COMMANDS (POST-DEPLOYMENT)

#### 5.1 Get Your API Endpoint
After deployment, you'll receive:
```
endpoint: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

Store this in a variable:
```bash
API_ENDPOINT="https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"
```

#### 5.2 Test /health/live Endpoint (Liveness Probe)
```bash
curl -X GET "${API_ENDPOINT}/health/live" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"

# Expected:
# {"status":"ok","message":"Service is alive","timestamp":"2026-06-08T10:00:00Z"}
# HTTP Status: 200
```

#### 5.3 Test /health/ready Endpoint (Readiness Probe)
```bash
curl -X GET "${API_ENDPOINT}/health/ready" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"

# Expected:
# {"status":"ok","message":"All systems ready",...}
# HTTP Status: 200
```

#### 5.4 Test /health/deep Endpoint (Deep Health Check)
```bash
curl -X GET "${API_ENDPOINT}/health/deep" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n"

# Expected includes detailed system status, database health, etc.
# HTTP Status: 200
```

#### 5.5 Automated Smoke Test Script
```bash
#!/bin/bash
# save as: smoke_test.sh

API_ENDPOINT="${1:?Usage: ./smoke_test.sh https://api-endpoint}"
FAILED=0

echo "Starting smoke tests against: $API_ENDPOINT"
echo "================================================"

# Test 1: Liveness probe
echo -n "Testing /health/live ... "
RESPONSE=$(curl -s -w "%{http_code}" "${API_ENDPOINT}/health/live")
HTTP_CODE="${RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
  echo "PASS (HTTP $HTTP_CODE)"
else
  echo "FAIL (HTTP $HTTP_CODE)"
  FAILED=$((FAILED + 1))
fi

# Test 2: Readiness probe
echo -n "Testing /health/ready ... "
RESPONSE=$(curl -s -w "%{http_code}" "${API_ENDPOINT}/health/ready")
HTTP_CODE="${RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
  echo "PASS (HTTP $HTTP_CODE)"
else
  echo "FAIL (HTTP $HTTP_CODE)"
  FAILED=$((FAILED + 1))
fi

# Test 3: Deep health check
echo -n "Testing /health/deep ... "
RESPONSE=$(curl -s -w "%{http_code}" "${API_ENDPOINT}/health/deep")
HTTP_CODE="${RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
  echo "PASS (HTTP $HTTP_CODE)"
else
  echo "FAIL (HTTP $HTTP_CODE)"
  FAILED=$((FAILED + 1))
fi

echo "================================================"
if [ $FAILED -eq 0 ]; then
  echo "All smoke tests PASSED ✅"
  exit 0
else
  echo "$FAILED smoke tests FAILED ❌"
  exit 1
fi
```

**Run the script**:
```bash
chmod +x smoke_test.sh
./smoke_test.sh https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

#### 5.6 Test Authentication Endpoint
```bash
# Register a new user
curl -X POST "${API_ENDPOINT}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"TestPassword123!",
    "name":"Test User"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"

# Login
curl -X POST "${API_ENDPOINT}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"TestPassword123!"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n"

# Expected response includes:
# {"access_token":"eyJ...","token_type":"bearer"}
```

---

### 6. ENVIRONMENT CONFIGURATION FOR PRODUCTION

#### 6.1 MongoDB Atlas Setup (Free Tier M0)
```bash
# 1. Create MongoDB Atlas account: https://www.mongodb.com/cloud/atlas
# 2. Create free M0 cluster
# 3. Get connection string: mongodb+srv://username:password@cluster.mongodb.net/

# 4. Store in environment variable (AWS Lambda):
export MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/freight-platform?retryWrites=true&w=majority"
```

#### 6.2 JWT Secret Key (Generate Secure Key)
```bash
# Generate a random secure key (minimum 32 characters)
openssl rand -base64 32

# Store in environment variable:
export JWT_SECRET_KEY="your_generated_key_here"
```

#### 6.3 CORS Configuration
```bash
# For frontend on specific domain:
export CORS_ORIGIN="https://yourdomain.com"

# For localhost (development):
export CORS_ORIGIN="http://localhost:4200"
```

#### 6.4 Deploy with Environment Variables
```bash
# Option 1: Use .env file (dev/staging only)
serverless deploy --stage dev --param="mongoUri=$MONGO_URI" --param="jwtSecret=$JWT_SECRET_KEY"

# Option 2: Edit .env in serverless.yml
# The serverless.yml already references environment variables from .env

# Option 3: AWS Secrets Manager (recommended for production)
# Create secrets in AWS:
aws secretsmanager create-secret \
  --name /heavy-freight/prod/MONGO_URI \
  --secret-string "mongodb+srv://..."

# Update main.py to read from Secrets Manager (already implemented in _get_secret())
```

---

### 7. MONITORING & TROUBLESHOOTING

#### 7.1 View Lambda Logs
```bash
# Real-time logs
serverless logs -f api --stage dev --tail

# Last 50 lines
serverless logs -f api --stage dev -t 50

# AWS CloudWatch (direct)
aws logs tail /aws/lambda/heavy-freight-platform-backend-dev-api --follow
```

#### 7.2 Common Issues

**Issue: "No module named 'mangum'"**
```bash
# Solution: Reinstall dependencies
cd backend
pip install -r requirements.txt
serverless deploy --stage dev
```

**Issue: "MongoDBConnection initialization error"**
```bash
# Solution: Verify MONGO_URI is set
echo $MONGO_URI  # Should show your MongoDB connection string
# If empty, add to .env or environment
```

**Issue: "CORS errors from frontend"**
```bash
# Solution: Update CORS_ORIGIN
export CORS_ORIGIN="https://your-frontend-domain.com"
serverless deploy --stage prod
```

**Issue: "JWT token validation fails"**
```bash
# Solution: Ensure JWT_SECRET_KEY is consistent
# Same key must be used for token generation and validation
# Check in MongoDB audit logs if needed
```

#### 7.3 Check Deployment Status
```bash
# List all deployed Lambda functions
serverless info --stage dev

# Get function details
aws lambda get-function --function-name heavy-freight-platform-backend-dev-api

# Get recent invocations
aws logs tail /aws/lambda/heavy-freight-platform-backend-dev-api --follow
```

---

### 8. ROLLBACK PROCEDURES

#### 8.1 Rollback to Previous Version
```bash
# AWS CloudFormation keeps previous versions
# List available versions:
aws lambda list-versions-by-function --function-name heavy-freight-platform-backend-dev-api

# Alias to previous version:
aws lambda update-alias \
  --function-name heavy-freight-platform-backend-dev-api \
  --name live \
  --function-version 1
```

#### 8.2 Manual Rollback (if needed)
```bash
# Remove current deployment
serverless remove --stage dev

# Deploy previous code version
git checkout <previous-commit>
serverless deploy --stage dev
```

---

### 9. COST ESTIMATION (FREE TIER)

**AWS Lambda Free Tier (monthly)**:
- 1,000,000 requests included
- 400,000 GB-seconds of compute included
- ✅ **No charge for health checks if under 1M requests/month**

**MongoDB Atlas M0 (free tier)**:
- ✅ Completely free
- 512MB storage included
- No credit card required
- Perfect for development/testing

**HTTP API v2 (Lower cost than REST API)**:
- $0.34 per 1M requests (vs $3.50 for REST API)
- No data transfer charges for local testing

**Estimated Monthly Cost for Light Usage**:
- Lambda: $0.00 (within free tier)
- MongoDB: $0.00 (free tier)
- HTTP API: $0.00 (within free tier)
- **Total: $0.00** ✅

---

### 10. QUICK START COMMANDS (Copy-Paste)

**One-time setup**:
```bash
cd backend
npm install serverless-python-requirements --save-dev
aws configure  # Enter AWS credentials
cat > .env << 'EOF'
FLASK_ENV=dev
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/freight-platform?retryWrites=true&w=majority
JWT_SECRET_KEY=$(openssl rand -base64 32)
CORS_ORIGIN=http://localhost:4200
EOF
```

**Deploy**:
```bash
cd backend
serverless deploy --stage dev
```

**After deployment, get endpoint and test**:
```bash
API_ENDPOINT=$(serverless info --stage dev | grep endpoint | awk '{print $NF}')
echo "Testing endpoint: $API_ENDPOINT"

# Smoke test
curl "${API_ENDPOINT}/health/live" && echo "✅ API is working"
```

---

### 11. CHECKLIST FOR PRODUCTION DEPLOYMENT

- [ ] All 826 tests passing: `pytest`
- [ ] Local smoke test passes: `./smoke_test.sh http://localhost:8000`
- [ ] .env file created with real MongoDB Atlas URI
- [ ] JWT_SECRET_KEY generated with `openssl rand -base64 32`
- [ ] CORS_ORIGIN set to frontend URL
- [ ] AWS credentials configured: `aws configure`
- [ ] Serverless plugins installed: `npm install`
- [ ] Deploy to staging first: `serverless deploy --stage staging`
- [ ] Staging smoke tests pass
- [ ] Deploy to production: `serverless deploy --stage prod`
- [ ] Production health endpoint responds: `curl $API_ENDPOINT/health/live`
- [ ] Monitor logs: `serverless logs -f api --tail`
- [ ] No errors in CloudWatch logs

---

### 12. FILES CHANGED IN MIGRATION

**New Files**:
- `backend/main.py` - FastAPI application
- `backend/lambda_handler.py` - Lambda handler with Mangum adapter
- `backend/src/api/fastapi_routers/health.py` - Health check endpoints
- `backend/src/api/fastapi_routers/auth.py` - Authentication endpoints
- `backend/src/api/fastapi_routers/*.py` - Domain routers (8 files)
- `backend/src/api/fastapi_routers/__init__.py` - Router initialization

**Modified Files**:
- `backend/serverless.yml` - Updated handler from wsgi.handler to lambda_handler.handler
- `backend/requirements.txt` - Replaced serverless-wsgi with mangum, added FastAPI/uvicorn

**Unchanged Files**:
- All `backend/src/` service and repository layers
- All `backend/tests/` - 826 tests still passing
- `.gitignore` - No changes needed
- All domain logic and business logic

---

### Questions?
- Check logs: `serverless logs -f api --tail`
- Verify endpoint: `serverless info --stage dev`
- Test directly: `curl https://api-endpoint/health/live`
