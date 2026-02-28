from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app import crud, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ResumeVersionResponse])
def read_resumes(
    db: Client = Depends(get_supabase),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve resume versions."""
    return crud.resume_version.get_multi(db, skip=skip, limit=limit)


@router.post("/", response_model=schemas.ResumeVersionResponse)
def create_resume(
    *,
    db: Client = Depends(get_supabase),
    resume_in: schemas.ResumeVersionCreate,
) -> Any:
    """Create new resume version."""
    return crud.resume_version.create(db=db, data=resume_in.model_dump())


@router.get("/{id}", response_model=schemas.ResumeVersionResponse)
def read_resume(
    *,
    db: Client = Depends(get_supabase),
    id: str,
) -> Any:
    """Get resume by ID."""
    resume = crud.resume_version.get(db, id=id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume version not found")
    return resume


@router.put("/{id}", response_model=schemas.ResumeVersionResponse)
def update_resume(
    *,
    db: Client = Depends(get_supabase),
    id: str,
    resume_in: schemas.ResumeVersionUpdate,
) -> Any:
    """Update a resume version."""
    existing = crud.resume_version.get(db, id=id)
    if not existing:
        raise HTTPException(status_code=404, detail="Resume version not found")
    update_data = resume_in.model_dump(exclude_unset=True)
    return crud.resume_version.update(db=db, id=id, data=update_data)
