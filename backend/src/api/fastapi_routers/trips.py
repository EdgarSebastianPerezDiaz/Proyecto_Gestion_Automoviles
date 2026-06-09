"""Trips CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional

from src.api.fastapi_routers.dependencies import get_db, get_current_user, to_frontend
from src.services.trip_service import TripService, TripError, TripNotFoundError, TripValidationError
from src.schemas.trip import TripCreate

router = APIRouter()


def _svc(db) -> TripService:
    return TripService(db)


@router.get("", status_code=200)
async def list_trips(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    items = svc.list_trips(limit=limit, skip=skip)
    return {"items": [to_frontend("trips", t) for t in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_trip(
    data: TripCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    user_id = user.get("user_id") or user.get("sub", "system")
    try:
        item = svc.create_trip(data.model_dump(), user_id=user_id)
        return to_frontend("trips", item)
    except TripValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TripError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{trip_id}", status_code=200)
async def get_trip(
    trip_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_trip(trip_id)
        return to_frontend("trips", item)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{trip_id}/status", status_code=200)
async def update_trip_status(
    trip_id: str,
    data: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    user_id = user.get("user_id") or user.get("sub", "system")
    status_code = data.get("status_code") or data.get("status")
    if not status_code:
        raise HTTPException(status_code=422, detail="status_code is required")
    try:
        item = svc.update_trip_status(trip_id, status_code, user_id)
        return to_frontend("trips", item)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TripError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
