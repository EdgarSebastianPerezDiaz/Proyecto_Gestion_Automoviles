# GitHub Actions Workflows

This directory contains GitHub Actions workflow files for Continuous Integration and Deployment (CI/CD).

## 📋 Available Workflows

### `deploy.yml`
**Heavy Freight Platform Backend - Automated Deployment to AWS Lambda**

**Purpose:** Automatically test and deploy backend to AWS Lambda using Serverless Framework

**Triggers:**
- ✅ `push` to `main` branch (automatic deployment to prod)
- ✅ `workflow_dispatch` (manual trigger with stage selection)

**Jobs:**
1. **test** - Runs pytest to verify all tests pass
2. **deploy** - Deploys to AWS Lambda (only if tests pass)
3. **rollback** - Automatically rolls back on deployment failure

**Environment:**
- AWS Region: `us-east-1`
- Python: `3.11`
- Node.js: `20`
- Serverless Framework: Latest

**Duration:** ~3-5 minutes per run

**Logs:** GitHub Actions tab → Click workflow run → View detailed logs

---

## 🚀 How to Trigger Deployment

### Automatic Deployment (on push to main)
```bash
# Code will be tested and deployed automatically
git push origin main
```

### Manual Deployment (choose stage)
```
1. Go to GitHub repository
2. Click "Actions" tab
3. Click "Deploy to AWS Lambda"
4. Click "Run workflow"
5. Select stage (dev, staging, prod)
6. Click "Run workflow"
```

### Using GitHub CLI
```bash
# Deploy with default stage (prod)
gh workflow run deploy.yml

# Deploy to specific stage
gh workflow run deploy.yml -f stage=staging

# View workflow runs
gh run list -w deploy.yml
```

---

## 📊 Workflow Steps

### Test Job
```
1. Checkout code
2. Set up Python 3.11
3. Install dependencies (requirements.txt, requirements-dev.txt)
4. Run: pytest tests/ -v
5. Upload test results
```

### Deploy Job (if tests pass)
```
1. Checkout code
2. Set up Node.js 20
3. Set up Python 3.11
4. Install dependencies
5. Install Serverless Framework
6. Configure AWS credentials from secrets
7. Verify AWS credentials
8. Deploy via Serverless (serverless deploy --stage prod --verbose)
9. Extract deployment endpoint
10. Run smoke tests (health checks)
11. Create deployment summary
12. Upload summary artifact
13. Notify Slack (if webhook configured)
```

### Rollback Job (if deployment fails)
```
1. Checkout code
2. Install Serverless Framework
3. Configure AWS credentials
4. Execute rollback (restore previous version)
5. Notify Slack about failure
```

---

## 🔐 Required GitHub Secrets

Configure these in: Settings → Secrets and variables → Actions

**Required:**
- `AWS_ACCESS_KEY_ID` - AWS IAM Access Key
- `AWS_SECRET_ACCESS_KEY` - AWS IAM Secret Key
- `JWT_SECRET_KEY` - JWT signing key
- `MONGO_URI` - MongoDB connection string
- `CORS_ORIGIN` - Frontend origin URL

**Optional:**
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_EXPIRATION_HOURS` - Token expiration (default: 8)
- `BCRYPT_ROUNDS` - Password hashing rounds (default: 12)
- `S3_BUCKET_NAME` - S3 bucket for documents
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications

**📖 Setup Guide:** See `GITHUB_SECRETS_QUICK_SETUP.md` in repository root

---

## 📈 Monitoring Deployments

### GitHub Actions UI
```
1. Go to Actions tab
2. Click "Deploy to AWS Lambda"
3. Click the latest workflow run
4. Watch progress in real-time
5. Expand steps to see detailed logs
```

### CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/heavy-freight-platform-backend-api-prod --follow

# View API Gateway logs
aws logs tail /aws/http-api/heavy-freight-platform-backend --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/heavy-freight-platform-backend-api-prod \
  --filter-pattern "ERROR"
```

### Artifacts
```
1. Go to Actions tab
2. Click workflow run
3. Scroll to "Artifacts"
4. Download "deployment-summary" for details
```

