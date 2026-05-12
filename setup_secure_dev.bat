@echo off
REM Setup script for secure development environment (Windows)
REM Usage: setup_secure_dev.bat

setlocal enabledelayedexpansion

echo ========================================================
echo 🔐 Heavy Freight Platform - Secure Development Setup
echo ========================================================
echo.

REM Check if we're in the project root
if not exist \"serverless.yml\" (
    echo ❌ ERROR: Please run from project root directory
    pause
    exit /b 1
)

echo [Step 1] Verify .env is in .gitignore
findstr /R \"^\\.env\" .gitignore >nul 2>&1
if errorlevel 1 (
    echo ❌ .env not found in .gitignore
    pause
    exit /b 1
) else (
    echo ✅ .env found in .gitignore
)

echo.
echo [Step 2] Create development .env from template
if exist \"backend\\.env\" (
    echo ⚠️  backend\\.env already exists
    set /p overwrite=\"Overwrite it [y/N]: \"
    if /i \"!overwrite!\"==\"y\" (
        copy backend\\.env.example backend\\.env >nul
        echo ✅ .env created from template
    ) else (
        echo Keeping existing .env
    )
) else (
    copy backend\\.env.example backend\\.env >nul
    echo ✅ .env created from template
)

echo.
echo [Step 3] Update .env with development values
echo Edit backend\\.env and update:
echo   - MONGO_URI (use development cluster)
echo   - JWT_SECRET_KEY (can be any safe value locally)
echo   - CORS_ORIGIN (http://localhost:4200)
echo   - FLASK_ENV (development)
echo.
pause

echo.
echo [Step 4] Install pre-commit hook
if not exist \".git\\hooks\" mkdir .git\\hooks
copy backend\\.git_hooks_pre-commit .git\\hooks\\pre-commit >nul
echo ✅ Pre-commit hook installed

echo.
echo [Step 5] Run security checker
cd backend
python security_checker.py
set SECURITY_CHECK=%ERRORLEVEL%
cd ..

if %SECURITY_CHECK% equ 0 (
    echo ✅ No secrets detected in code
) else (
    echo ❌ Secrets found! Fix them before proceeding
    pause
    exit /b 1
)

echo.
echo [Step 6] Verify dependencies
if not exist \"backend\\requirements.txt\" (
    echo ❌ backend\\requirements.txt not found
    pause
    exit /b 1
)
echo ✅ requirements.txt found

echo.
echo [Step 7] Install Python dependencies
set /p install_deps=\"Install Python dependencies [y/N]: \"
if /i \"!install_deps!\"==\"y\" (
    cd backend
    pip install -r requirements.txt
    echo ✅ Dependencies installed
    cd ..
) else (
    echo Skipping dependency installation
)

echo.
echo ✅ SETUP COMPLETE!
echo.
echo Next steps:
echo 1. Start development: cd backend ^&^& python -m flask run
echo 2. Test auth: curl -X POST http://localhost:5000/auth/signup
echo 3. Read SECURITY.md for production deployment
echo.
echo ⚠️  SECURITY REMINDERS:
echo   - NEVER commit backend\\.env
echo   - NEVER hardcode secrets in code
echo   - ALWAYS use environment variables
echo   - Check pre-commit hook prevents secret commits
echo.

pause
