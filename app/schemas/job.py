from pydantic import BaseModel, ConfigDict, HttpUrl, Field
from typing import Optional
from datetime import datetime
from app.schemas.company import CompanyResponse

class JobPostingBase(BaseModel):
    title: str = Field(..., max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    requirements: Optional[str] = None

class JobPostingCreate(JobPostingBase):
    company_id: str

class JobPostingUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    requirements: Optional[str] = None

class JobPostingResponse(JobPostingBase):
    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class JobPostingWithCompanyResponse(JobPostingResponse):
    company: CompanyResponse
