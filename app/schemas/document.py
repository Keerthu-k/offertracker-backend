"""Pydantic schemas for Application Documents."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

from app.schemas.enums import DocumentType


# ------------------------------------------------------------------ #
# Input schemas
# ------------------------------------------------------------------ #

class DocumentCreate(BaseModel):
    """Attach a document to an application."""
    application_id: str
    doc_type: DocumentType = DocumentType.OTHER
    name: str = Field(..., max_length=255, description="Descriptive file name")
    file_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class DocumentUpdate(BaseModel):
    """Partial update for a document."""
    doc_type: Optional[DocumentType] = None
    name: Optional[str] = Field(None, max_length=255)
    file_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


# ------------------------------------------------------------------ #
# Response schema
# ------------------------------------------------------------------ #

class DocumentResponse(BaseModel):
    id: str
    application_id: str
    doc_type: str = "Other"
    name: str
    file_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
