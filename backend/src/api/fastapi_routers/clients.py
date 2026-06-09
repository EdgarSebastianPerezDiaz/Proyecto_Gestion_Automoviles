"""Clients CRUD router — uses repository directly (service expects nit-based schema)."""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional
from datetime import datetime, timezone
import uuid

from src.api.fastapi_routers.dependencies import get_db, get_current_user, to_frontend, from_frontend
from src.repositories.client_repository import ClientRepository
from src.schemas.client import ClientCreate, ClientUpdate

router = APIRouter()


def _repo(db) -> ClientRepository:
    return ClientRepository(db)


@router.get("", status_code=200)
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    items = repo.find_active(skip=skip, limit=limit)
    return {"items": [to_frontend("clients", c) for c in items], "total": len(items), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_client(
    body: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    translated = from_frontend("clients", body)
    translated.setdefault("city", "Colombia")
    try:
        data = ClientCreate(**translated)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    email = data.email.lower().strip()
    if repo.find_by_email(email):
        raise HTTPException(status_code=409, detail=f"Client with email {email} already exists")
    doc = {
        **data.model_dump(),
        "email": email,
        "nit": f"GEN{uuid.uuid4().hex[:9].upper()}",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    inserted_id = repo.insert_one(doc)
    doc["_id"] = inserted_id
    return to_frontend("clients", doc)


@router.get("/{client_id}", status_code=200)
async def get_client(
    client_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    item = repo.find_by_id(client_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return to_frontend("clients", item)


@router.put("/{client_id}", status_code=200)
async def update_client(
    client_id: str,
    body: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    if repo.find_by_id(client_id) is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    update_data = from_frontend("clients", body)
    update_data.pop("city", None)  # don't force city override on updates
    repo.update(client_id, update_data)
    updated = repo.find_by_id(client_id)
    return to_frontend("clients", updated)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    repo = _repo(db)
    if repo.find_by_id(client_id) is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    repo.soft_delete(client_id)
