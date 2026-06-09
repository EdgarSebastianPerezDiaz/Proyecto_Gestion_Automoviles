"""Trip statuses CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query

from src.api.fastapi_routers.dependencies import get_db, get_current_user, serialize_doc
from src.repositories.trip_status_repository import TripStatusRepository
from src.services.trip_status_service import (
    TripStatusService, TripStatusAlreadyExistsError,
    TripStatusNotFoundError, TripStatusValidationError, TripStatusInUseError
)
from src.schemas.trip_status import TripStatusCreate, TripStatusUpdate

router = APIRouter()


def _svc(db) -> TripStatusService:
    return TripStatusService(TripStatusRepository(db))


@router.get("", status_code=200)
async def list_statuses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    items = svc.list_all_statuses(skip=skip, limit=limit)
    return {"items": [serialize_doc(i) for i in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_status(
    data: TripStatusCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.create_trip_status(data.model_dump())
        return serialize_doc(item)
    except TripStatusAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except TripStatusValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{status_id}", status_code=200)
async def get_status(
    status_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_trip_status(status_id)
        return serialize_doc(item)
    except TripStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{status_id}", status_code=200)
async def update_status(
    status_id: str,
    data: TripStatusUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.update_trip_status(status_id, data.model_dump(exclude_none=True))
        return serialize_doc(item)
    except TripStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TripStatusValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{status_id}", status_code=204)
async def delete_status(
    status_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        svc.delete_trip_status(status_id)
    except TripStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TripStatusInUseError as e:
        raise HTTPException(status_code=409, detail=str(e))
