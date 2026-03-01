"""Resume file-upload endpoint (Supabase Storage)."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
from app import crud

router = APIRouter()

BUCKET_NAME = "resumes"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/resumes/{resume_id}")
async def upload_resume_file(
    *,
    db: Client = Depends(get_supabase),
    resume_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Upload a file for a resume version and update the ``file_url`` field."""
    try:
        resume = crud.resume_version.get(db, id=resume_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch resume %s: %s", resume_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch resume")
    if not resume:
        raise HTTPException(status_code=404, detail="Resume version not found")
    if resume.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your resume")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Word documents are allowed",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    file_path = f"{current_user['id']}/{resume_id}/{file.filename}"
    try:
        db.storage.from_(BUCKET_NAME).upload(
            file_path,
            content,
            {"content-type": file.content_type, "upsert": "true"},
        )
    except Exception as e:
        logger.error("Storage upload failed for %s: %s", file_path, e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    try:
        file_url = db.storage.from_(BUCKET_NAME).get_public_url(file_path)
        updated = crud.resume_version.update(
            db=db, id=resume_id, data={"file_url": file_url}
        )
    except Exception as exc:
        logger.error("Failed to update resume URL after upload: %s", exc)
        raise HTTPException(status_code=500, detail="Upload succeeded but failed to update resume record")

    return {"file_url": file_url, "resume": updated}
