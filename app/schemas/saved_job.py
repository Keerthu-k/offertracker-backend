"""Pydantic schemas for Saved Jobs.

A saved job is a job posting the user has bookmarked but not yet applied to.
It can be promoted to a full application via the convert endpoint, at which
point its status flips to 'Converted' and converted_to_application_id is set.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date

from app.schemas.enums import JobType, WorkMode, Priority


# ------------------------------------------------------------------ #
# Input schemas
# ------------------------------------------------------------------ #

class SavedJobCreate(BaseModel):
    """Save a new job posting for later."""
    company_name: str = Field(..., max_length=255)
    role_title: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500, description="Job posting URL")
    company_website: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[JobType] = None
    work_mode: Optional[WorkMode] = None
    salary_range_min: Optional[int] = Field(None, ge=0)
    salary_range_max: Optional[int] = Field(None, ge=0)
    salary_currency: str = Field(default="USD", max_length=3)
    priority: Priority = Priority.MEDIUM
    source: Optional[str] = Field(None, max_length=255, description="Where you found this job")
    notes: Optional[str] = None
    deadline: Optional[date] = Field(None, description="Application deadline")
    excitement_level: Optional[int] = Field(
        None, ge=1, le=5, description="How excited you are about this role (1–5)"
    )


class SavedJobUpdate(BaseModel):
    """Partial update for a saved job."""
    company_name: Optional[str] = Field(None, max_length=255)
    role_title: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    company_website: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[JobType] = None
    work_mode: Optional[WorkMode] = None
    salary_range_min: Optional[int] = Field(None, ge=0)
    salary_range_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=3)
    priority: Optional[Priority] = None
    source: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    deadline: Optional[date] = None
    excitement_level: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = Field(
        None,
        description="Active | Archived  (Converted is set automatically by the convert endpoint)",
    )


# ------------------------------------------------------------------ #
# Response schema
# ------------------------------------------------------------------ #

class SavedJobResponse(BaseModel):
    id: str
    user_id: str
    company_name: str
    role_title: Optional[str] = None
    url: Optional[str] = None
    company_website: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    work_mode: Optional[str] = None
    salary_range_min: Optional[int] = None
    salary_range_max: Optional[int] = None
    salary_currency: str = "USD"
    priority: str = "Medium"
    source: Optional[str] = None
    notes: Optional[str] = None
    deadline: Optional[date] = None
    status: str = "Active"
    excitement_level: Optional[int] = None
    converted_to_application_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
