"""Drivers CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional

from src.api.fastapi_routers.dependencies import get_db, get_current_user, to_frontend, from_frontend
from src.repositories.driver_repository import DriverRepository
from src.services.driver_service import (
    DriverService, DriverAlreadyExistsError, DriverNotFoundError, DriverValidationError
)
from src.schemas.driver import DriverCreate

router = APIRouter()


def _svc(db) -> DriverService:
    return DriverService(DriverRepository(db))


@router.get("", status_code=200)
async def list_drivers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_expired: bool = Query(False),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    items = svc.list_drivers(skip=skip, limit=limit, include_expired=include_expired)
    return {"items": [to_frontend("drivers", d) for d in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_driver(
    body: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        data = DriverCreate(**from_frontend("drivers", body))
        item = svc.create_driver(data.model_dump())
        return to_frontend("drivers", item)
    except DriverAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DriverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{driver_id}", status_code=200)
async def get_driver(
    driver_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_driver(driver_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
        return to_frontend("drivers", item)
    except DriverNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{driver_id}", status_code=200)
async def update_driver(
    driver_id: str,
    data: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        translated = from_frontend("drivers", data)
        item = svc.update_driver(driver_id, translated)
        return to_frontend("drivers", item)
    except DriverNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DriverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{driver_id}", status_code=204)
async def delete_driver(
    driver_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        svc.delete_driver(driver_id)
    except DriverNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
