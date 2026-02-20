from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app import crud, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.ResumeVersionResponse])
async def read_resumes(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve resume versions."""
    resumes = await crud.resume_version.get_multi(db, skip=skip, limit=limit)
    return resumes

@router.post("/", response_model=schemas.ResumeVersionResponse)
async def create_resume(
    *,
    db: AsyncSession = Depends(get_db),
    resume_in: schemas.ResumeVersionCreate,
) -> Any:
    """Create new resume version."""
    resume = await crud.resume_version.create(db=db, obj_in=resume_in)
    return resume

@router.get("/{id}", response_model=schemas.ResumeVersionResponse)
async def read_resume(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
) -> Any:
    """Get resume by ID."""
    resume = await crud.resume_version.get(db=db, id=id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume version not found")
    return resume

@router.put("/{id}", response_model=schemas.ResumeVersionResponse)
async def update_resume(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    resume_in: schemas.ResumeVersionUpdate,
) -> Any:
    """Update a resume version."""
    resume = await crud.resume_version.get(db=db, id=id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume version not found")
    resume = await crud.resume_version.update(db=db, db_obj=resume, obj_in=resume_in)
    return resume
