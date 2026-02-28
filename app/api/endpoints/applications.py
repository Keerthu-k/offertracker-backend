from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app import crud, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ApplicationResponse])
def read_applications(
    db: Client = Depends(get_supabase),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve applications with nested relations."""
    return crud.application.get_multi_with_relations(db, skip=skip, limit=limit)


@router.post("/", response_model=schemas.ApplicationResponse)
def create_application(
    *,
    db: Client = Depends(get_supabase),
    application_in: schemas.ApplicationCreate,
) -> Any:
    """Create new application."""
    data = application_in.model_dump()
    if data.get("resume_version_id"):
        resume = crud.resume_version.get(db, id=data["resume_version_id"])
        if not resume:
            raise HTTPException(status_code=404, detail="Resume version not found")
    # Convert date to string for JSON serialisation
    if data.get("applied_date"):
        data["applied_date"] = str(data["applied_date"])
    row = crud.application.create(db=db, data=data)
    # Return with empty nested lists so response_model is satisfied
    row.setdefault("stages", [])
    row.setdefault("outcome", None)
    row.setdefault("reflection", None)
    return row


@router.get("/{id}", response_model=schemas.ApplicationResponse)
def read_application(
    *,
    db: Client = Depends(get_supabase),
    id: str,
) -> Any:
    """Get application by ID."""
    application = crud.application.get_with_relations(db, id=id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.put("/{id}", response_model=schemas.ApplicationResponse)
def update_application(
    *,
    db: Client = Depends(get_supabase),
    id: str,
    application_in: schemas.ApplicationUpdate,
) -> Any:
    """Update an application."""
    existing = crud.application.get(db, id=id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")
    update_data = application_in.model_dump(exclude_unset=True)
    if "applied_date" in update_data and update_data["applied_date"]:
        update_data["applied_date"] = str(update_data["applied_date"])
    row = crud.application.update(db=db, id=id, data=update_data)
    row.setdefault("stages", [])
    row.setdefault("outcome", None)
    row.setdefault("reflection", None)
    return row


# --- Stages ---
@router.post("/{id}/stages", response_model=schemas.ApplicationStageResponse)
def add_stage(
    *,
    db: Client = Depends(get_supabase),
    id: str,
    stage_in: schemas.ApplicationStageCreate,
) -> Any:
    """Add a stage to an application."""
    if id != stage_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    existing = crud.application.get(db, id=id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")
    data = stage_in.model_dump()
    if data.get("stage_date"):
        data["stage_date"] = str(data["stage_date"])
    return crud.application_stage.create(db=db, data=data)


# --- Outcomes ---
@router.post("/{id}/outcome", response_model=schemas.OutcomeResponse)
def set_outcome(
    *,
    db: Client = Depends(get_supabase),
    id: str,
    outcome_in: schemas.OutcomeCreate,
) -> Any:
    """Set the outcome of an application."""
    if id != outcome_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    return crud.outcome.create(db=db, data=outcome_in.model_dump())


# --- Reflections ---
@router.post("/{id}/reflection", response_model=schemas.ReflectionResponse)
def add_reflection(
    *,
    db: Client = Depends(get_supabase),
    id: str,
    reflection_in: schemas.ReflectionCreate,
) -> Any:
    """Add a reflection to an application."""
    if id != reflection_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    return crud.reflection.create(db=db, data=reflection_in.model_dump())
