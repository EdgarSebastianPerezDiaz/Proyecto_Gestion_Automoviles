"""Final recipients CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query

from src.api.fastapi_routers.dependencies import get_db, get_current_user, serialize_doc
from src.repositories.final_recipient_repository import FinalRecipientRepository
from src.services.final_recipient_service import (
    FinalRecipientService, FinalRecipientAlreadyExistsError,
    FinalRecipientNotFoundError, FinalRecipientValidationError
)
from src.schemas.final_recipient import FinalRecipientCreate, FinalRecipientUpdate

router = APIRouter()


def _svc(db) -> FinalRecipientService:
    return FinalRecipientService(FinalRecipientRepository(db))


@router.get("", status_code=200)
async def list_recipients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    items = svc.list_recipients(skip=skip, limit=limit)
    return {"items": [serialize_doc(i) for i in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_recipient(
    data: FinalRecipientCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.create_recipient(data.model_dump())
        return serialize_doc(item)
    except FinalRecipientAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except FinalRecipientValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{recipient_id}", status_code=200)
async def get_recipient(
    recipient_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_recipient(recipient_id)
        return serialize_doc(item)
    except FinalRecipientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{recipient_id}", status_code=200)
async def update_recipient(
    recipient_id: str,
    data: FinalRecipientUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.update_recipient(recipient_id, data.model_dump(exclude_none=True))
        return serialize_doc(item)
    except FinalRecipientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FinalRecipientValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{recipient_id}", status_code=204)
async def delete_recipient(
    recipient_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        svc.delete_recipient(recipient_id)
    except FinalRecipientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
