"""Contacts / Networking tracker endpoints.

Track recruiters, hiring managers, referrals, and other professional
contacts across your job search — optionally linked to specific applications.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
from app.crud.crud_contact import contact as crud_contact
from app.crud.crud_activity import log_activity
from app import crud, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ContactResponse])
def list_contacts(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_id: Optional[str] = None,
    contact_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List contacts, optionally filtered by application or type."""
    try:
        return crud_contact.get_user_contacts(
            db,
            current_user["id"],
            application_id=application_id,
            contact_type=contact_type,
            skip=skip,
            limit=limit,
        )
    except Exception as exc:
        logger.error("Failed to list contacts for user %s: %s", current_user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to load contacts")


@router.post("/", response_model=schemas.ContactResponse, status_code=201)
def create_contact(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    contact_in: schemas.ContactCreate,
) -> Any:
    """Add a new networking contact."""
    data = contact_in.model_dump()
    data["user_id"] = current_user["id"]
    # Convert date to string for JSON serialisation
    if data.get("last_contacted"):
        data["last_contacted"] = str(data["last_contacted"])
    try:
        result = crud_contact.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to create contact: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create contact")
    log_activity(
        db,
        user_id=current_user["id"],
        action="Contact Added",
        description=f"Added contact: {contact_in.name}",
        application_id=contact_in.application_id,
    )
    track_progress_and_check_milestones(db, current_user["id"], "add_contact")
    return result


@router.get("/{contact_id}", response_model=schemas.ContactResponse)
def get_contact(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    contact_id: str,
) -> Any:
    """Get a contact by ID."""
    try:
        row = crud_contact.get(db, id=contact_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch contact %s: %s", contact_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch contact")
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    if row.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your contact")
    return row


@router.put("/{contact_id}", response_model=schemas.ContactResponse)
def update_contact(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    contact_id: str,
    contact_in: schemas.ContactUpdate,
) -> Any:
    """Update a contact."""
    try:
        existing = crud_contact.get(db, id=contact_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch contact %s: %s", contact_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch contact")
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your contact")
    update_data = contact_in.model_dump(exclude_unset=True)
    if "last_contacted" in update_data and update_data["last_contacted"]:
        update_data["last_contacted"] = str(update_data["last_contacted"])
    try:
        return crud_contact.update(db=db, id=contact_id, data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update contact %s: %s", contact_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update contact")


@router.delete("/{contact_id}")
def delete_contact(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    contact_id: str,
) -> Any:
    """Delete a contact."""
    try:
        existing = crud_contact.get(db, id=contact_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch contact %s: %s", contact_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch contact")
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your contact")
    try:
        crud_contact.remove(db=db, id=contact_id)
    except DatabaseError as exc:
        logger.error("Failed to delete contact %s: %s", contact_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete contact")
    return {"detail": "Contact deleted"}
