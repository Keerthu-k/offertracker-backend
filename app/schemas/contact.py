"""Pydantic schemas for the Contacts / Networking tracker."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date

from app.schemas.enums import ContactType


# ------------------------------------------------------------------ #
# Input schemas
# ------------------------------------------------------------------ #

class ContactCreate(BaseModel):
    """Create a new networking contact."""
    application_id: Optional[str] = Field(
        None, description="Link to an application (optional — contacts can be general)"
    )
    name: str = Field(..., max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role_title: Optional[str] = Field(None, max_length=255, description="Contact's job title")
    company: Optional[str] = Field(None, max_length=255)
    contact_type: ContactType = ContactType.OTHER
    linkedin_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    last_contacted: Optional[date] = None


class ContactUpdate(BaseModel):
    """Partial update for a contact."""
    application_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role_title: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    contact_type: Optional[ContactType] = None
    linkedin_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    last_contacted: Optional[date] = None


# ------------------------------------------------------------------ #
# Response schema
# ------------------------------------------------------------------ #

class ContactResponse(BaseModel):
    id: str
    user_id: str
    application_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role_title: Optional[str] = None
    company: Optional[str] = None
    contact_type: str = "Other"
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None
    last_contacted: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
