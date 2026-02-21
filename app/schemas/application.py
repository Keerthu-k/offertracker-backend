from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# ---------------
# ApplicationStage
# ---------------
class ApplicationStageBase(BaseModel):
    stage_name: str = Field(..., max_length=100)
    stage_date: Optional[date] = None
    notes: Optional[str] = None

class ApplicationStageCreate(ApplicationStageBase):
    application_id: str

class ApplicationStageUpdate(BaseModel):
    stage_name: Optional[str] = Field(None, max_length=100)
    stage_date: Optional[date] = None
    notes: Optional[str] = None

class ApplicationStageResponse(ApplicationStageBase):
    id: str
    application_id: str
    stage_date: date
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------------
# Outcome
# ---------------
class OutcomeBase(BaseModel):
    status: str = Field(..., max_length=50)  # Offer, Rejected, Withdrawn
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None

class OutcomeCreate(OutcomeBase):
    application_id: str

class OutcomeUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=50)
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None

class OutcomeResponse(OutcomeBase):
    id: str
    application_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------------
# Reflection
# ---------------
class ReflectionBase(BaseModel):
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None
    skill_gaps: Optional[Dict[str, Any]] = None
    improvement_plan: Optional[str] = None

class ReflectionCreate(ReflectionBase):
    application_id: str

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


# ---------------
# Application
# ---------------
class ApplicationBase(BaseModel):
    company_name: str = Field(..., max_length=255)
    role_title: str = Field(..., max_length=255)
    applied_source: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    status: str = Field(default="Applied", max_length=50)
    applied_date: Optional[date] = None

class ApplicationCreate(ApplicationBase):
    resume_version_id: Optional[str] = None

class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=255)
    role_title: Optional[str] = Field(None, max_length=255)
    applied_source: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)
    applied_date: Optional[date] = None
    resume_version_id: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: str
    resume_version_id: Optional[str] = None
    applied_date: date
    created_at: datetime
    updated_at: datetime

    stages: List[ApplicationStageResponse] = []
    outcome: Optional[OutcomeResponse] = None
    reflection: Optional[ReflectionResponse] = None

    model_config = ConfigDict(from_attributes=True)
