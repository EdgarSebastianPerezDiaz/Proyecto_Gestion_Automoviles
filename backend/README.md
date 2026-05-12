# Heavy Freight Platform - Backend

Serverless Flask API for freight transport management and logistics optimization.

## Project Architecture

```
backend/
├── src/
│   ├── api/              # Flask blueprints and route handlers
│   ├── domain/           # Business logic and domain models
│   ├── repositories/     # Data access layer (MongoDB)
│   ├── services/         # Business logic and orchestration
│   └── infrastructure/   # Configuration, utilities, external service integrations
├── tests/                # Test suite
├── wsgi.py              # Flask application entry point (Lambda handler)
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Development and testing dependencies
├── .env.example         # Environment variables template
└── .gitignore          # Git ignore patterns
```

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- MongoDB (local or MongoDB Atlas)

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (macOS/Linux)
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (includes production)
pip install -r requirements-dev.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# ⚠️ IMPORTANT: Do NOT commit .env to version control
nano .env  # or your preferred editor
```

**Required configurations:**
- `MONGO_URI`: Your MongoDB connection string
- `JWT_SECRET_KEY`: Generate a strong random key for production

**Generate a strong JWT secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Run Local Development Server

```bash
# Set Flask to development mode
export FLASK_ENV=development  # macOS/Linux
set FLASK_ENV=development     # Windows

# Run the development server
python -m flask --app wsgi run
```

The server will start at `http://localhost:5000`

### 5. Verify Health Endpoint

```bash
curl http://localhost:5000/health
# Expected response: {"message": "ok"}
```

### 6. Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

### 7. Code Quality Checks

```bash
# Format code with Black
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Security scan with Bandit
bandit -r src/
```

## Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `MONGO_URI` | ✓ | - | MongoDB connection string |
| `JWT_SECRET_KEY` | ✓ | - | Secret key for JWT token generation |
| `JWT_ALGORITHM` | ✗ | HS256 | JWT signing algorithm |
| `JWT_EXPIRATION_HOURS` | ✗ | 8 | JWT token expiration time |
| `BCRYPT_ROUNDS` | ✗ | 12 | bcrypt cost factor (8-12 recommended) |
| `CORS_ORIGIN` | ✗ | http://localhost:4200 | Allowed CORS origin |
| `FLASK_ENV` | ✗ | development | Flask environment |
| `AWS_REGION` | ✗ | us-east-1 | AWS region for Lambda deployment |

## Security Notes

### Secrets Management
- Never hardcode secrets in code
- Use environment variables for all sensitive configuration
- Use `.env` for local development only (add to `.gitignore`)
- For production, use AWS Secrets Manager or similar services

### Authentication & Authorization
- JWT tokens with configurable expiration
- bcrypt for password hashing (salted and iterative)
- CORS protection with configurable allowed origins

### Production Deployment
- Enable HTTPS/TLS for all connections
- Use strong, randomly generated `JWT_SECRET_KEY`
- Configure MongoDB authentication credentials
- Use least privilege IAM roles for Lambda execution

## 🚀 Deployment to AWS Lambda

> **⚡ Quick Start**: New to deployment? Read [`DEPLOY_QUICK_START.md`](DEPLOY_QUICK_START.md) first (5 min)

### Complete Deployment Guide

For detailed, step-by-step deployment instructions, see:

- **[`DEPLOY_QUICK_START.md`](DEPLOY_QUICK_START.md)** - 5-minute quick reference
- **[`DEPLOYMENT.md`](DEPLOYMENT.md)** - Complete deployment guide (AWS setup, IAM, Secrets Manager, troubleshooting)
- **[`DEPLOY_CHECKLIST.md`](DEPLOY_CHECKLIST.md)** - Pre-deployment checklist

### Prerequisites for Deployment

1. **AWS Account** with appropriate permissions
2. **Node.js 18+** (required for Serverless Framework)
3. **AWS CLI** configured locally
4. **Serverless Framework** installed globally
5. **AWS Secrets Manager** secrets configured
6. **MongoDB Atlas** cluster ready with credentials

### Local Deployment Setup (TL;DR)

```bash
# Install tools
npm install -g serverless
npm install serverless-python-requirements serverless-wsgi

# Configure AWS
aws configure
# Enter: Access Key, Secret Key, region (us-east-1), format (json)

# Create secrets
aws secretsmanager create-secret --name heavy-freight/production/JWT_SECRET_KEY --secret-string "..."
aws secretsmanager create-secret --name heavy-freight/production/MONGO_URI --secret-string "..."

# Deploy
cd backend
serverless deploy --stage production --region us-east-1

# Verify
curl https://your-api.execute-api.us-east-1.amazonaws.com/health
```

**⚠️ IMPORTANT SECURITY**: 
- Never commit AWS credentials or secrets to version control
- Use AWS Secrets Manager for production secrets
- Use `aws configure` or environment variables for AWS credentials
- All sensitive data must be stored in AWS Secrets Manager, NOT in code

#### 4. Set Production Environment Variables

Create a production `.env` file or use AWS Secrets Manager:

```bash
# Copy and populate the production configuration
cp .env.example .env.production

# Required variables for production:
FLASK_ENV=production
MONGO_URI=mongodb+srv://[username]:[password]@[cluster].mongodb.net/[database]
JWT_SECRET_KEY=[generate-a-strong-random-key]
CORS_ORIGIN=https://yourdomain.com
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=8
```

