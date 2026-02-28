"""Application endpoints — the core of OfferTracker.

Status flow:
  Saved → Applied → Interviewing → Offer → Accepted
                                        → Rejected (at any point)
                                        → Withdrawn (at any point)

Auto-transitions:
  - Creating with status Applied auto-sets applied_date to today
  - Changing status Saved → Applied auto-sets applied_date
  - Adding a stage auto-transitions Applied → Interviewing
  - Adding an outcome (offer) auto-transitions to Offer
"""

from datetime import date as date_type
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app.crud.crud_activity import log_activity
from app import crud, schemas

router = APIRouter()

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

DATE_FIELDS = ("applied_date", "follow_up_date")
OUTCOME_DATE_FIELDS = ("start_date", "deadline")


def _serialise_dates(data: dict, fields: tuple) -> None:
    """Convert date objects to ISO strings for Supabase JSON serialisation."""
    for f in fields:
        if f in data and data[f] is not None:
            data[f] = str(data[f])


def _ensure_nested(row: dict) -> dict:
    """Guarantee the nested relation keys exist so response_model is happy."""
    row.setdefault("stages", [])
    row.setdefault("outcome", None)
    row.setdefault("reflection", None)
    return row


def _verify_ownership(db, current_user, app_id: str):
    """Fetch application and verify the current user owns it."""
    app = crud.application.get(db, id=app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    return app


# ==================================================================
# Applications CRUD
# ==================================================================


@router.get("/", response_model=List[schemas.ApplicationResponse])
def read_applications(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> Any:
    """List current user's applications with nested stages, outcome, reflection.

    Optional query params: ``status``, ``priority``.
    """
    return crud.application.get_multi_with_relations(
        db,
        user_id=current_user["id"],
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
    )


@router.post("/", response_model=schemas.ApplicationResponse, status_code=201)
def create_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_in: schemas.ApplicationCreate,
) -> Any:
    """Create a new application (default status: Saved)."""
    data = application_in.model_dump(exclude_none=True)
    data["user_id"] = current_user["id"]

    # Validate resume link if provided
    if data.get("resume_version_id"):
        resume = crud.resume_version.get(db, id=data["resume_version_id"])
        if not resume:
            raise HTTPException(status_code=404, detail="Resume version not found")

    # Auto-set applied_date when creating as Applied
    if data.get("status") == "Applied" and "applied_date" not in data:
        data["applied_date"] = str(date_type.today())

    _serialise_dates(data, DATE_FIELDS)

    row = _ensure_nested(crud.application.create(db=db, data=data))

    # Activity + milestones
    log_activity(
        db,
        user_id=current_user["id"],
        action="Application Created",
        description=f"Created: {application_in.company_name} — {application_in.role_title}",
        application_id=row["id"],
    )
    track_progress_and_check_milestones(db, current_user["id"], "create_application")
    if data.get("salary_min") or data.get("salary_max"):
        track_progress_and_check_milestones(db, current_user["id"], "track_salary")

    return row


@router.get("/{id}", response_model=schemas.ApplicationResponse)
def read_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
) -> Any:
    """Get application by ID with nested relations."""
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
    existing = _verify_ownership(db, current_user, id)
    update_data = application_in.model_dump(exclude_unset=True)

    old_status = existing.get("status")
    new_status = update_data.get("status")

    # Auto-set applied_date when transitioning Saved → Applied
    if (
        new_status == "Applied"
        and old_status == "Saved"
        and "applied_date" not in update_data
    ):
        update_data["applied_date"] = str(date_type.today())

    _serialise_dates(update_data, DATE_FIELDS)

    row = _ensure_nested(crud.application.update(db=db, id=id, data=update_data))

    # Log status change or general update
    if new_status and new_status != old_status:
        log_activity(
            db,
            user_id=current_user["id"],
            action="Status Changed",
            description=f"Status: {old_status} → {new_status}",
            application_id=id,
            metadata={"old_status": old_status, "new_status": new_status},
        )
    else:
        log_activity(
            db,
            user_id=current_user["id"],
            action="Application Updated",
            description=f"Updated {existing.get('company_name', 'application')}",
            application_id=id,
        )

    return row


@router.delete("/{id}")
def delete_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
) -> Any:
    """Delete an application and all related data."""
    _verify_ownership(db, current_user, id)
    crud.application.remove(db=db, id=id)
    return {"detail": "Application deleted"}


# ==================================================================
# Stages
# ==================================================================


