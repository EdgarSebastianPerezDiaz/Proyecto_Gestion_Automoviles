"""Stub routers - will be implemented fully"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter()

@router.get("", status_code=status.HTTP_200_OK)
async def list_items():
    return {"message": "Not yet implemented"}

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_item():
    raise HTTPException(status_code=501, detail="Not yet implemented")

@router.get("/{item_id}", status_code=status.HTTP_200_OK)
async def get_item(item_id: str):
    raise HTTPException(status_code=501, detail="Not yet implemented")

@router.put("/{item_id}", status_code=status.HTTP_200_OK)
async def update_item(item_id: str):
    raise HTTPException(status_code=501, detail="Not yet implemented")

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str):
    raise HTTPException(status_code=501, detail="Not yet implemented")
