from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date


class UserRegister(BaseModel):
    email: str = Field(..., max_length=255)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    is_profile_public: Optional[bool] = None
    profile_visibility: Optional[str] = Field(
        None,
        pattern="^(private|followers|groups|public)$",
    )


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    is_profile_public: bool = False
    profile_visibility: str = "private"
    streak_days: int = 0
    last_active_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class UserPublicProfile(BaseModel):
    id: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_visibility: str = "private"
    streak_days: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
