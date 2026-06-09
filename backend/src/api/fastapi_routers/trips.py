"""Trips CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional

from src.api.fastapi_routers.dependencies import get_db, get_current_user, to_frontend, from_frontend
from src.services.trip_service import TripService, TripError, TripNotFoundError, TripValidationError
from src.schemas.trip import TripCreate
from src.repositories.trip_status_repository import TripStatusRepository

router = APIRouter()

# English internal codes → Spanish display names
_STATUS_EN_TO_ES = {
    "scheduled":  "Programado",
    "in_transit": "En Tránsito",
    "delivered":  "Entregado",
    "cancelled":  "Cancelado",
}


def _build_status_lookup(db) -> dict:
    """Return {str(status_id): display_name} for all trip statuses."""
    try:
        statuses = TripStatusRepository(db).find_many({}, limit=200, skip=0)
        result = {}
        for s in statuses:
            sid = str(s.get("_id", ""))
            code = s.get("code", "")
            # Prefer Spanish translation for known English codes; fall back to DB name
            name = _STATUS_EN_TO_ES.get(code) or s.get("name") or code
            if sid:
                result[sid] = name
        return result
    except Exception:
        return {}


def _enrich(trip_doc: dict, lookup: dict) -> dict:
    """Set trip_doc['status'] from status_id lookup (so to_frontend reads it)."""
    sid = str(trip_doc.get("status_id", ""))
    if sid and sid in lookup:
        trip_doc["status"] = lookup[sid]
    return trip_doc


def _svc(db) -> TripService:
    return TripService(db)


@router.get("", status_code=200)
async def list_trips(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
    estado: Optional[str] = Query(None),
    without_fulfillment: Optional[bool] = Query(None),  # Angular filter — accepted but not yet used
    search: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    items = svc.list_trips(limit=limit, skip=skip)
    lookup = _build_status_lookup(db)
    return {"items": [to_frontend("trips", _enrich(t, lookup)) for t in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_trip(
    body: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    user_id = user.get("user_id") or user.get("sub", "system")
    try:
        translated = from_frontend("trips", body)
        data = TripCreate(**translated)
        item = svc.create_trip(data.model_dump(), user_id=user_id)
        lookup = _build_status_lookup(db)
        return to_frontend("trips", _enrich(item, lookup))
    except TripValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TripError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{trip_id}", status_code=200)
async def get_trip(
    trip_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_trip(trip_id)
        lookup = _build_status_lookup(db)
        return to_frontend("trips", _enrich(item, lookup))
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


async def _do_update_trip_status(trip_id: str, data: dict, db, user):
    svc = _svc(db)
    user_id = user.get("user_id") or user.get("sub", "system")
    # Accept status_code, status, or estado (Spanish field used by Angular TripService)
    # Normalize to lowercase snake_case to match trip_statuses.code (e.g. "En Ruta" -> "en_ruta")
    raw = data.get("status_code") or data.get("status") or data.get("estado") or ""
    status_code = raw.lower().replace(" ", "_").replace("-", "_") if raw else None
    if not status_code:
        raise HTTPException(status_code=422, detail="status_code is required")
    try:
        item = svc.update_trip_status(trip_id, status_code, user_id)
        lookup = _build_status_lookup(db)
        return to_frontend("trips", _enrich(item, lookup))
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TripError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{trip_id}/status", status_code=200)
async def update_trip_status(
    trip_id: str,
    data: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    return await _do_update_trip_status(trip_id, data, db, user)


@router.patch("/{trip_id}/status", status_code=200)
async def update_trip_status_patch(
    trip_id: str,
    data: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    return await _do_update_trip_status(trip_id, data, db, user)


@router.delete("/{trip_id}", status_code=204)
async def delete_trip(
    trip_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    user_id = user.get("user_id") or user.get("sub", "system")
    try:
        svc.delete_trip(trip_id, user_id)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TripError as e:
        raise HTTPException(status_code=400, detail=str(e))
