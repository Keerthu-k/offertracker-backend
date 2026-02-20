from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app import crud, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.CompanyResponse])
async def read_companies(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve companies."""
    companies = await crud.company.get_multi(db, skip=skip, limit=limit)
    return companies

@router.post("/", response_model=schemas.CompanyResponse)
async def create_company(
    *,
    db: AsyncSession = Depends(get_db),
    company_in: schemas.CompanyCreate,
) -> Any:
    """Create new company."""
    company = await crud.company.create(db=db, obj_in=company_in)
    return company

@router.get("/{id}", response_model=schemas.CompanyResponse)
async def read_company(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
) -> Any:
    """Get company by ID."""
    company = await crud.company.get(db=db, id=id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.put("/{id}", response_model=schemas.CompanyResponse)
async def update_company(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    company_in: schemas.CompanyUpdate,
) -> Any:
    """Update a company."""
    company = await crud.company.get(db=db, id=id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company = await crud.company.update(db=db, db_obj=company, obj_in=company_in)
    return company
