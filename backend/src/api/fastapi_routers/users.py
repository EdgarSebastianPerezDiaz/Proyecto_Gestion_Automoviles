"""Users management router."""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId

from src.api.fastapi_routers.dependencies import get_db, get_current_user
from src.repositories.user_repository import UserRepository

router = APIRouter()

_SAFE_FIELDS = {"_id", "id", "email", "full_name", "role", "is_active", "created_at", "last_login"}


def _repo(db) -> UserRepository:
    return UserRepository(db)


def _safe(doc: dict) -> dict:
    """Return user doc without password_hash."""
    out = {k: v for k, v in doc.items() if k not in ("password_hash", "password")}
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    return out


@router.get("", status_code=200)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
    search: Optional[str] = Query(None),
    rol: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    filt: dict = {}
    if rol:
        filt["role"] = rol
    if search:
        filt["$or"] = [
            {"email":     {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
        ]
    try:
        col = db.get_collection("users")
        docs = list(col.find(filt).skip(skip).limit(limit).sort("created_at", -1))
        items = [_safe(d) for d in docs]
        return {"items": items, "total": len(items), "skip": skip, "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", status_code=200)
async def get_user(
    user_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        col = db.get_collection("users")
        doc = col.find_one({"_id": ObjectId(user_id)})
        if not doc:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return _safe(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}", status_code=200)
async def update_user(
    user_id: str,
    body: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        col = db.get_collection("users")
        allowed = {"full_name", "role", "is_active"}
        update = {k: v for k, v in body.items() if k in allowed and v is not None}
        update["updated_at"] = datetime.now(timezone.utc)
        result = col.update_one({"_id": ObjectId(user_id)}, {"$set": update})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        doc = col.find_one({"_id": ObjectId(user_id)})
        return _safe(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        col = db.get_collection("users")
        result = col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
