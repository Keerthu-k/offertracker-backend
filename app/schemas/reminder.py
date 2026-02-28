"""Pydantic schemas for the Reminders system."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

from app.schemas.enums import ReminderType


# ------------------------------------------------------------------ #
# Input schemas
# ------------------------------------------------------------------ #

class ReminderCreate(BaseModel):
    """Schedule a new reminder."""
    application_id: Optional[str] = Field(
        None, description="Link to an application (optional)"
    )
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    remind_at: datetime = Field(..., description="When to trigger the reminder (ISO 8601)")
    reminder_type: ReminderType = ReminderType.GENERAL


class ReminderUpdate(BaseModel):
    """Partial update for a reminder."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    remind_at: Optional[datetime] = None
    reminder_type: Optional[ReminderType] = None
    is_completed: Optional[bool] = None


# ------------------------------------------------------------------ #
# Response schema
# ------------------------------------------------------------------ #

class ReminderResponse(BaseModel):
    id: str
    user_id: str
    application_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    remind_at: datetime
    reminder_type: str = "General"
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
