"""
Lambda Handler - FastAPI with Mangum Adapter
Entry point for AWS Lambda with HTTP API v2

This replaces serverless-wsgi with Mangum for FastAPI compatibility.
"""

from mangum import Mangum
from main import app

# lifespan="auto" lets FastAPI run startup/shutdown properly.
# The startup lifespan catches MongoDB failures gracefully when FLASK_ENV != 'production'.
handler = Mangum(app, lifespan="auto")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
