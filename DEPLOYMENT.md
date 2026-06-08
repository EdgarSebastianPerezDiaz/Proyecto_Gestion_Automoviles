# 📋 Deployment Guide - Heavy Freight Platform Backend

## Overview

This guide covers how to set up and manage deployments for the Heavy Freight Platform backend using GitHub Actions and AWS Lambda.

---

## 📊 Deployment Pipeline

The deployment pipeline is defined in `.github/workflows/deploy.yml` and consists of:

1. **Test Job** - Runs pytest to verify all tests pass
2. **Deploy Job** - Deploys to AWS Lambda using Serverless Framework (only if tests pass)
3. **Rollback Job** - Automatically rolls back on deployment failure

**Triggers:**
- ✅ Automatic: Push to `main` branch
- ✅ Manual: GitHub Actions `workflow_dispatch` button (allows choosing stage)

---

## 🔧 GitHub Secrets Configuration

### Required Secrets

You must configure the following secrets in your GitHub repository settings:

**Location:** `Settings` → `Secrets and variables` → `Actions`

#### 1. AWS Credentials

**`AWS_ACCESS_KEY_ID`** (Required)
- **Description:** AWS IAM Access Key ID
- **How to create:**
  ```bash
  # Create an IAM user with programmatic access
  aws iam create-user --user-name heavy-freight-ci-cd
  aws iam attach-user-policy \
    --user-name heavy-freight-ci-cd \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
  aws iam create-access-key --user-name heavy-freight-ci-cd
  ```
- **Value format:** `AKIAIOSFODNN7EXAMPLE`
- **Security:** Rotate every 90 days

**`AWS_SECRET_ACCESS_KEY`** (Required)
- **Description:** AWS IAM Secret Access Key
- **How to create:** Generated with access key (see above)
- **Value format:** 40-character alphanumeric string
- **Security:** Never commit to repository, store securely
- **⚠️ WARNING:** If exposed, regenerate immediately!

#### 2. JWT Configuration

**`JWT_SECRET_KEY`** (Required)
- **Description:** Secret key for JWT token signing
- **Recommendation:** Generate a strong random string
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- **Value format:** At least 32 characters, random string
- **Security:** Keep confidential, rotate periodically

**`JWT_ALGORITHM`** (Optional)
- **Description:** JWT signing algorithm
- **Default value:** `HS256`
- **Allowed values:** `HS256`, `HS512`, `RS256`, etc.
- **Recommendation:** Use `HS256` for simplicity or `RS256` for enhanced security

**`JWT_EXPIRATION_HOURS`** (Optional)
- **Description:** JWT token expiration time in hours
- **Default value:** `8`
- **Recommendation:** 8 hours for API tokens, adjust based on security needs

#### 3. MongoDB Configuration

**`MONGO_URI`** (Required)
- **Description:** MongoDB connection string
- **Format:** `mongodb+srv://username:password@cluster.mongodb.net/database`
- **Security:** Use environment-specific credentials
- **Example:**
  ```
  mongodb+srv://prod_user:SecurePassword123@cluster-prod.mongodb.net/heavy-freight
  ```
- **⚠️ WARNING:** Never use special characters without proper URL encoding

#### 4. CORS Configuration

**`CORS_ORIGIN`** (Required)
- **Description:** Frontend origin for CORS validation
- **Format:** Full URL without trailing slash
- **Examples:**
  ```
  Production: https://app.example.com
  Staging: https://staging.example.com
  Development: http://localhost:4200
  ```
- **Security:** Only allow trusted origins
- **Note:** For HTTP API (v2), do NOT include `/stage` in the path

#### 5. Optional Secrets

**`BCRYPT_ROUNDS`** (Optional)
- **Description:** Number of rounds for bcrypt password hashing
- **Default:** `12`
- **Range:** 8-15 (higher = slower but more secure)
- **Format:** Integer string

**`S3_BUCKET_NAME`** (Optional)
- **Description:** S3 bucket name for PDF document storage
- **Format:** `heavy-freight-prod-documents-{account-id}`
- **Security:** Ensure bucket is private with proper ACLs

**`SLACK_WEBHOOK_URL`** (Optional)
- **Description:** Slack webhook for deployment notifications
- **How to create:**
  1. Go to https://api.slack.com/messaging/webhooks
  2. Create new webhook for your channel
  3. Copy webhook URL
- **Usage:** Receives notifications on deployment success/failure
- **Format:** `https://hooks.slack.com/services/...`

---

## 🔐 How to Add Secrets to GitHub

### Method 1: GitHub Web UI (Easiest)

1. Navigate to your repository
2. Click **Settings** (top right)
3. Go to **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Enter secret name (e.g., `AWS_ACCESS_KEY_ID`)
6. Paste secret value
7. Click **Add secret**

**Repeat for all required secrets**

### Method 2: GitHub CLI

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com

# Add AWS Access Key
gh secret set AWS_ACCESS_KEY_ID --body "AKIAIOSFODNN7EXAMPLE"

