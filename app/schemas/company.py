from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    name: str = Field(..., max_length=255)
    industry: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)

class CompanyResponse(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
