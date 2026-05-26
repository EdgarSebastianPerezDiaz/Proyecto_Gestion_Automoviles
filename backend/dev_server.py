#!/usr/bin/env python
"""
Development Server for Transport App Backend
Simplified Flask server that bypasses serverless-wsgi for local development
"""
import os
import sys
import logging

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Try to import required modules
try:
    from flask import Flask
    from flask_cors import CORS
    logger.info("Flask and Flask-CORS imported successfully")
except ImportError as e:
    logger.error(f"Missing required module: {e}")
    logger.info("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-cors", "pymongo", "pydantic", "python-jose[cryptography]"])
    from flask import Flask
    from flask_cors import CORS

# Create Flask app
app = Flask(__name__)
CORS(app, origins=[os.getenv('CORS_ORIGIN', 'http://localhost:4200')])

# Configure app
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Health check endpoint (required for all services)
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return {'message': 'ok', 'status': 'healthy'}, 200

# Simple login endpoint for testing
@app.route('/api/auth/login', methods=['POST'])
def test_login():
    """Test login endpoint - returns mock JWT token"""
    from datetime import datetime, timedelta
    import json
    from jose import jwt
    
    # Get request data
    data = request.get_json() or {}
    email = data.get('email', '')
    password = data.get('password', '')
    
    # Mock validation (any non-empty email/password works for testing)
    if email and password:
        # Determine role based on email
        role = 'admin' if 'admin' in email.lower() else 'operator'
        
        # Create mock token
        secret = os.getenv('JWT_SECRET_KEY', 'test-secret-key')
        payload = {
            'email': email,
            'role': role,
            'user_id': email,
            'full_name': email.split('@')[0].replace('.', ' ').title(),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        try:
            token = jwt.encode(payload, secret, algorithm='HS256')
            return {
                'access_token': token,
                'token_type': 'bearer',
                'user': {
                    'email': email,
                    'role': role,
                    'full_name': payload['full_name']
                }
            }, 200
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            return {'error': 'Token creation failed'}, 500
    
    return {'error': 'Invalid credentials'}, 401

# Import request for the login endpoint
from flask import request

# Dashboard endpoints (stub for testing)
@app.route('/api/admin/dashboard', methods=['GET'])
def admin_dashboard():
    """Mock admin dashboard data"""
    return {
        'kpis': [
            {'label': 'Empresas', 'value': 15, 'unit': 'activas', 'icon': '🏢', 'color': 'gold'},
            {'label': 'Conductores', 'value': 48, 'unit': 'activos', 'icon': '👨‍✈️', 'color': 'green'},
            {'label': 'Vehículos', 'value': 32, 'unit': 'disponibles', 'icon': '🚚', 'color': 'blue'},
            {'label': 'Viajes', 'value': 127, 'unit': 'totales', 'icon': '🗺️', 'color': 'orange'}
        ],
        'alerts': [
            {'severity': 'warning', 'message': 'Documentación próxima a vencer', 'timestamp': '2026-05-21T10:30:00Z'},
            {'severity': 'info', 'message': 'Viaje completado exitosamente', 'timestamp': '2026-05-21T09:15:00Z'}
        ]
    }, 200

@app.route('/api/operator/dashboard', methods=['GET'])
def operator_dashboard():
    """Mock operator dashboard data"""
    return {
        'kpis': [
            {'label': 'Viajes Activos', 'value': 5, 'unit': 'viajes', 'icon': '📊', 'color': 'gold'},
            {'label': 'Distancia', 'value': 1240, 'unit': 'km', 'icon': '📏', 'color': 'blue'},
            {'label': 'Combustible', 'value': 320, 'unit': 'L', 'icon': '⛽', 'color': 'orange'},
            {'label': 'Documentos', 'value': 8, 'unit': 'pendientes', 'icon': '📄', 'color': 'red'}
        ],
        'alerts': [
            {'severity': 'info', 'message': 'Próximo viaje en 2 horas', 'timestamp': '2026-05-21T11:00:00Z'}
        ]
    }, 200

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return {'error': 'Endpoint not found'}, 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    port = int(os.getenv('SERVER_PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting development server on http://localhost:{port}")
    logger.info(f"CORS enabled for: {os.getenv('CORS_ORIGIN', 'http://localhost:4200')}")
    
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=True)