# Add AWS Secret Key
gh secret set AWS_SECRET_ACCESS_KEY --body "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Add JWT Secret
gh secret set JWT_SECRET_KEY --body "your-jwt-secret-key-here"

# Add MongoDB URI
gh secret set MONGO_URI --body "mongodb+srv://user:pass@cluster.mongodb.net/db"

# Add CORS Origin
gh secret set CORS_ORIGIN --body "https://app.example.com"

# List all secrets
gh secret list
```

### Method 3: Terraform/IaC (For Teams)

```hcl
resource "github_actions_secret" "aws_access_key_id" {
  repository       = "heavy-freight-platform"
  secret_name      = "AWS_ACCESS_KEY_ID"
  plaintext_value  = var.aws_access_key_id
}

resource "github_actions_secret" "aws_secret_access_key" {
  repository       = "heavy-freight-platform"
  secret_name      = "AWS_SECRET_ACCESS_KEY"
  plaintext_value  = var.aws_secret_access_key
}

resource "github_actions_secret" "jwt_secret_key" {
  repository       = "heavy-freight-platform"
  secret_name      = "JWT_SECRET_KEY"
  plaintext_value  = var.jwt_secret_key
}

# ... repeat for other secrets
```

---

## 📝 Environment-Specific Configuration

### Development (dev)

```
AWS_REGION: us-east-1
Stage: dev
Concurrency: 0
Keep-warm: Disabled
```

### Staging (staging)

```
AWS_REGION: us-east-1
Stage: staging
Concurrency: 1
Keep-warm: Enabled
```

### Production (prod)

```
AWS_REGION: us-east-1
Stage: prod
Concurrency: 2
Keep-warm: Enabled
```

**To deploy to a specific stage:**

1. Go to **Actions** tab in GitHub
2. Click **Deploy to AWS Lambda**
3. Click **Run workflow**
4. Select stage from dropdown (dev, staging, prod)
5. Click **Run workflow**

---

## 🚀 Manual Deployment

### Using GitHub Actions UI

1. Go to **Actions** → **Deploy to AWS Lambda**
2. Click **Run workflow**
3. Leave default (prod) or select alternative stage
4. Click **Run workflow**
5. Monitor job progress in real-time

### Using GitHub CLI

```bash
# Trigger workflow for main branch (prod)
gh workflow run deploy.yml

# Trigger with specific stage
gh workflow run deploy.yml \
  -f stage=staging

# Check workflow status
gh run list -w deploy.yml
```

### Using Serverless CLI Locally

```bash
# Prerequisite: AWS credentials configured locally
export AWS_ACCESS_KEY_ID="your-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# Deploy to production
cd backend
serverless deploy --stage prod --verbose

# Deploy to staging
serverless deploy --stage staging --verbose

# Get deployment info
serverless info --stage prod

# Rollback to previous version
serverless rollback --stage prod
```

---

## 🧪 Testing Deployment Workflow

### Local Testing with Act

GitHub provides a tool called `act` to test workflows locally:

```bash
# Install act
# macOS:
brew install act
# Linux:
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | bash
# Windows: Use WSL or GitHub Desktop

# Create .env file with your secrets
cat > .env << EOF
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
JWT_SECRET_KEY=your-jwt-secret
MONGO_URI=your-mongo-uri
CORS_ORIGIN=https://app.example.com
EOF

# Run the workflow locally
act push -b -f .github/workflows/deploy.yml

# Run specific job
act push -j test

# Run with specific secrets from file
act push --secret-file .env
```

### Manual Workflow Validation

```bash
# Validate GitHub Actions workflow syntax
pip install yamllint
yamllint .github/workflows/deploy.yml

# Check for common issues
cat .github/workflows/deploy.yml | grep -E "TODO|FIXME|XXX"
```

---

## 📊 Monitoring Deployments

### CloudWatch Logs

```bash
# View Lambda function logs
aws logs tail /aws/lambda/heavy-freight-platform-backend-api-prod --follow

# View API Gateway logs (HTTP API)
aws logs tail /aws/http-api/heavy-freight-platform-backend --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/heavy-freight-platform-backend-api-prod \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics

```bash
# Get Lambda function metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=heavy-freight-platform-backend-api-prod \
  --start-time 2026-05-15T00:00:00Z \
  --end-time 2026-05-16T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### GitHub Actions

1. Go to **Actions** tab
2. Click on the workflow run
3. Expand job steps to see detailed logs
4. Check **Artifacts** tab for deployment summary

---

## 🔄 Rollback Procedure

### Automatic Rollback

The workflow automatically attempts rollback on deployment failure:

```yaml
rollback:
  name: Rollback on Failure
  runs-on: ubuntu-latest
  needs: deploy
  if: failure()
```

### Manual Rollback

```bash
# Rollback to previous version
cd backend
serverless rollback --stage prod --verbose

# Rollback to specific timestamp
serverless rollback --stage prod --timestamp "1620000000"

