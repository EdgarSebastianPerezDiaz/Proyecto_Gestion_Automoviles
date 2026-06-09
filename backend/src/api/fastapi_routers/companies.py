"""Companies CRUD router."""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from src.api.fastapi_routers.dependencies import get_db, get_current_user, to_frontend, from_frontend
from src.repositories.company_repository import CompanyRepository
from src.services.company_service import (
    CompanyService, CompanyAlreadyExistsError, CompanyNotFoundError, CompanyValidationError
)
from src.services.audit_service import AuditService
from src.schemas.company import CompanyCreate

router = APIRouter()


def _svc(db) -> CompanyService:
    audit = AuditService(db)
    return CompanyService(CompanyRepository(db), audit)


@router.get("", status_code=200)
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    companies = svc.list_companies(skip=skip, limit=limit)
    return {"items": [to_frontend("companies", c) for c in companies], "total": len(companies), "skip": skip, "limit": limit}


@router.post("", status_code=201)
async def create_company(
    body: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    translated = from_frontend("companies", body)
    translated.setdefault("city", "Colombia")
    try:
        data = CompanyCreate(**translated)
        company = svc.create_company(data.model_dump())
        return to_frontend("companies", company)
    except CompanyAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CompanyValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{company_id}", status_code=200)
async def get_company(
    company_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        company = svc.get_company(company_id)
        return to_frontend("companies", company)
    except CompanyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{company_id}", status_code=200)
async def update_company(
    company_id: str,
    data: dict = Body(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        translated = from_frontend("companies", data)
        translated.pop("city", None)  # don't force city override on updates
        company = svc.update_company(company_id, translated)
        return to_frontend("companies", company)
    except CompanyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CompanyValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    svc = _svc(db)
    try:
        svc.delete_company(company_id)
    except CompanyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
