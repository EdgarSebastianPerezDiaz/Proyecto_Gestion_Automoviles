"""Cargo types CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query

from src.api.fastapi_routers.dependencies import get_db, get_current_user, serialize_doc
from src.repositories.cargo_type_repository import CargoTypeRepository
from src.services.cargo_type_service import (
    CargoTypeService, CargoTypeAlreadyExistsError, CargoTypeNotFoundError, CargoTypeValidationError
)
from src.schemas.cargo_type import CargoTypeCreate, CargoTypeUpdate

router = APIRouter()


def _svc(db) -> CargoTypeService:
    return CargoTypeService(CargoTypeRepository(db))


@router.get("", status_code=200)
async def list_cargo_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    items = svc.list_active_cargo_types(skip=skip, limit=limit)
    return {"items": [serialize_doc(i) for i in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_cargo_type(
    data: CargoTypeCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.create_cargo_type(data.model_dump())
        return serialize_doc(item)
    except CargoTypeAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CargoTypeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{cargo_id}", status_code=200)
async def get_cargo_type(
    cargo_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_cargo_type(cargo_id)
        return serialize_doc(item)
    except CargoTypeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{cargo_id}", status_code=200)
async def update_cargo_type(
    cargo_id: str,
    data: CargoTypeUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.update_cargo_type(cargo_id, data.model_dump(exclude_none=True))
        return serialize_doc(item)
    except CargoTypeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CargoTypeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{cargo_id}", status_code=204)
async def delete_cargo_type(
    cargo_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        svc.delete_cargo_type(cargo_id)
    except CargoTypeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
