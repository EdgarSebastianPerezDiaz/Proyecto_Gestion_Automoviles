"""Final recipients CRUD router — uses repository directly (service/schema field mismatch)."""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from bson import ObjectId

from src.api.fastapi_routers.dependencies import get_db, get_current_user, to_frontend
from src.repositories.final_recipient_repository import FinalRecipientRepository
from src.schemas.final_recipient import FinalRecipientCreate, FinalRecipientUpdate

router = APIRouter()


def _repo(db) -> FinalRecipientRepository:
    return FinalRecipientRepository(db)


@router.get("", status_code=200)
async def list_recipients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    items = repo.find_active(skip=skip, limit=limit)
    return {"items": [to_frontend("final_recipients", i) for i in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_recipient(
    data: FinalRecipientCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    payload = data.model_dump()
    # Check email uniqueness when provided
    email = payload.get("email")
    if email:
        existing = repo.find_one({"email": email.lower(), "is_active": True})
        if existing:
            raise HTTPException(status_code=409, detail=f"Recipient with email {email} already exists")
    doc = {
        **payload,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    inserted_id = repo.insert_one(doc)
    doc["_id"] = inserted_id
    return to_frontend("final_recipients", doc)


@router.get("/{recipient_id}", status_code=200)
async def get_recipient(
    recipient_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    item = repo.find_by_id(recipient_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")
    return to_frontend("final_recipients", item)


@router.put("/{recipient_id}", status_code=200)
async def update_recipient(
    recipient_id: str,
    data: FinalRecipientUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    if repo.find_by_id(recipient_id) is None:
        raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    update_fields["updated_at"] = datetime.now(timezone.utc)
    repo.update_one({"_id": ObjectId(recipient_id)}, {"$set": update_fields})
    return to_frontend("final_recipients", repo.find_by_id(recipient_id))


@router.delete("/{recipient_id}", status_code=204)
async def delete_recipient(
    recipient_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    if repo.find_by_id(recipient_id) is None:
        raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")
    repo.update_one(
        {"_id": ObjectId(recipient_id)},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
