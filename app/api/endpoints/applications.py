from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app import crud, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ApplicationResponse])
def read_applications(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve current user's applications with nested relations."""
    return crud.application.get_multi_with_relations(
        db, user_id=current_user["id"], skip=skip, limit=limit
    )


@router.post("/", response_model=schemas.ApplicationResponse)
def create_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_in: schemas.ApplicationCreate,
) -> Any:
    """Create new application."""
    data = application_in.model_dump()
    data["user_id"] = current_user["id"]
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
    # Progress tracking
    track_progress_and_check_milestones(db, current_user["id"], "create_application")
    return row


@router.get("/{id}", response_model=schemas.ApplicationResponse)
def read_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
) -> Any:
    """Get application by ID."""
    application = crud.application.get_with_relations(db, id=id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    return application


@router.put("/{id}", response_model=schemas.ApplicationResponse)
def update_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    application_in: schemas.ApplicationUpdate,
) -> Any:
    """Update an application."""
    existing = crud.application.get(db, id=id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    update_data = application_in.model_dump(exclude_unset=True)
    if "applied_date" in update_data and update_data["applied_date"]:
        update_data["applied_date"] = str(update_data["applied_date"])
    row = crud.application.update(db=db, id=id, data=update_data)
    row.setdefault("stages", [])
    row.setdefault("outcome", None)
    row.setdefault("reflection", None)
    return row


@router.delete("/{id}")
def delete_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
) -> Any:
    """Delete an application and all related stages, outcome, reflection."""
    existing = crud.application.get(db, id=id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    crud.application.remove(db=db, id=id)
    return {"detail": "Application deleted"}


# --- Stages ---


@router.post("/{id}/stages", response_model=schemas.ApplicationStageResponse)
def add_stage(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    stage_in: schemas.ApplicationStageCreate,
) -> Any:
    """Add a stage to an application."""
    if id != stage_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    existing = crud.application.get(db, id=id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    data = stage_in.model_dump()
    if data.get("stage_date"):
        data["stage_date"] = str(data["stage_date"])
    result = crud.application_stage.create(db=db, data=data)
    track_progress_and_check_milestones(db, current_user["id"], "add_stage")
    return result


@router.put("/{id}/stages/{stage_id}", response_model=schemas.ApplicationStageResponse)
def update_stage(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    stage_id: str,
    stage_in: schemas.ApplicationStageUpdate,
) -> Any:
    """Update a stage."""
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    existing = crud.application_stage.get(db, id=stage_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Stage not found")
    update_data = stage_in.model_dump(exclude_unset=True)
    if "stage_date" in update_data and update_data["stage_date"]:
        update_data["stage_date"] = str(update_data["stage_date"])
    return crud.application_stage.update(db=db, id=stage_id, data=update_data)


@router.delete("/{id}/stages/{stage_id}")
def delete_stage(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    stage_id: str,
) -> Any:
    """Delete a stage."""
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    existing = crud.application_stage.get(db, id=stage_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Stage not found")
    crud.application_stage.remove(db=db, id=stage_id)
    return {"detail": "Stage deleted"}


# --- Outcomes ---


@router.post("/{id}/outcome", response_model=schemas.OutcomeResponse)
def set_outcome(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    outcome_in: schemas.OutcomeCreate,
) -> Any:
    """Set the outcome of an application."""
    if id != outcome_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    result = crud.outcome.create(db=db, data=outcome_in.model_dump())
    track_progress_and_check_milestones(db, current_user["id"], "set_outcome")
    return result


@router.put("/{id}/outcome/{outcome_id}", response_model=schemas.OutcomeResponse)
def update_outcome(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    outcome_id: str,
    outcome_in: schemas.OutcomeUpdate,
) -> Any:
    """Update an outcome."""
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    existing = crud.outcome.get(db, id=outcome_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Outcome not found")
    update_data = outcome_in.model_dump(exclude_unset=True)
    return crud.outcome.update(db=db, id=outcome_id, data=update_data)


@router.delete("/{id}/outcome/{outcome_id}")
def delete_outcome(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    outcome_id: str,
) -> Any:
    """Delete an outcome."""
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    existing = crud.outcome.get(db, id=outcome_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Outcome not found")
    crud.outcome.remove(db=db, id=outcome_id)
    return {"detail": "Outcome deleted"}


# --- Reflections ---


@router.post("/{id}/reflection", response_model=schemas.ReflectionResponse)
def add_reflection(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    reflection_in: schemas.ReflectionCreate,
) -> Any:
    """Add a reflection to an application."""
    if id != reflection_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    result = crud.reflection.create(db=db, data=reflection_in.model_dump())
    track_progress_and_check_milestones(db, current_user["id"], "add_reflection")
    return result


@router.put("/{id}/reflection/{reflection_id}", response_model=schemas.ReflectionResponse)
def update_reflection(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    reflection_id: str,
    reflection_in: schemas.ReflectionUpdate,
) -> Any:
    """Update a reflection."""
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    existing = crud.reflection.get(db, id=reflection_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Reflection not found")
    update_data = reflection_in.model_dump(exclude_unset=True)
    return crud.reflection.update(db=db, id=reflection_id, data=update_data)


@router.delete("/{id}/reflection/{reflection_id}")
def delete_reflection(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    reflection_id: str,
) -> Any:
    """Delete a reflection."""
    app = crud.application.get(db, id=id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    existing = crud.reflection.get(db, id=reflection_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Reflection not found")
    crud.reflection.remove(db=db, id=reflection_id)
    return {"detail": "Reflection deleted"}
