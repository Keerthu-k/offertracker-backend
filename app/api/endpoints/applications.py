"""Application endpoints — the core of OfferTracker.

Status flow:
  Open → Applied → Shortlisted → Interview → Offer → Closed
                                                    → Rejected (at any point)
                                                    → Closed (user withdraws at any point)

Auto-transitions:
  - Creating with status Applied auto-sets applied_date to today
  - Changing status Open → Applied auto-sets applied_date
  - Adding a stage auto-transitions Applied → Interview
  - Adding an outcome (offer) auto-transitions to Offer
"""

from datetime import date as date_type
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
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
    try:
        app = crud.application.get(db, id=app_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch application %s: %s", app_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch application")
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
    try:
        return crud.application.get_multi_with_relations(
            db,
            user_id=current_user["id"],
            skip=skip,
            limit=limit,
            status=status,
            priority=priority,
        )
    except Exception as exc:
        logger.error("Failed to list applications for user %s: %s", current_user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to load applications")


@router.post("/", response_model=schemas.ApplicationResponse, status_code=201)
def create_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_in: schemas.ApplicationCreate,
) -> Any:
    """Create a new application (default status: Open)."""
    data = application_in.model_dump(exclude_none=True)
    data["user_id"] = current_user["id"]

    # Validate resume link if provided
    if data.get("resume_version_id"):
        try:
            resume = crud.resume_version.get(db, id=data["resume_version_id"])
        except DatabaseError:
            resume = None
        if not resume:
            raise HTTPException(status_code=404, detail="Resume version not found")

    # Auto-set applied_date when creating as Applied
    if data.get("status") == "Applied" and "applied_date" not in data:
        data["applied_date"] = str(date_type.today())

    _serialise_dates(data, DATE_FIELDS)

    try:
        row = _ensure_nested(crud.application.create(db=db, data=data))
    except DatabaseError as exc:
        logger.error("Failed to create application: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create application")

    # Activity + milestones (non-critical)
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
    try:
        application = crud.application.get_with_relations(db, id=id)
    except Exception as exc:
        logger.error("Failed to fetch application %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch application")
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

    # Auto-set applied_date when transitioning Open → Applied
    if (
        new_status == "Applied"
        and old_status == "Open"
        and "applied_date" not in update_data
    ):
        update_data["applied_date"] = str(date_type.today())

    _serialise_dates(update_data, DATE_FIELDS)

    try:
        row = _ensure_nested(crud.application.update(db=db, id=id, data=update_data))
    except DatabaseError as exc:
        logger.error("Failed to update application %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to update application")

    # Log status change or general update (non-critical)
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
    try:
        crud.application.remove(db=db, id=id)
    except DatabaseError as exc:
        logger.error("Failed to delete application %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete application")
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

    try:
        result = crud.application_stage.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to add stage to application %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to add interview stage")

    # Auto-transition: Applied → Interview
    if existing.get("status") == "Applied":
        try:
            crud.application.update(db=db, id=id, data={"status": "Interview"})
            log_activity(
                db,
                user_id=current_user["id"],
                action="Status Changed",
                description="Status: Applied → Interview (auto)",
                application_id=id,
                metadata={"old_status": "Applied", "new_status": "Interview", "auto": True},
            )
        except Exception as exc:
            logger.warning("Auto-transition to Interview failed for %s: %s", id, exc)

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
    try:
        existing = crud.application_stage.get(db, id=stage_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch stage %s: %s", stage_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch stage")
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Stage not found")

    update_data = stage_in.model_dump(exclude_unset=True)
    if "stage_date" in update_data and update_data["stage_date"]:
        update_data["stage_date"] = str(update_data["stage_date"])
    if "questions_asked" in update_data and update_data["questions_asked"] is None:
        update_data["questions_asked"] = []

    try:
        return crud.application_stage.update(db=db, id=stage_id, data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update stage %s: %s", stage_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update stage")


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
    try:
        existing = crud.application_stage.get(db, id=stage_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch stage %s: %s", stage_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch stage")
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Stage not found")
    try:
        crud.application_stage.remove(db=db, id=stage_id)
    except DatabaseError as exc:
        logger.error("Failed to delete stage %s: %s", stage_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete stage")
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
    try:
        existing_outcome = (
            db.table("outcomes")
            .select("id")
            .eq("application_id", id)
            .maybe_single()
            .execute()
        )
        if existing_outcome and existing_outcome.data:
            raise HTTPException(
                status_code=409,
                detail="This application already has offer details. Use PUT to update.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to check existing outcome for application %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to check existing outcome")

    data = outcome_in.model_dump(exclude_none=True)
    data["application_id"] = id
    data.setdefault("status", "Offer")

    _serialise_dates(data, OUTCOME_DATE_FIELDS)

    try:
        result = crud.outcome.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to create outcome for application %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to record offer details")

    # Auto-transition to Offer (unless already Closed)
    old_status = app.get("status")
    if old_status not in ("Offer", "Closed"):
        try:
            crud.application.update(db=db, id=id, data={"status": "Offer"})
            log_activity(
                db,
                user_id=current_user["id"],
                action="Status Changed",
                description=f"Status: {old_status} → Offer (offer received)",
                application_id=id,
                metadata={"old_status": old_status, "new_status": "Offer", "auto": True},
            )
        except Exception as exc:
            logger.warning("Auto-transition to Offer failed for %s: %s", id, exc)

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
    try:
        existing = crud.outcome.get(db, id=outcome_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch outcome %s: %s", outcome_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch outcome")
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Outcome not found")

    update_data = outcome_in.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is None:
        update_data.pop("status")
    _serialise_dates(update_data, OUTCOME_DATE_FIELDS)

    try:
        return crud.outcome.update(db=db, id=outcome_id, data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update outcome %s: %s", outcome_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update outcome")


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
    try:
        existing = crud.outcome.get(db, id=outcome_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch outcome %s: %s", outcome_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch outcome")
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Outcome not found")
    try:
        crud.outcome.remove(db=db, id=outcome_id)
    except DatabaseError as exc:
        logger.error("Failed to delete outcome %s: %s", outcome_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete outcome")
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

    try:
        result = crud.reflection.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to create reflection for application %s: %s", id, exc)
        raise HTTPException(status_code=500, detail="Failed to add reflection")

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
    try:
        existing = crud.reflection.get(db, id=reflection_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch reflection %s: %s", reflection_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch reflection")
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Reflection not found")
    try:
        return crud.reflection.update(
            db=db, id=reflection_id, data=reflection_in.model_dump(exclude_unset=True)
        )
    except DatabaseError as exc:
        logger.error("Failed to update reflection %s: %s", reflection_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update reflection")


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
    try:
        existing = crud.reflection.get(db, id=reflection_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch reflection %s: %s", reflection_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch reflection")
    if not existing or existing.get("application_id") != id:
        raise HTTPException(status_code=404, detail="Reflection not found")
    try:
        crud.reflection.remove(db=db, id=reflection_id)
    except DatabaseError as exc:
        logger.error("Failed to delete reflection %s: %s", reflection_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete reflection")
    return {"detail": "Reflection deleted"}
