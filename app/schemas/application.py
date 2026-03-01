"""Application schemas — the core of OfferTracker.

Design principles:
- Every field earns its place (no bloat)
- Only company_name and role_title are required
- Optional fields match what real job postings actually show
- Sub-resource Create schemas take application_id from the URL path

Status flow:
  Open → Applied → Shortlisted → Interview → Offer → Closed
  At any point → Rejected or Closed
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from app.schemas.enums import (
    ApplicationStatus,
    StageType,
    StageResult,
    JobType,
    WorkMode,
    Priority,
    Source,
)


# ===================================================================
# Interview Stage
# ===================================================================

class ApplicationStageBase(BaseModel):
    stage_name: str = Field(..., max_length=100)
    stage_type: Optional[StageType] = None
    stage_date: Optional[date] = None
    result: StageResult = StageResult.PENDING
    duration_minutes: Optional[int] = Field(None, gt=0, description="Length in minutes")
    interviewer_names: Optional[str] = Field(None, description="Comma-separated names")
    prep_notes: Optional[str] = None
    questions_asked: Optional[List[str]] = Field(
        None, description="Interview questions that were asked"
    )
    notes: Optional[str] = None


class ApplicationStageCreate(ApplicationStageBase):
    """application_id is inferred from the URL path."""
    pass


class ApplicationStageUpdate(BaseModel):
    stage_name: Optional[str] = Field(None, max_length=100)
    stage_type: Optional[StageType] = None
    stage_date: Optional[date] = None
    result: Optional[StageResult] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    interviewer_names: Optional[str] = None
    prep_notes: Optional[str] = None
    questions_asked: Optional[List[str]] = None
    notes: Optional[str] = None


class ApplicationStageResponse(BaseModel):
    id: str
    application_id: str
    stage_name: str
    stage_type: Optional[str] = None
    stage_date: Optional[date] = None
    result: str = "Pending"
    duration_minutes: Optional[int] = None
    interviewer_names: Optional[str] = None
    prep_notes: Optional[str] = None
    questions_asked: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================================================================
# Outcome — offer details (created when you receive an offer)
# ===================================================================

class OutcomeBase(BaseModel):
    """Offer details — only relevant when an offer is received."""
    status: Optional[str] = Field(None, description="Offer, Rejected, or Closed")
    salary: Optional[int] = Field(None, ge=0, description="Annual base salary offered")
    salary_currency: str = Field(default="USD", max_length=3)
    bonus: Optional[str] = Field(None, description="Sign-on or annual bonus details")
    equity: Optional[str] = Field(None, description="Equity details e.g. '10k RSUs / 4yr'")
    benefits: Optional[str] = Field(None, description="Key benefits (PTO, health, 401k)")
    start_date: Optional[date] = None
    deadline: Optional[date] = Field(None, description="Deadline to accept the offer")
    negotiation_notes: Optional[str] = None
    notes: Optional[str] = None


class OutcomeCreate(OutcomeBase):
    """application_id is inferred from the URL path."""
    pass


class OutcomeUpdate(BaseModel):
    status: Optional[str] = None
    salary: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=3)
    bonus: Optional[str] = None
    equity: Optional[str] = None
    benefits: Optional[str] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    negotiation_notes: Optional[str] = None
    notes: Optional[str] = None


class OutcomeResponse(BaseModel):
    id: str
    application_id: str
    status: Optional[str] = None
    salary: Optional[int] = None
    salary_currency: str = "USD"
    bonus: Optional[str] = None
    equity: Optional[str] = None
    benefits: Optional[str] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    negotiation_notes: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================================================================
# Reflection
# ===================================================================

class ReflectionBase(BaseModel):
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None
    skill_gaps: Optional[Dict[str, Any]] = None
    improvement_plan: Optional[str] = None


class ReflectionCreate(ReflectionBase):
    """application_id is inferred from the URL path."""
    pass


class ReflectionUpdate(BaseModel):
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None
    skill_gaps: Optional[Dict[str, Any]] = None
    improvement_plan: Optional[str] = None


class ReflectionResponse(ReflectionBase):
    id: str
    application_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================================================================
# Application — lean, focused, every field earns its place
# ===================================================================

class ApplicationBase(BaseModel):
    company_name: str = Field(..., max_length=255)
    role_title: str = Field(..., max_length=255)
    url: Optional[str] = Field(None, max_length=500, description="Job posting URL")
    description: Optional[str] = Field(None, description="Job description or key requirements")
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[JobType] = None
    work_mode: Optional[WorkMode] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: str = Field(default="USD", max_length=3)
    applied_source: Optional[Source] = Field(None, description="Where you found this job")
    applied_date: Optional[date] = Field(
        None, description="When you applied (auto-set when status → Applied)"
    )
    follow_up_date: Optional[date] = Field(None, description="When to follow up next")
    priority: Optional[Priority] = None
    notes: Optional[str] = None
    status: ApplicationStatus = ApplicationStatus.OPEN


class ApplicationCreate(ApplicationBase):
    resume_version_id: Optional[str] = None


class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=255)
    role_title: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[JobType] = None
    work_mode: Optional[WorkMode] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=3)
    applied_source: Optional[Source] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    priority: Optional[Priority] = None
    notes: Optional[str] = None
    status: Optional[ApplicationStatus] = None
    resume_version_id: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: str
    company_name: str
    role_title: str
    url: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    work_mode: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    applied_source: Optional[str] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    status: str = "Open"
    resume_version_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    stages: List[ApplicationStageResponse] = []
    outcome: Optional[OutcomeResponse] = None
    reflection: Optional[ReflectionResponse] = None

    model_config = ConfigDict(from_attributes=True)
