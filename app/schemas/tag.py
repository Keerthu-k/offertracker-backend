"""Pydantic schemas for the Tags system."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


# ------------------------------------------------------------------ #
# Input schemas
# ------------------------------------------------------------------ #

class TagCreate(BaseModel):
    """Create a new user-defined tag."""
    name: str = Field(..., max_length=50, description="Tag label (unique per user)")
    color: str = Field(
        default="#6366f1",
        max_length=7,
        description="Hex colour code, e.g. #6366f1",
    )


class TagUpdate(BaseModel):
    """Partial update for a tag."""
    name: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7)


# ------------------------------------------------------------------ #
# Response schemas
# ------------------------------------------------------------------ #

class TagResponse(BaseModel):
    id: str
    user_id: str
    name: str
    color: str = "#6366f1"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationTagResponse(BaseModel):
    """Association between an application and a tag."""
    id: str
    application_id: str
    tag_id: str
    created_at: datetime
    tag: Optional[TagResponse] = None

    model_config = ConfigDict(from_attributes=True)
