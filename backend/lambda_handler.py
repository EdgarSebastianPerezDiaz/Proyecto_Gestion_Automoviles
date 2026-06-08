"""
Lambda Handler - FastAPI with Mangum Adapter
Entry point for AWS Lambda with HTTP API v2

This replaces serverless-wsgi with Mangum for FastAPI compatibility.
"""

from mangum import Mangum
from main import app

# Create Lambda handler
handler = Mangum(app, lifespan="off")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
