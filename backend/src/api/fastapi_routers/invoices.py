"""Invoices router (read + payment status updates)."""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from src.api.fastapi_routers.dependencies import get_db, get_current_user, serialize_doc
from src.services.invoice_service import InvoiceService, InvoiceError, InvoiceNotFoundError

router = APIRouter()


def _svc(db) -> InvoiceService:
    return InvoiceService(db)


@router.get("", status_code=200)
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    filters = {}
    if client_id:
        filters["client_id"] = client_id
    if status:
        filters["status"] = status
    items = svc.list_invoices(filters=filters, limit=limit, skip=skip)
    return {"items": [serialize_doc(i) for i in items], "total": len(items), "skip": skip, "limit": limit}


@router.get("/{invoice_id}", status_code=200)
async def get_invoice(
    invoice_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_invoice(invoice_id)
        return serialize_doc(item)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{invoice_id}/pay", status_code=200)
async def mark_as_paid(
    invoice_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.mark_as_paid(invoice_id)
        return serialize_doc(item)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvoiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{invoice_id}/void", status_code=200)
async def void_invoice(
    invoice_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.void_invoice(invoice_id)
        return serialize_doc(item)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvoiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