# List deployment history
serverless rollback list --stage prod
```

### Verify Rollback

```bash
# Check current deployment
serverless info --stage prod

# Test API endpoint
curl https://{api-id}.execute-api.region.com/health/live
```

---

## ⚠️ Troubleshooting

### Common Issues

**1. AWS Credentials Invalid**
```
Error: The AWS Access Key Id provided does not exist
```
- **Solution:** Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are correct
- **Check:** `aws sts get-caller-identity` locally

**2. Insufficient Permissions**
```
Error: User is not authorized to perform: lambda:CreateFunction
```
- **Solution:** Attach AdministratorAccess or specific IAM policies
- **Check:** User should have Lambda, API Gateway, IAM permissions

**3. Deployment Timeout**
```
Error: Serverless deployment timed out after 30 minutes
```
- **Solution:** Increase CloudFormation timeout or check for blocking resources
- **Check:** View CloudFormation events in AWS Console

**4. CORS Origin Not Updated**
```
Error: Origin 'https://app.example.com' is not allowed by Access-Control-Allow-Origin
```
- **Solution:** Update CORS_ORIGIN secret with correct frontend URL
- **Check:** Ensure no `/stage` in HTTP API configuration

**5. MongoDB Connection Failed**
```
Error: connect ENOTFOUND cluster-prod.mongodb.net
```
- **Solution:** Verify MONGO_URI is correct and network is accessible
- **Check:** Test connection locally with: `python -c "from pymongo import MongoClient; MongoClient('uri')"`

### Debug Tips

1. **Enable Verbose Logging:**
   ```bash
   serverless deploy --stage prod --verbose --debug
   ```

2. **Check GitHub Actions Logs:**
   - Go to Actions → Workflow run → Expand failed step
   - Look for error messages and stack traces

3. **AWS CloudFormation Events:**
   ```bash
   aws cloudformation describe-stack-events \
     --stack-name heavy-freight-platform-backend-prod
   ```

4. **Local Testing:**
   ```bash
   cd backend
   pytest tests/ -v
   python wsgi.py  # Test Flask app locally
   ```

---

## 🔒 Security Best Practices

### Secret Rotation

1. **Set calendar reminder** for quarterly secret rotation
2. **Generate new secrets** in advance
3. **Update GitHub secrets** with new values
4. **Deploy** with new secrets
5. **Revoke old AWS keys** after successful deployment

### AWS IAM Best Practices

```bash
# Create a dedicated CI/CD user (instead of root)
aws iam create-user --user-name github-actions-ci-cd

# Attach minimal required policies
aws iam attach-user-policy \
  --user-name github-actions-ci-cd \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess

aws iam attach-user-policy \
  --user-name github-actions-ci-cd \
  --policy-arn arn:aws:iam::aws:policy/AmazonAPIGatewayFullAccess

aws iam attach-user-policy \
  --user-name github-actions-ci-cd \
  --policy-arn arn:aws:iam::aws:policy/CloudFrontFullAccess

# Create access key for GitHub Actions
aws iam create-access-key --user-name github-actions-ci-cd
```

### Secret Security

- ✅ Use GitHub Secrets for sensitive data
- ✅ Enable branch protection on `main`
- ✅ Require code review before merge
- ✅ Rotate credentials every 90 days
- ✅ Revoke old keys immediately after rotation
- ❌ Never commit secrets to repository
- ❌ Never share secrets via Slack/email
- ❌ Never use personal AWS accounts

---

## 📋 Pre-Deployment Checklist

Before your first deployment, verify:

- [ ] All required secrets are configured in GitHub
- [ ] AWS credentials have appropriate permissions
- [ ] MongoDB connection string is correct and accessible
- [ ] CORS origin matches frontend URL (no /stage)
- [ ] JWT secret is strong and random
- [ ] Tests pass locally: `pytest tests/ -v`
- [ ] No hardcoded secrets in code
- [ ] serverless.yml has correct stage configuration
- [ ] All Lambda function environment variables are set
- [ ] CloudWatch alarms are configured

---

## 📞 Support

**Issues?** Check:
1. GitHub Actions logs (Actions tab → Workflow run)
2. AWS CloudFormation events (CloudFormation → Stacks)
3. CloudWatch logs (/aws/lambda/...)
4. Deployment summary artifact

**Contact:**
- Platform Team: [team-contact]
- AWS Support: https://console.aws.amazon.com/support

---

## 🚀 Next Steps

1. **Configure all required secrets** (see GitHub Secrets Configuration above)
2. **Test local deployment:** `serverless deploy --stage dev`
3. **Verify tests pass:** `pytest tests/ -v`
4. **Push to main branch** and watch GitHub Actions
5. **Monitor CloudWatch logs** after deployment
6. **Smoke test the endpoint:** `curl https://endpoint/health/live`

---

**Status:** ✅ Ready for production deployment

**Last Updated:** May 15, 2026
**Maintained By:** GitHub Copilot
