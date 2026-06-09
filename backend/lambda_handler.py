"""
Lambda Handler - FastAPI with Mangum Adapter
Entry point for AWS Lambda with HTTP API v2
"""

import traceback

try:
    from mangum import Mangum
    from main import app
    handler = Mangum(app, lifespan="auto")
    _startup_error = None
except Exception as _exc:
    # Expose import/startup errors as HTTP 500 with body so they are visible
    # in curl/smoke-test without needing CloudWatch access.
    _startup_error = (
        f"Lambda startup failed: {type(_exc).__name__}: {_exc}\n\n"
        f"{traceback.format_exc()}"
    )

    def handler(event, context):  # type: ignore[misc]
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": _startup_error,
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # type: ignore[name-defined]
