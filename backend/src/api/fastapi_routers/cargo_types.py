"""Cargo types CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from bson import ObjectId

from src.api.fastapi_routers.dependencies import get_db, get_current_user, serialize_doc
from src.repositories.cargo_type_repository import CargoTypeRepository
from src.services.cargo_type_service import (
    CargoTypeService, CargoTypeAlreadyExistsError, CargoTypeNotFoundError, CargoTypeValidationError
)
from src.schemas.cargo_type import CargoTypeCreate, CargoTypeUpdate

router = APIRouter()


def _svc(db) -> CargoTypeService:
    return CargoTypeService(CargoTypeRepository(db))


def _repo(db) -> CargoTypeRepository:
    return CargoTypeRepository(db)


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
        result = svc.create_cargo_type(data.model_dump())
        # Service returns the inserted ID (str), not the full document
        if isinstance(result, str):
            item = svc.get_cargo_type(result)
        else:
            item = result
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
    # Bypass service — CargoTypeRepository lacks update()/soft_delete()
    repo = _repo(db)
    if repo.find_by_id(cargo_id) is None:
        raise HTTPException(status_code=404, detail=f"Cargo type {cargo_id} not found")
    update_fields = data.model_dump(exclude_none=True)
    update_fields["updated_at"] = datetime.now(timezone.utc)
    try:
        repo.update_one({"_id": ObjectId(cargo_id)}, {"$set": update_fields})
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid cargo type data")
    return serialize_doc(repo.find_by_id(cargo_id))


@router.delete("/{cargo_id}", status_code=204)
async def delete_cargo_type(
    cargo_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    # Bypass service — CargoTypeRepository lacks soft_delete()
    repo = _repo(db)
    if repo.find_by_id(cargo_id) is None:
        raise HTTPException(status_code=404, detail=f"Cargo type {cargo_id} not found")
    repo.update_one(
        {"_id": ObjectId(cargo_id)},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
