"""Reminders endpoints — follow-ups, deadlines, interview prep alerts.

Reminders help professionals stay on top of time-sensitive tasks:
- Following up after an interview
- Responding to an offer before the deadline
- Preparing for an upcoming interview
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
from app.crud.crud_reminder import reminder as crud_reminder
from app.crud.crud_activity import log_activity
from app import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ReminderResponse])
def list_reminders(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    is_completed: Optional[bool] = None,
    reminder_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List reminders, optionally filtered by completion status or type."""
    try:
        return crud_reminder.get_user_reminders(
            db,
            current_user["id"],
            is_completed=is_completed,
            reminder_type=reminder_type,
            skip=skip,
            limit=limit,
        )
    except Exception as exc:
        logger.error("Failed to list reminders for user %s: %s", current_user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to load reminders")


@router.get("/upcoming", response_model=List[schemas.ReminderResponse])
def upcoming_reminders(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 10,
) -> Any:
    """Get the next upcoming incomplete reminders."""
    try:
        return crud_reminder.get_upcoming(db, current_user["id"], limit=limit)
    except Exception as exc:
        logger.error("Failed to load upcoming reminders for user %s: %s", current_user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to load upcoming reminders")


@router.post("/", response_model=schemas.ReminderResponse, status_code=201)
def create_reminder(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    reminder_in: schemas.ReminderCreate,
) -> Any:
    """Schedule a new reminder."""
    data = reminder_in.model_dump()
    data["user_id"] = current_user["id"]
    # Convert datetime to ISO string for JSON serialisation
    if data.get("remind_at"):
        data["remind_at"] = data["remind_at"].isoformat()
    try:
        result = crud_reminder.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to create reminder: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create reminder")
    log_activity(
        db,
        user_id=current_user["id"],
        action="Reminder Created",
        description=f"Reminder: {reminder_in.title}",
        application_id=reminder_in.application_id,
    )
    return result


@router.get("/{reminder_id}", response_model=schemas.ReminderResponse)
def get_reminder(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    reminder_id: str,
) -> Any:
    """Get a reminder by ID."""
    try:
        row = crud_reminder.get(db, id=reminder_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch reminder %s: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch reminder")
    if not row:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if row.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your reminder")
    return row


@router.put("/{reminder_id}", response_model=schemas.ReminderResponse)
def update_reminder(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    reminder_id: str,
    reminder_in: schemas.ReminderUpdate,
) -> Any:
    """Update a reminder."""
    try:
        existing = crud_reminder.get(db, id=reminder_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch reminder %s: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch reminder")
    if not existing:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your reminder")
    update_data = reminder_in.model_dump(exclude_unset=True)
    if "remind_at" in update_data and update_data["remind_at"]:
        update_data["remind_at"] = update_data["remind_at"].isoformat()
    try:
        return crud_reminder.update(db=db, id=reminder_id, data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update reminder %s: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update reminder")


@router.post("/{reminder_id}/complete", response_model=schemas.ReminderResponse)
def complete_reminder(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    reminder_id: str,
) -> Any:
    """Mark a reminder as completed."""
    try:
        existing = crud_reminder.get(db, id=reminder_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch reminder %s: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch reminder")
    if not existing:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your reminder")
    if existing.get("is_completed"):
        raise HTTPException(status_code=400, detail="Reminder already completed")
    try:
        result = crud_reminder.mark_completed(db, reminder_id)
    except Exception as exc:
        logger.error("Failed to complete reminder %s: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail="Failed to complete reminder")
    log_activity(
        db,
        user_id=current_user["id"],
        action="Reminder Completed",
        description=f"Completed: {existing.get('title', 'Reminder')}",
        application_id=existing.get("application_id"),
    )
    track_progress_and_check_milestones(db, current_user["id"], "complete_reminder")
    return result


@router.delete("/{reminder_id}")
def delete_reminder(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    reminder_id: str,
) -> Any:
    """Delete a reminder."""
    try:
        existing = crud_reminder.get(db, id=reminder_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch reminder %s: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch reminder")
    if not existing:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your reminder")
    try:
        crud_reminder.remove(db=db, id=reminder_id)
    except DatabaseError as exc:
        logger.error("Failed to delete reminder %s: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete reminder")
    return {"detail": "Reminder deleted"}
