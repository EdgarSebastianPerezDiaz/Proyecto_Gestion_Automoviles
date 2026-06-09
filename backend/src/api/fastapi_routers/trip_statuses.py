"""Trip statuses CRUD router — uses repository directly (service uses code/label, schema uses name)."""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from bson import ObjectId

from src.api.fastapi_routers.dependencies import get_db, get_current_user, serialize_doc
from src.repositories.trip_status_repository import TripStatusRepository
from src.schemas.trip_status import TripStatusCreate, TripStatusUpdate

router = APIRouter()


def _repo(db) -> TripStatusRepository:
    return TripStatusRepository(db)


@router.get("", status_code=200)
async def list_statuses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    items = repo.find_all(skip=skip, limit=limit)
    return {"items": [serialize_doc(i) for i in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_status(
    data: TripStatusCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    # Check duplicate name
    existing = repo.find_one({"name": data.name})
    if existing:
        raise HTTPException(status_code=409, detail=f"Trip status '{data.name}' already exists")
    doc = {
        "name": data.name,
        "description": data.description,
        "sequence_order": data.sequence_order,
        "is_terminal": data.is_terminal,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    inserted_id = repo.insert_one(doc)
    doc["_id"] = inserted_id
    return serialize_doc(doc)


@router.get("/{status_id}", status_code=200)
async def get_status(
    status_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    item = repo.find_by_id(status_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Trip status {status_id} not found")
    return serialize_doc(item)


@router.put("/{status_id}", status_code=200)
async def update_status(
    status_id: str,
    data: TripStatusUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    if repo.find_by_id(status_id) is None:
        raise HTTPException(status_code=404, detail=f"Trip status {status_id} not found")
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    update_fields["updated_at"] = datetime.now(timezone.utc)
    repo.update_one({"_id": ObjectId(status_id)}, {"$set": update_fields})
    return serialize_doc(repo.find_by_id(status_id))


@router.delete("/{status_id}", status_code=204)
async def delete_status(
    status_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    if repo.find_by_id(status_id) is None:
        raise HTTPException(status_code=404, detail=f"Trip status {status_id} not found")
    repo.delete_by_id(status_id)