---

## 🔧 Troubleshooting

### Workflow Fails During Tests
```
1. Check "test" job logs
2. Run tests locally: cd backend && pytest tests/ -v
3. Fix failing tests
4. Push fix to main
```

### Workflow Fails During Deployment
```
1. Check "deploy" job logs
2. Verify AWS credentials in secrets
3. Check AWS CloudFormation events
4. Review serverless.yml configuration
5. Check CloudWatch logs after deployment
```

### Deployment Succeeds but API Not Responding
```
1. Check endpoint URL in "deploy" job output
2. Wait 1-2 minutes (CloudFormation propagation)
3. Test: curl https://{endpoint}/health/live
4. Check CloudWatch logs for errors
```

### Secrets Not Found
```
1. Go to Settings → Secrets and variables → Actions
2. Verify secret names match exactly (case-sensitive)
3. Re-add secrets if needed
4. Wait 30 seconds for changes to propagate
```

---

## 📋 Workflow Configuration Details

### Test Job
```yaml
runs-on: ubuntu-latest
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v4 (python 3.11)
  - run: pip install -r backend/requirements.txt
  - run: pip install -r backend/requirements-dev.txt
  - run: cd backend && pytest tests/ -v
```

### Deploy Job
```yaml
runs-on: ubuntu-latest
needs: test (only runs if test passes)
environment: production (requires approval if configured)
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-node@v4 (node 20)
  - uses: actions/setup-python@v4 (python 3.11)
  - uses: aws-actions/configure-aws-credentials@v4
  - run: serverless deploy --stage prod --verbose
```

---

## 🔄 Rollback

### Automatic Rollback
```
If deployment fails, the workflow automatically:
1. Detects failure
2. Runs rollback job
3. Restores previous version
4. Notifies Slack (if configured)
```

### Manual Rollback
```bash
cd backend
serverless rollback --stage prod --verbose
```

---

## 📊 Performance Metrics

**Typical Deployment Time:**
- Test job: ~1-2 minutes
- Deploy job: ~2-3 minutes
- Smoke tests: ~30 seconds
- **Total:** ~3-5 minutes

**Resource Usage:**
- Ubuntu runner (GitHub hosted)
- ~2GB memory
- ~2 vCPU
- Minimal cost (included in GitHub Actions free tier)

---

## 🎯 Best Practices

1. **Always write tests** - Prevent regressions
2. **Test locally first** - Before pushing to main
3. **Review PRs** - Use branch protection on main
4. **Monitor after deploy** - Check logs and metrics
5. **Rotate secrets** - Every 90 days
6. **Set CloudWatch alarms** - Alert on errors
7. **Use descriptive commits** - Reference issues/tickets

---

## 📞 Common Commands

```bash
# View workflow runs
gh run list -w deploy.yml

# View specific run details
gh run view [RUN_ID]

# View job logs
gh run view [RUN_ID] --log

# Cancel running workflow
gh run cancel [RUN_ID]

# List all secrets
gh secret list

# Set a secret
gh secret set AWS_ACCESS_KEY_ID --body "AKIA..."

# Delete a secret
gh secret delete AWS_ACCESS_KEY_ID
```

---

## 📚 Related Documentation

- **DEPLOYMENT.md** - Full deployment guide with troubleshooting
- **GITHUB_SECRETS_QUICK_SETUP.md** - Quick secrets configuration
- **backend/README_MIGRATION.md** - API Gateway migration details
- **backend/HTTP_API_DEPLOYMENT_CHECKLIST.txt** - Pre-deployment checklist

---

## ✅ Sign-Off

Workflow is production-ready and has been tested with:
- ✅ Successful test execution
- ✅ Successful deployment to Lambda
- ✅ Successful smoke tests
- ✅ Successful rollback capability
- ✅ CloudWatch logging working
- ✅ Slack notifications (if configured)

**Status**: Ready for production CI/CD

---

**Last Updated:** May 15, 2026
**Maintained By:** GitHub Copilot
**Version:** 2.0 (REST API → HTTP API v2 migration)
