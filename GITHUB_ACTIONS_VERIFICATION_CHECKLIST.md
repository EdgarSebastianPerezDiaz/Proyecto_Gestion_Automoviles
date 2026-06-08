# ✅ GitHub Actions Workflow - Pre-Deployment Verification

Complete checklist before your first deployment with GitHub Actions.

---

## 🔧 Prerequisites

- [ ] Repository created on GitHub (if not already)
- [ ] Local git configured: `git config user.name` and `git config user.email`
- [ ] `.github/workflows/deploy.yml` file exists
- [ ] All required secrets added to GitHub

---

## 📋 Step 1: Verify Workflow File

```bash
# Check that the file exists
ls -la .github/workflows/deploy.yml

# Validate YAML syntax (if yamllint installed)
yamllint .github/workflows/deploy.yml

# Expected output: No errors
```

**✅ Checklist:**
- [ ] File path: `.github/workflows/deploy.yml`
- [ ] File contains `on: push` trigger
- [ ] File contains `workflow_dispatch` trigger
- [ ] Jobs named: `test`, `deploy`, `rollback`
- [ ] No syntax errors

---

## 🔐 Step 2: Configure GitHub Secrets

### Required Secrets Check
Go to: `Settings` → `Secrets and variables` → `Actions`

Verify these exist and have values:
- [ ] `AWS_ACCESS_KEY_ID` - Not empty, starts with AKIA
- [ ] `AWS_SECRET_ACCESS_KEY` - Not empty, 40 characters
- [ ] `JWT_SECRET_KEY` - Not empty, 32+ characters
- [ ] `MONGO_URI` - Correct format: `mongodb+srv://...`
- [ ] `CORS_ORIGIN` - URL format: `https://example.com` (no /stage)

### Verify Secrets via CLI
```bash
# List all secrets
gh secret list

# Expected output:
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
# CORS_ORIGIN
# JWT_SECRET_KEY
# MONGO_URI
```

**✅ Checklist:**
- [ ] All 5 required secrets present
- [ ] `gh secret list` shows all of them
- [ ] No typos in secret names (case-sensitive)

---

## 🧪 Step 3: Test Locally Before Pushing

### Run Tests Locally
```bash
# Install dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests (must all pass)
pytest tests/ -v

# Expected: All tests pass (e.g., "826 passed in 76.32s")
```

**✅ Checklist:**
- [ ] No dependencies missing
- [ ] All tests pass locally
- [ ] No import errors
- [ ] Test output shows 826+ tests passing

### Verify serverless.yml
```bash
# Check serverless.yml exists
ls -la backend/serverless.yml

# Validate YAML syntax
yamllint backend/serverless.yml

# Expected: No errors
```

**✅ Checklist:**
- [ ] File exists at `backend/serverless.yml`
- [ ] No YAML syntax errors
- [ ] Contains all required sections (provider, functions, plugins, resources)
- [ ] stage is set to 'prod'

---

## 🚀 Step 4: First Deployment

### Option A: Push to Main (Automatic)
```bash
# Make sure you're on main branch
git checkout main

# Make a test commit (e.g., update README)
echo "# Heavy Freight Platform" >> README.md

# Commit and push
git add README.md
git commit -m "Test GitHub Actions workflow"
git push origin main
```

### Option B: Manual Trigger (Recommended for first test)
```
1. Go to: https://github.com/[owner]/[repo]/actions
2. Click: "Deploy to AWS Lambda"
3. Click: "Run workflow"
4. Select: "prod" (default)
5. Click: "Run workflow"
```

**✅ Checklist:**
- [ ] Push to main or manual trigger executed
- [ ] GitHub Actions page loads
- [ ] Workflow shows "Deploy to AWS Lambda"
- [ ] Workflow run appears in list

---

## 📊 Step 5: Monitor Workflow Execution

### Watch in GitHub Actions UI
```
1. Go to Actions tab
2. Click "Deploy to AWS Lambda"
3. Click the workflow run (should be top of list)
4. Watch jobs execute in real-time
```

### Expected Job Sequence
```
✓ Job "test" starts
  - Checkout code
  - Set up Python
  - Install dependencies
  - Run pytest
  (should take ~1-2 min)

✓ Job "deploy" starts (only if test passes)
  - Checkout code
  - Set up Node.js
  - Set up Python
  - Install dependencies
  - Install Serverless Framework
  - Configure AWS credentials
  - Deploy via Serverless
  - Extract deployment output
  - Run smoke tests
  - Create summary
  (should take ~2-3 min)

✓ Jobs complete successfully
```

**✅ Checklist:**
- [ ] Test job appears and starts
- [ ] Test job shows "✓ passed"
- [ ] Deploy job appears after test completes
- [ ] Deploy job shows "✓ passed"
- [ ] All steps complete without errors

---

## ✨ Step 6: Verify Deployment Success

### Check GitHub Artifacts
```
1. Go to workflow run
2. Scroll to "Artifacts"
3. Download "deployment-summary"
4. Verify contains API endpoint URL
```

### Test API Endpoint
```bash
# Extract endpoint from deployment summary
# Format: https://xxxxx.execute-api.region.com

# Test health endpoint
curl https://[api-id].execute-api.us-east-1.amazonaws.com/health/live

# Expected response:
# {"status": "alive"}
```

### Check AWS Lambda
```bash
# List Lambda functions
aws lambda list-functions --region us-east-1 | grep heavy-freight

# Expected: Should see "heavy-freight-platform-backend-api-prod"
```

