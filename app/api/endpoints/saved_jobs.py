"""Saved Jobs endpoints.

A saved job is a bookmarked posting the user intends to apply to later.
It lives outside the application pipeline until the user consciously
promotes it via POST /saved-jobs/{id}/convert, which creates a full
application and marks the saved job as Converted.

Endpoints:
  GET    /saved-jobs/              — list (filter by status, priority)
  POST   /saved-jobs/              — save a new job
  GET    /saved-jobs/{id}          — get one
  PUT    /saved-jobs/{id}          — update (status can be set to Archived)
  DELETE /saved-jobs/{id}          — remove
  POST   /saved-jobs/{id}/convert  — promote to a full application
"""

from datetime import date as date_type
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app.crud.crud_saved_job import saved_job as crud_saved_job
from app.crud.crud_activity import log_activity
from app import crud, schemas

router = APIRouter()


def _verify_ownership(db: Client, current_user: dict, saved_job_id: str) -> dict:
    row = crud_saved_job.get(db, id=saved_job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Saved job not found")
    if row.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your saved job")
    return row


# ======================================================================
# CRUD
# ======================================================================

@router.get("/", response_model=List[schemas.SavedJobResponse])
def list_saved_jobs(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List saved jobs, optionally filtered by status and/or priority."""
    return crud_saved_job.get_user_saved_jobs(
        db,
        current_user["id"],
        status=status,
        priority=priority,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=schemas.SavedJobResponse, status_code=201)
def create_saved_job(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_in: schemas.SavedJobCreate,
) -> Any:
    """Save a job posting for later review."""
    data = job_in.model_dump(exclude_none=True)
    data["user_id"] = current_user["id"]
    if "deadline" in data and data["deadline"] is not None:
        data["deadline"] = str(data["deadline"])

    result = crud_saved_job.create(db=db, data=data)

    log_activity(
        db,
        user_id=current_user["id"],
        action="Application Created",   # closest activity_log action available
        description=f"Saved job: {job_in.company_name}"
                    + (f" — {job_in.role_title}" if job_in.role_title else ""),
    )
    track_progress_and_check_milestones(db, current_user["id"], "save_job")
    return result


@router.get("/{saved_job_id}", response_model=schemas.SavedJobResponse)
def get_saved_job(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_job_id: str,
) -> Any:
    """Get a saved job by ID."""
    return _verify_ownership(db, current_user, saved_job_id)


@router.put("/{saved_job_id}", response_model=schemas.SavedJobResponse)
def update_saved_job(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_job_id: str,
    job_in: schemas.SavedJobUpdate,
) -> Any:
    """Update a saved job.

    You can archive it by setting status='Archived'.
    Status 'Converted' is managed automatically by the /convert endpoint.
    """
    existing = _verify_ownership(db, current_user, saved_job_id)

    # Prevent manually setting Converted — that must go through /convert
    update_data = job_in.model_dump(exclude_unset=True)
    if update_data.get("status") == "Converted":
        raise HTTPException(
            status_code=400,
            detail="Use POST /saved-jobs/{id}/convert to convert a saved job to an application.",
        )
    if "deadline" in update_data and update_data["deadline"] is not None:
        update_data["deadline"] = str(update_data["deadline"])

    return crud_saved_job.update(db=db, id=saved_job_id, data=update_data)


@router.delete("/{saved_job_id}")
def delete_saved_job(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_job_id: str,
) -> Any:
    """Delete a saved job."""
    _verify_ownership(db, current_user, saved_job_id)
    crud_saved_job.remove(db=db, id=saved_job_id)
    return {"detail": "Saved job deleted"}


# ======================================================================
# Convert → Application
# ======================================================================

@router.post("/{saved_job_id}/convert", response_model=schemas.ApplicationResponse, status_code=201)
def convert_to_application(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_job_id: str,
) -> Any:
    """Promote a saved job to a full application.

    - Creates an application pre-filled with the saved job's data.
    - Sets the application status to 'Open' (user has not applied yet).
    - Marks the saved job status as 'Converted' and records the new
      application ID in converted_to_application_id.
    - Idempotent guard: raises 409 if already converted.
    """
    saved = _verify_ownership(db, current_user, saved_job_id)

    if saved.get("status") == "Converted":
        raise HTTPException(
            status_code=409,
            detail="This saved job has already been converted to an application.",
        )

    # Build application payload from saved job fields
    app_data: dict = {
        "user_id": current_user["id"],
        "company_name": saved["company_name"],
        "status": "Open",
    }
    # Map fields that exist on applications
    for field in (
        "role_title", "url", "company_website", "location",
        "job_type", "work_mode",
        "salary_min", "salary_max", "salary_currency",
        "applied_source", "notes",
    ):
        # saved_jobs uses salary_range_min/max; applications uses salary_min/max
        if field == "salary_min" and saved.get("salary_range_min") is not None:
            app_data["salary_min"] = saved["salary_range_min"]
        elif field == "salary_max" and saved.get("salary_range_max") is not None:
            app_data["salary_max"] = saved["salary_range_max"]
        elif field in saved and saved[field] is not None:
            app_data[field] = saved[field]

    new_app = crud.application.create(db=db, data=app_data)
    new_app.setdefault("stages", [])
    new_app.setdefault("outcome", None)
    new_app.setdefault("reflection", None)

    # Mark saved job as Converted
    crud_saved_job.update(
        db=db,
        id=saved_job_id,
        data={
            "status": "Converted",
            "converted_to_application_id": new_app["id"],
        },
    )

    log_activity(
        db,
        user_id=current_user["id"],
        action="Application Created",
        description=f"Converted saved job to application: {saved['company_name']}"
                    + (f" — {saved.get('role_title', '')}" if saved.get("role_title") else ""),
        application_id=new_app["id"],
        metadata={"source": "saved_job", "saved_job_id": saved_job_id},
    )
    track_progress_and_check_milestones(db, current_user["id"], "create_application")
    track_progress_and_check_milestones(db, current_user["id"], "convert_saved_job")

    return new_app
