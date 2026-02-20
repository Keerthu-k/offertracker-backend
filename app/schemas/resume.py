from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class ResumeVersionBase(BaseModel):
    version_name: str = Field(..., max_length=50)
    notes: Optional[str] = None
    file_url: Optional[str] = Field(None, max_length=500)

class ResumeVersionCreate(ResumeVersionBase):
    pass

class ResumeVersionUpdate(BaseModel):
    version_name: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    file_url: Optional[str] = Field(None, max_length=500)

class ResumeVersionResponse(ResumeVersionBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
