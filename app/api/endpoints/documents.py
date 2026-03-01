"""Application Documents endpoints — attach cover letters, portfolios,
work samples, and other files to specific applications.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
from app.crud.crud_document import document as crud_document
from app.crud.crud_activity import log_activity
from app import crud, schemas

router = APIRouter()


@router.get("/{application_id}", response_model=List[schemas.DocumentResponse])
def list_documents(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_id: str,
) -> Any:
    """List all documents attached to an application."""
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
        return crud_document.get_for_application(db, application_id)
    except Exception as exc:
        logger.error("Failed to list documents for application %s: %s", application_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load documents")


@router.post("/", response_model=schemas.DocumentResponse, status_code=201)
def create_document(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    doc_in: schemas.DocumentCreate,
) -> Any:
    """Attach a document to an application."""
    try:
        app = crud.application.get(db, id=doc_in.application_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch application %s: %s", doc_in.application_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch application")
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    data = doc_in.model_dump()
    try:
        result = crud_document.create(db=db, data=data)
    except DatabaseError as exc:
        logger.error("Failed to create document: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to attach document")
    log_activity(
        db,
        user_id=current_user["id"],
        action="Document Added",
        description=f"Added {doc_in.doc_type}: {doc_in.name}",
        application_id=doc_in.application_id,
    )
    return result


@router.put("/{doc_id}", response_model=schemas.DocumentResponse)
def update_document(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    doc_id: str,
    doc_in: schemas.DocumentUpdate,
) -> Any:
    """Update a document's metadata."""
    try:
        existing = crud_document.get(db, id=doc_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch document %s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch document")
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        app = crud.application.get(db, id=existing["application_id"])
    except DatabaseError as exc:
        logger.error("Failed to fetch parent application: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to verify ownership")
    if not app or app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your document")
    update_data = doc_in.model_dump(exclude_unset=True)
    try:
        return crud_document.update(db=db, id=doc_id, data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update document %s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update document")


@router.delete("/{doc_id}")
def delete_document(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    doc_id: str,
) -> Any:
    """Remove a document."""
    try:
        existing = crud_document.get(db, id=doc_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch document %s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch document")
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        app = crud.application.get(db, id=existing["application_id"])
    except DatabaseError as exc:
        logger.error("Failed to fetch parent application: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to verify ownership")
    if not app or app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your document")
    try:
        crud_document.remove(db=db, id=doc_id)
    except DatabaseError as exc:
        logger.error("Failed to delete document %s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete document")
    return {"detail": "Document deleted"}
