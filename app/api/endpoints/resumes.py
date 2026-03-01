from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
from app import crud, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ResumeVersionResponse])
def read_resumes(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve current user's resume versions."""
    try:
        return crud.resume_version.get_multi_by_field(
            db, field="user_id", value=current_user["id"], skip=skip, limit=limit
        )
    except DatabaseError as exc:
        logger.error("Failed to list resumes for user %s: %s", current_user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to load resumes")


@router.post("/", response_model=schemas.ResumeVersionResponse)
def create_resume(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    resume_in: schemas.ResumeVersionCreate,
) -> Any:
    """Create new resume version."""
    data = resume_in.model_dump()
    data["user_id"] = current_user["id"]
    try:
        return crud.resume_version.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to create resume: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create resume")


@router.get("/{id}", response_model=schemas.ResumeVersionResponse)
def read_resume(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
) -> Any:
    """Get resume by ID."""
    try:
        resume = crud.resume_version.get(db, id=id)
    except DatabaseError as exc:
        logger.error("Failed to fetch resume %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch resume")
    if not resume:
        raise HTTPException(status_code=404, detail="Resume version not found")
    if resume.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your resume")
    return resume


@router.put("/{id}", response_model=schemas.ResumeVersionResponse)
def update_resume(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    resume_in: schemas.ResumeVersionUpdate,
) -> Any:
    """Update a resume version."""
    try:
        existing = crud.resume_version.get(db, id=id)
    except DatabaseError as exc:
        logger.error("Failed to fetch resume %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch resume")
    if not existing:
        raise HTTPException(status_code=404, detail="Resume version not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your resume")
    update_data = resume_in.model_dump(exclude_unset=True)
    try:
        return crud.resume_version.update(db=db, id=id, data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update resume %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to update resume")


@router.delete("/{id}")
def delete_resume(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
) -> Any:
    """Delete a resume version."""
    try:
        existing = crud.resume_version.get(db, id=id)
    except DatabaseError as exc:
        logger.error("Failed to fetch resume %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch resume")
    if not existing:
        raise HTTPException(status_code=404, detail="Resume version not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your resume")
    try:
        crud.resume_version.remove(db=db, id=id)
    except DatabaseError as exc:
        logger.error("Failed to delete resume %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete resume")
    return {"detail": "Resume version deleted"}
