"""Invoices router (read + payment status updates)."""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime, timezone

from src.api.fastapi_routers.dependencies import get_db, get_current_user, to_frontend
from src.services.invoice_service import InvoiceService, InvoiceError, InvoiceNotFoundError

router = APIRouter()

# Angular sends estadoPago; map to internal status values
_ESTADO_PAGO_MAP = {
    "Pendiente": "issued",
    "Pagado": "paid",
    "Anulado": "void",
    "pendiente": "issued",
    "pagado": "paid",
}


def _svc(db) -> InvoiceService:
    return InvoiceService(db)


@router.get("", status_code=200)
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    estadoPago: Optional[str] = Query(None),   # Angular alias for status
    dateFrom: Optional[str] = Query(None),      # YYYY-MM-DD date range
    dateTo: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    filters = {}
    if client_id:
        filters["client_id"] = client_id
    # status or estadoPago (Spanish alias)
    resolved_status = status or _ESTADO_PAGO_MAP.get(estadoPago or "", "")
    if resolved_status:
        filters["status"] = resolved_status
    # Date range on created_at
    if dateFrom or dateTo:
        date_filter = {}
        if dateFrom:
            try:
                date_filter["$gte"] = datetime.fromisoformat(dateFrom).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if dateTo:
            try:
                date_filter["$lte"] = datetime.fromisoformat(dateTo + "T23:59:59").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if date_filter:
            filters["created_at"] = date_filter
    items = svc.list_invoices(filters=filters, limit=limit, skip=skip)
    return {"items": [to_frontend("invoices", i) for i in items], "total": len(items), "skip": skip, "limit": limit}


@router.get("/{invoice_id}", status_code=200)
async def get_invoice(
    invoice_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        item = svc.get_invoice(invoice_id)
        return to_frontend("invoices", item)
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
        return to_frontend("invoices", item)
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
        return to_frontend("invoices", item)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvoiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