@router.post("/{id}/stages", response_model=schemas.ApplicationStageResponse, status_code=201)
def add_stage(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    stage_in: schemas.ApplicationStageCreate,
) -> Any:
    """Add an interview stage to an application."""
    existing = _verify_ownership(db, current_user, id)

    data = stage_in.model_dump(exclude_none=True)
    data["application_id"] = id

    if data.get("stage_date"):
        data["stage_date"] = str(data["stage_date"])

    result = crud.application_stage.create(db=db, data=data)

    # Auto-transition: Applied → Interviewing
    if existing.get("status") == "Applied":
        crud.application.update(db=db, id=id, data={"status": "Interviewing"})
        log_activity(
            db,
            user_id=current_user["id"],
            action="Status Changed",
            description="Status: Applied → Interviewing (auto)",
            application_id=id,
            metadata={"old_status": "Applied", "new_status": "Interviewing", "auto": True},
        )

    log_activity(
        db,
        user_id=current_user["id"],
        action="Stage Added",
        description=f"Added stage: {stage_in.stage_name}",
        application_id=id,
    )
    track_progress_and_check_milestones(db, current_user["id"], "add_stage")
    if data.get("prep_notes"):
        track_progress_and_check_milestones(db, current_user["id"], "add_prep_notes")

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
    """Update an interview stage."""
    _verify_ownership(db, current_user, id)
    existing = crud.application_stage.get(db, id=stage_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Stage not found")

    update_data = stage_in.model_dump(exclude_unset=True)
    if "stage_date" in update_data and update_data["stage_date"]:
        update_data["stage_date"] = str(update_data["stage_date"])
    if "questions_asked" in update_data and update_data["questions_asked"] is None:
        update_data["questions_asked"] = []

    return crud.application_stage.update(db=db, id=stage_id, data=update_data)


@router.delete("/{id}/stages/{stage_id}")
def delete_stage(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    stage_id: str,
) -> Any:
    """Delete an interview stage."""
    _verify_ownership(db, current_user, id)
    existing = crud.application_stage.get(db, id=stage_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Stage not found")
    crud.application_stage.remove(db=db, id=stage_id)
    return {"detail": "Stage deleted"}


# ==================================================================
# Outcome (Offer Details)
# ==================================================================


@router.post("/{id}/outcome", response_model=schemas.OutcomeResponse, status_code=201)
def set_outcome(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    outcome_in: schemas.OutcomeCreate,
) -> Any:
    """Record offer details for an application.

    Automatically transitions the application status to Offer.
    """
    app = _verify_ownership(db, current_user, id)

    # Check for existing outcome (one-to-one)
    existing_outcome = (
        db.table("outcomes")
        .select("id")
        .eq("application_id", id)
        .maybe_single()
        .execute()
    )
    if existing_outcome.data:
        raise HTTPException(
            status_code=409,
            detail="This application already has offer details. Use PUT to update.",
        )

    data = outcome_in.model_dump(exclude_none=True)
    data["application_id"] = id
    data.setdefault("status", "Offer")

    _serialise_dates(data, OUTCOME_DATE_FIELDS)

    result = crud.outcome.create(db=db, data=data)

    # Auto-transition to Offer (unless already Accepted)
    old_status = app.get("status")
    if old_status not in ("Offer", "Accepted"):
        crud.application.update(db=db, id=id, data={"status": "Offer"})
        log_activity(
            db,
            user_id=current_user["id"],
            action="Status Changed",
            description=f"Status: {old_status} → Offer (offer received)",
            application_id=id,
            metadata={"old_status": old_status, "new_status": "Offer", "auto": True},
        )

    log_activity(
        db,
        user_id=current_user["id"],
        action="Offer Added",
        description="Recorded offer details",
        application_id=id,
    )
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
    """Update offer details."""
    _verify_ownership(db, current_user, id)
    existing = crud.outcome.get(db, id=outcome_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Outcome not found")

    update_data = outcome_in.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is None:
        update_data.pop("status")
    _serialise_dates(update_data, OUTCOME_DATE_FIELDS)

    return crud.outcome.update(db=db, id=outcome_id, data=update_data)


@router.delete("/{id}/outcome/{outcome_id}")
def delete_outcome(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    outcome_id: str,
) -> Any:
    """Delete offer details."""
    _verify_ownership(db, current_user, id)
    existing = crud.outcome.get(db, id=outcome_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Outcome not found")
    crud.outcome.remove(db=db, id=outcome_id)
    return {"detail": "Outcome deleted"}


# ==================================================================
# Reflections
# ==================================================================


@router.post("/{id}/reflection", response_model=schemas.ReflectionResponse, status_code=201)
def add_reflection(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    reflection_in: schemas.ReflectionCreate,
) -> Any:
    """Add a reflection to an application."""
    _verify_ownership(db, current_user, id)

    data = reflection_in.model_dump(exclude_none=True)
    data["application_id"] = id

    result = crud.reflection.create(db=db, data=data)

    log_activity(
        db,
        user_id=current_user["id"],
        action="Reflection Added",
        description="Added a post-interview reflection",
        application_id=id,
    )
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
    _verify_ownership(db, current_user, id)
    existing = crud.reflection.get(db, id=reflection_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Reflection not found")
    return crud.reflection.update(
        db=db, id=reflection_id, data=reflection_in.model_dump(exclude_unset=True)
    )


@router.delete("/{id}/reflection/{reflection_id}")
def delete_reflection(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    id: str,
    reflection_id: str,
) -> Any:
    """Delete a reflection."""
    _verify_ownership(db, current_user, id)
    existing = crud.reflection.get(db, id=reflection_id)
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Reflection not found")
    crud.reflection.remove(db=db, id=reflection_id)
    return {"detail": "Reflection deleted"}
