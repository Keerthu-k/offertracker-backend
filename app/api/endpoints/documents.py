"""Application Documents endpoints — attach cover letters, portfolios,
work samples, and other files to specific applications.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
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
    app = crud.application.get(db, id=application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    return crud_document.get_for_application(db, application_id)


@router.post("/", response_model=schemas.DocumentResponse, status_code=201)
def create_document(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    doc_in: schemas.DocumentCreate,
) -> Any:
    """Attach a document to an application."""
    app = crud.application.get(db, id=doc_in.application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    data = doc_in.model_dump()
    result = crud_document.create(db=db, data=data)
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
    existing = crud_document.get(db, id=doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")
    app = crud.application.get(db, id=existing["application_id"])
    if not app or app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your document")
    update_data = doc_in.model_dump(exclude_unset=True)
    return crud_document.update(db=db, id=doc_id, data=update_data)


@router.delete("/{doc_id}")
def delete_document(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    doc_id: str,
) -> Any:
    """Remove a document."""
    existing = crud_document.get(db, id=doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")
    app = crud.application.get(db, id=existing["application_id"])
    if not app or app.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your document")
    crud_document.remove(db=db, id=doc_id)
    return {"detail": "Document deleted"}
