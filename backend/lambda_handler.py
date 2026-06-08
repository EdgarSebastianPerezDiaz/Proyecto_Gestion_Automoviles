"""
Lambda Handler - FastAPI with Mangum Adapter
Entry point for AWS Lambda with HTTP API v2
"""

import json
import traceback

_init_error = None
_mangum_handler = None

try:
    from mangum import Mangum
    from main import app
    _mangum_handler = Mangum(app, lifespan="auto")
except Exception as _e:
    _init_error = {
        "init_error": type(_e).__name__,
        "message": str(_e),
        "traceback": traceback.format_exc(),
    }


def handler(event, context):
    # If module-level import failed, expose the real error
    if _init_error is not None:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(_init_error),
        }
    try:
        return _mangum_handler(event, context)
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "handler_error": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }),
        }


if __name__ == "__main__":
    import uvicorn
    from main import app as _app
    uvicorn.run(_app, host="0.0.0.0", port=8000)