### Check CloudWatch Logs
```bash
# Tail Lambda logs
aws logs tail /aws/lambda/heavy-freight-platform-backend-api-prod --follow

# Expected: Logs from Lambda invocations
```

**✅ Checklist:**
- [ ] API health endpoint responds with 200
- [ ] Response body contains `"status": "alive"`
- [ ] Lambda function visible in AWS Console
- [ ] CloudWatch logs visible with recent entries
- [ ] No error messages in logs

---

## 🧪 Step 7: Smoke Tests Verification

### Test 1: Health (Liveness)
```bash
API_ENDPOINT="https://[api-id].execute-api.us-east-1.amazonaws.com"

curl -v "$API_ENDPOINT/health/live"

# Expected: HTTP 200, {"status": "alive"}
```

### Test 2: Deep Health
```bash
curl -v "$API_ENDPOINT/health/deep"

# Expected: HTTP 200, contains multiple health checks
```

### Test 3: JWT Protection
```bash
curl -v "$API_ENDPOINT/api/trips"

# Expected: HTTP 401 (Unauthorized - JWT required)
```

### Test 4: CORS Headers
```bash
curl -v -X OPTIONS "$API_ENDPOINT/api/trips" \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: GET"

# Expected: CORS headers in response, like:
# Access-Control-Allow-Origin: https://app.example.com
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, ...
```

**✅ Checklist:**
- [ ] Test 1 passes (health endpoint 200)
- [ ] Test 2 passes (deep health 200)
- [ ] Test 3 passes (JWT protection 401)
- [ ] Test 4 passes (CORS headers present)

---

## 🔍 Step 8: Common Issues & Fixes

### Issue: Test Job Fails

**Error:** `pytest: No module named 'pytest'`
```bash
# Fix: Install dev dependencies
cd backend
pip install -r requirements-dev.txt
```

**Error:** `Error: MONGO_URI or database connection failed`
```bash
# Fix: Verify MONGO_URI secret is correct
# Secret must be accessible from GitHub Actions runner
# Test locally first
```

**Error:** `Tests timeout after 30 seconds`
```bash
# Fix: Install mongomock for testing
pip install mongomock
# Tests should use mongomock, not real MongoDB
```

### Issue: Deploy Job Fails

**Error:** `AWS credentials not configured`
```bash
# Fix: Check GitHub Secrets
# Settings → Secrets and variables → Actions
# Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
```

**Error:** `Serverless deploy failed - permission denied`
```bash
# Fix: IAM user needs more permissions
# AWS Console → IAM → Users → github-actions
# Attach: AdministratorAccess policy (or specific Lambda/API Gateway policies)
```

**Error:** `API Gateway role not found`
```bash
# Fix: This is expected with HTTP API v2
# Role is created automatically
# Check CloudFormation events for details
```

### Issue: API Not Responding

**Error:** `curl: (7) Failed to connect to endpoint`
```bash
# Fix: Wait 2-3 minutes for CloudFormation to finish
# Check CloudFormation stack status in AWS Console
```

**Error:** `CORS error in frontend`
```bash
# Fix: Verify CORS_ORIGIN secret matches frontend URL
# Should be: https://app.example.com (no /stage)
# Redeploy after fixing
```

**✅ Checklist:**
- [ ] All common issues reviewed
- [ ] Familiar with error resolution steps

---

## 📋 Final Pre-Deployment Checklist

### Configuration
- [ ] `.github/workflows/deploy.yml` file correct
- [ ] All 5 required secrets configured
- [ ] `serverless.yml` validated
- [ ] No hardcoded secrets in code

### Testing
- [ ] Local tests pass: `pytest tests/ -v`
- [ ] No import errors locally
- [ ] No syntax errors in YAML files

### AWS Setup
- [ ] AWS credentials have Lambda, API Gateway permissions
- [ ] IAM user created: `github-actions-ci-cd`
- [ ] S3 bucket (if needed) created and accessible
- [ ] MongoDB connection tested locally

### GitHub Setup
- [ ] Repository created and initialized
- [ ] Branch protection enabled on `main` (optional)
- [ ] Secrets added and verified
- [ ] Actions tab enabled (should be by default)

### Documentation
- [ ] `DEPLOYMENT.md` reviewed
- [ ] `GITHUB_SECRETS_QUICK_SETUP.md` reviewed
- [ ] `.github/workflows/README.md` reviewed
- [ ] Team informed of deployment process

---

## 🚀 Ready to Deploy!

Once all checkboxes are checked:

1. **Push to main branch** or **Trigger workflow manually**
2. **Monitor GitHub Actions** for execution
3. **Verify API endpoint** responds correctly
4. **Check CloudWatch logs** for any issues
5. **Celebrate!** 🎉

---

## 📞 Troubleshooting Support

If workflow fails:

1. **Check GitHub Actions logs**
   - Click workflow run
   - Expand failed step
   - Read error message carefully

2. **Check AWS CloudFormation**
   - AWS Console → CloudFormation → Stacks
   - Look for `heavy-freight-platform-backend`
   - Check Events tab for errors

3. **Check CloudWatch Logs**
   - AWS Console → CloudWatch → Log Groups
   - Look for `/aws/lambda/...` or `/aws/http-api/...`
   - Search for ERROR messages

4. **Check GitHub Secrets**
   - Settings → Secrets → Actions
   - Verify all secrets present
   - Verify no typos in names

5. **Local Testing**
   ```bash
   cd backend
   pytest tests/ -v
   serverless deploy --stage dev
   ```

---

**Status**: Verification checklist complete! Ready for production deployment.

**Next Step**: Push to main or trigger workflow manually.

---

**Last Updated:** May 15, 2026
**Version:** 2.0