**⚠️ IMPORTANT**: For AWS Lambda deployment, use AWS SSM Parameter Store instead of `.env` files.

See **[AWS_SSM_SETUP.md](./AWS_SSM_SETUP.md)** for detailed instructions on setting up SSM Parameter Store.

**Generate a strong JWT secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Manual Deployment to AWS

#### Development Stage

```bash
# Deploy to development stage
serverless deploy --stage dev --region us-east-1 --verbose

# Output will show your Lambda endpoint URL
```

#### Production Stage

```bash
# Deploy to production stage
serverless deploy --stage prod --region us-east-1 --verbose

# Environment variables must be set as AWS Lambda environment variables
# or in AWS Secrets Manager
```

#### Remove Deployment

```bash
# Remove a deployed stack
serverless remove --stage dev

# or remove production
serverless remove --stage prod
```

### Automated Deployment with GitHub Actions

This project includes a CI/CD pipeline (`.github/workflows/deploy.yml`) that automatically:
1. Runs tests on every push to `main`
2. Deploys to AWS Lambda if tests pass

#### Setup GitHub Secrets

Navigate to **Settings > Secrets and variables > Actions** and create the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | Your AWS Access Key ID | AWS credentials for deployment |
| `AWS_SECRET_ACCESS_KEY` | Your AWS Secret Access Key | AWS credentials for deployment |
| `JWT_SECRET_KEY` | Strong random key (32+ chars) | JWT signing secret for production |
| `MONGO_URI` | MongoDB connection string | MongoDB Atlas or self-hosted |
| `CORS_ORIGIN` | Your frontend domain | e.g., https://yourdomain.com |

**Generate secure secret values:**
```bash
# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate another random key  
python -c "import secrets; print(secrets.token_hex(32))"
```

#### CI/CD Pipeline Steps

1. **Trigger (on push to main)**
   ```yaml
   on:
     push:
       branches: [main]
   ```

2. **Test Stage** - Runs pytest with mongomock
   - Installs dependencies
   - Runs linting (flake8)
   - Executes test suite
   - Uploads coverage to Codecov

3. **Deploy Stage** - Deploys to AWS (only if tests pass)
   - Configures AWS credentials from GitHub secrets
   - Installs Serverless Framework
   - Deploys to AWS Lambda production stage
   - Sets production environment variables

#### Monitoring Deployment

```bash
# View Lambda function logs
serverless logs --function handle_request --stage prod --tail

# View all metrics
serverless metrics --stage prod

# Get function info
serverless info --stage prod
```

### Environment Variable Validation

The application validates environment variables at startup:

**Testing/Development Mode:**
- Uses dummy values if environment variables are missing
- Allows quick local development

**Production Mode:**
- Validates ALL critical variables (`MONGO_URI`, `JWT_SECRET_KEY`)
- Fails fast if variables are missing
- Application will NOT start in production without proper configuration

See `wsgi.py::validate_env_vars()` for validation logic.

### Troubleshooting

#### "Missing critical environment variables" Error

**Solution**: Ensure all required variables are set:
```bash
# Check current environment
env | grep -E "MONGO_URI|JWT_SECRET_KEY|FLASK_ENV"

# Set missing variables
export MONGO_URI="your_mongodb_uri"
export JWT_SECRET_KEY="your_secret_key"
```

#### "Unable to import" or "Permission denied" (on Lambda)

**Solution**: Ensure IAM role for Lambda execution has permissions:
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
- `ec2:CreateNetworkInterface` (if accessing private MongoDB)
- `secretsmanager:GetSecretValue` (if using Secrets Manager)

#### Serverless Deploy Fails

**Solution**: Verify AWS credentials:
```bash
aws sts get-caller-identity

# Should return your AWS account info
# If error: check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
```

#### Tests Fail Locally but Not in CI

**Solution**: Ensure MongoDB is accessible or mongomock is installed:
```bash
pip install mongomock
python -m pytest --tb=short
```

## Production Deployment Checklist

- [ ] AWS account created and configured
- [ ] AWS credentials securely stored (not in repository)
- [ ] GitHub secrets created (AWS keys, JWT secret, MongoDB URI, CORS origin)
- [ ] `serverless.yml` configured correctly
- [ ] All tests passing locally (`pytest`)
- [ ] Environment variables validated (`validate_env_vars()`)
- [ ] Security headers configured in `src/infrastructure/security_headers.py`
- [ ] CORS origins properly configured
- [ ] MongoDB connection string is for production database
- [ ] Logging configured for CloudWatch
- [ ] Rate limiting configured
- [ ] API documentation updated
- [ ] Monitoring and alerting configured in AWS CloudWatch

## Development Roadmap

- [ ] Authentication module (JWT, login/register)
- [ ] User management and authorization
- [ ] Shipment CRUD operations
- [ ] Driver and vehicle management
- [ ] Route planning and optimization
- [ ] Real-time tracking
- [ ] PDF report generation
- [ ] Notification system
- [ ] Integration tests
- [ ] Database migrations

## Contributing

1. Create a feature branch
2. Make changes and add tests
3. Run quality checks (`black`, `flake8`, `bandit`)
4. Ensure all tests pass
5. Submit pull request

## License

Proprietary - Heavy Freight Platform
