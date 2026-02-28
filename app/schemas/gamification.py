from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class MilestoneResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    criteria: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserMilestoneResponse(BaseModel):
    id: str
    user_id: str
    milestone_id: str
    reached_at: datetime
    milestone: Optional[MilestoneResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CommunityMemberEntry(BaseModel):
    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    streak_days: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserStatsResponse(BaseModel):
    total_applications: int = 0
    total_offers: int = 0
    total_rejections: int = 0
    total_reflections: int = 0
    total_stages: int = 0
    streak_days: int = 0
    milestones_reached: int = 0
