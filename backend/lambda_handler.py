"""
Lambda Handler - FastAPI with Mangum Adapter
Entry point for AWS Lambda with HTTP API v2
"""

from mangum import Mangum
from main import app

# lifespan="auto" runs FastAPI startup/shutdown events inside Lambda.
handler = Mangum(app, lifespan="auto")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
