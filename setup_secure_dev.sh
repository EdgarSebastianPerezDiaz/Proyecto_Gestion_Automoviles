#!/bin/bash
# Setup script for secure development environment
# Usage: bash setup_secure_dev.sh

set -e

echo \"🔐 Heavy Freight Platform - Secure Development Setup\"
echo \"=================================================\"
echo \"\"

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Check if we're in the project root
if [ ! -f \"serverless.yml\" ]; then
    echo -e \"${RED}❌ ERROR: Please run from project root directory${NC}\"
    exit 1
fi

echo -e \"${YELLOW}Step 1: Verify .env is in .gitignore${NC}\"
if grep -q '^\\.env' .gitignore 2>/dev/null; then
    echo -e \"${GREEN}✅ .env found in .gitignore${NC}\"
else
    echo -e \"${RED}❌ .env not found in .gitignore${NC}\"
    exit 1
fi

echo \"\"
echo -e \"${YELLOW}Step 2: Create development .env from template${NC}\"
if [ -f \"backend/.env\" ]; then
    echo -e \"${YELLOW}⚠️  backend/.env already exists${NC}\"
    read -p \"Overwrite it? (y/N): \" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo \"Keeping existing .env\"
    else
        cp backend/.env.example backend/.env
        echo -e \"${GREEN}✅ .env created from template${NC}\"
    fi
else
    cp backend/.env.example backend/.env
    echo -e \"${GREEN}✅ .env created from template${NC}\"
fi

echo \"\"
echo -e \"${YELLOW}Step 3: Update .env with development values${NC}\"
echo \"Edit backend/.env and update:\"
echo \"  - MONGO_URI (use development cluster)\"
echo \"  - JWT_SECRET_KEY (can be any safe value locally)\"
echo \"  - CORS_ORIGIN (http://localhost:4200)\"
echo \"  - FLASK_ENV (development)\"
echo \"\"
read -p \"Press ENTER when done editing .env...\"

echo \"\"
echo -e \"${YELLOW}Step 4: Install pre-commit hook${NC}\"
if [ ! -d \".git/hooks\" ]; then
    mkdir -p .git/hooks
fi

chmod +x backend/.git_hooks_pre-commit
cp backend/.git_hooks_pre-commit .git/hooks/pre-commit
echo -e \"${GREEN}✅ Pre-commit hook installed${NC}\"

echo \"\"
echo -e \"${YELLOW}Step 5: Run security checker${NC}\"
cd backend
python security_checker.py
SECURITY_CHECK=$?
cd ..

if [ $SECURITY_CHECK -eq 0 ]; then
    echo -e \"${GREEN}✅ No secrets detected in code${NC}\"
else
    echo -e \"${RED}❌ Secrets found! Fix them before proceeding${NC}\"
    exit 1
fi

echo \"\"
echo -e \"${YELLOW}Step 6: Verify dependencies${NC}\"
if [ ! -f \"backend/requirements.txt\" ]; then
    echo -e \"${RED}❌ backend/requirements.txt not found${NC}\"
    exit 1
fi
echo -e \"${GREEN}✅ requirements.txt found${NC}\"

echo \"\"
echo -e \"${YELLOW}Step 7: Install Python dependencies (optional)${NC}\"
read -p \"Install Python dependencies? (y/N): \" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd backend
    pip install -r requirements.txt
    echo -e \"${GREEN}✅ Dependencies installed${NC}\"
    cd ..
else
    echo \"Skipping dependency installation\"
fi

echo \"\"
echo -e \"${GREEN}✅ SETUP COMPLETE!${NC}\"
echo \"\"
echo \"Next steps:\"
echo \"1. Start development: cd backend && python -m flask run\"
echo \"2. Test auth: curl -X POST http://localhost:5000/auth/signup\"
echo \"3. Read SECURITY.md for production deployment\"
echo \"\"
echo \"⚠️  SECURITY REMINDERS:\"
echo \"  - NEVER commit backend/.env\"
echo \"  - NEVER hardcode secrets in code\"
echo \"  - ALWAYS use environment variables\"
echo \"  - Check pre-commit hook prevents secret commits\"
echo \"\"
