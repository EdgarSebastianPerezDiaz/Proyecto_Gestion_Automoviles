"""Shared FastAPI dependencies: database access and JWT authentication."""
import os
from typing import Optional, Any
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
from jose import jwt, JWTError

_db_connection = None
_security = HTTPBearer()


def set_db(db) -> None:
    global _db_connection
    _db_connection = db


def get_db():
    if _db_connection is None:
        raise HTTPException(status_code=503, detail="Database connection not initialized")
    return _db_connection


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> dict:
    secret = os.getenv("JWT_SECRET_KEY")
    algo = os.getenv("JWT_ALGORITHM", "HS256")
    if not secret:
        raise HTTPException(status_code=503, detail="JWT_SECRET_KEY not configured")
    try:
        payload = jwt.decode(credentials.credentials, secret, algorithms=[algo])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def serialize_doc(doc: Optional[dict]) -> Optional[dict]:
    """Convert MongoDB document to JSON-serializable dict (ObjectId → str)."""
    if doc is None:
        return None
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result["id"] = str(v)
        elif hasattr(v, "__str__") and type(v).__name__ == "ObjectId":
            result[k] = str(v)
        elif isinstance(v, dict):
            result[k] = serialize_doc(v)
        elif isinstance(v, list):
            result[k] = [serialize_doc(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result
