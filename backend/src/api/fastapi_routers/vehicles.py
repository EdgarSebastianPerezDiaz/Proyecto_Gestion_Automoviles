"""Vehicles CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from src.api.fastapi_routers.dependencies import get_db, get_current_user, serialize_doc
from src.repositories.vehicle_repository import VehicleRepository
from src.services.vehicle_service import (
    VehicleService, VehicleAlreadyExistsError, VehicleNotFoundError, VehicleValidationError
)
from src.schemas.vehicle import VehicleCreate, VehicleUpdate

router = APIRouter()


def _svc(db) -> VehicleService:
    return VehicleService(VehicleRepository(db))


@router.get("", status_code=200)
async def list_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    items = svc.list_vehicles(skip=skip, limit=limit, status_filter=status_filter)
    return {"items": [serialize_doc(v) for v in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_vehicle(
    data: VehicleCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.create_vehicle(data.model_dump())
        return serialize_doc(item)
    except VehicleAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except VehicleValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{vehicle_id}", status_code=200)
async def get_vehicle(
    vehicle_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_vehicle(vehicle_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
        return serialize_doc(item)
    except VehicleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{vehicle_id}", status_code=200)
async def update_vehicle(
    vehicle_id: str,
    data: VehicleUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.update_vehicle(vehicle_id, data.model_dump(exclude_none=True))
        return serialize_doc(item)
    except VehicleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except VehicleValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{vehicle_id}", status_code=204)
async def delete_vehicle(
    vehicle_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        svc.delete_vehicle(vehicle_id)
    except VehicleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
