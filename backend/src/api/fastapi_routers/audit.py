"""Audit router — exposes login_log and audit_log collections."""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timezone

from src.api.fastapi_routers.dependencies import get_db, get_current_user

router = APIRouter()


def _fmt(doc: dict) -> dict:
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


@router.get("/operations", status_code=200)
async def list_operations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
    search: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    dateFrom: Optional[str] = Query(None),
    dateTo: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    filt: dict = {}
    if accion:
        filt["action"] = {"$regex": accion, "$options": "i"}
    if search:
        filt["$or"] = [
            {"collection": {"$regex": search, "$options": "i"}},
            {"action":     {"$regex": search, "$options": "i"}},
        ]
    if dateFrom or dateTo:
        df: dict = {}
        if dateFrom:
            try: df["$gte"] = datetime.fromisoformat(dateFrom).replace(tzinfo=timezone.utc)
            except ValueError: pass
        if dateTo:
            try: df["$lte"] = datetime.fromisoformat(dateTo + "T23:59:59").replace(tzinfo=timezone.utc)
            except ValueError: pass
        if df:
            filt["timestamp"] = df
    try:
        col = db.get_collection("audit_log")
        docs = list(col.find(filt).skip(skip).limit(limit).sort("timestamp", -1))
        items = [_fmt(d) for d in docs]
        return {"items": items, "total": len(items), "skip": skip, "limit": limit}
    except Exception:
        return {"items": [], "total": 0, "skip": skip, "limit": limit}


@router.get("/logins", status_code=200)
async def list_logins(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
    search: Optional[str] = Query(None),
    dateFrom: Optional[str] = Query(None),
    dateTo: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    filt: dict = {}
    if search:
        filt["email"] = {"$regex": search, "$options": "i"}
    if dateFrom or dateTo:
        df: dict = {}
        if dateFrom:
            try: df["$gte"] = datetime.fromisoformat(dateFrom).replace(tzinfo=timezone.utc)
            except ValueError: pass
        if dateTo:
            try: df["$lte"] = datetime.fromisoformat(dateTo + "T23:59:59").replace(tzinfo=timezone.utc)
            except ValueError: pass
        if df:
            filt["timestamp"] = df
    try:
        col = db.get_collection("login_log")
        docs = list(col.find(filt).skip(skip).limit(limit).sort("timestamp", -1))
        items = [_fmt(d) for d in docs]
        return {"items": items, "total": len(items), "skip": skip, "limit": limit}
    except Exception:
        return {"items": [], "total": 0, "skip": skip, "limit": limit}
