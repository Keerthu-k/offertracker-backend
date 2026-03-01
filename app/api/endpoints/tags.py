"""Tags endpoints — user-defined, colour-coded labels for applications.

Tags let users organise applications in any way that makes sense to them:
"Dream Job", "Backup", "FAANG", "Remote OK", "Needs Visa", etc.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
from app.crud.crud_tag import tag as crud_tag, application_tag as crud_app_tag
from app.crud.crud_activity import log_activity
from app import crud, schemas

router = APIRouter()


# ======================================================================
# Tag CRUD
# ======================================================================


@router.get("/", response_model=List[schemas.TagResponse])
def list_tags(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List all tags for the current user."""
    try:
        return crud_tag.get_user_tags(db, current_user["id"])
    except Exception as exc:
        logger.error("Failed to list tags for user %s: %s", current_user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to load tags")


@router.post("/", response_model=schemas.TagResponse, status_code=201)
def create_tag(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    tag_in: schemas.TagCreate,
) -> Any:
    """Create a new tag (name must be unique per user)."""
    try:
        existing = crud_tag.get_by_name(db, current_user["id"], tag_in.name)
    except Exception as exc:
        logger.error("Failed to check tag name: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to check tag name")
    if existing:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")
    data = tag_in.model_dump()
    data["user_id"] = current_user["id"]
    try:
        result = crud_tag.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to create tag: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create tag")
    track_progress_and_check_milestones(db, current_user["id"], "create_tag")
    return result


@router.put("/{tag_id}", response_model=schemas.TagResponse)
def update_tag(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    tag_id: str,
    tag_in: schemas.TagUpdate,
) -> Any:
    """Update a tag's name or colour."""
    try:
        existing = crud_tag.get(db, id=tag_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch tag %s: %s", tag_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch tag")
    if not existing:
        raise HTTPException(status_code=404, detail="Tag not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your tag")
    update_data = tag_in.model_dump(exclude_unset=True)
    try:
        return crud_tag.update(db=db, id=tag_id, data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update tag %s: %s", tag_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update tag")


@router.delete("/{tag_id}")
def delete_tag(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    tag_id: str,
) -> Any:
    """Delete a tag (also removes it from all applications)."""
    try:
        existing = crud_tag.get(db, id=tag_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch tag %s: %s", tag_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch tag")
    if not existing:
        raise HTTPException(status_code=404, detail="Tag not found")
    if existing.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your tag")
    try:
        crud_tag.remove(db=db, id=tag_id)
    except DatabaseError as exc:
        logger.error("Failed to delete tag %s: %s", tag_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete tag")
    return {"detail": "Tag deleted"}


# ======================================================================
# Application ↔ Tag assignments
# ======================================================================


@router.get(
    "/application/{application_id}",
    response_model=List[schemas.ApplicationTagResponse],
)
def get_tags_for_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_id: str,
) -> Any:
    """Get all tags assigned to an application."""
    try:
        app = crud.application.get(db, id=application_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch application %s: %s", application_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch application")
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    try:
        return crud_app_tag.get_tags_for_application(db, application_id)
    except Exception as exc:
        logger.error("Failed to load tags for application %s: %s", application_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load application tags")


@router.post(
    "/application/{application_id}/{tag_id}",
    response_model=schemas.ApplicationTagResponse,
    status_code=201,
)
def assign_tag(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_id: str,
    tag_id: str,
) -> Any:
    """Assign a tag to an application."""
    try:
        app = crud.application.get(db, id=application_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch application %s: %s", application_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch application")
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    try:
        tag_row = crud_tag.get(db, id=tag_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch tag %s: %s", tag_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch tag")
    if not tag_row or tag_row.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Tag not found")
    try:
        result = crud_app_tag.assign(db, application_id, tag_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Tag already assigned to this application")
    log_activity(
        db,
        user_id=current_user["id"],
        action="Tag Assigned",
        description=f"Tagged application with '{tag_row['name']}'",
        application_id=application_id,
    )
    return result


@router.delete("/application/{application_id}/{tag_id}")
def unassign_tag(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_id: str,
    tag_id: str,
) -> Any:
    """Remove a tag from an application."""
    try:
        app = crud.application.get(db, id=application_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch application %s: %s", application_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch application")
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    try:
        success = crud_app_tag.unassign(db, application_id, tag_id)
    except Exception as exc:
        logger.error("Failed to unassign tag %s from application %s: %s", tag_id, application_id, exc)
        raise HTTPException(status_code=500, detail="Failed to remove tag")
    if not success:
        raise HTTPException(status_code=404, detail="Tag not assigned to this application")
    return {"detail": "Tag removed from application"}
