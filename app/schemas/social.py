from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


# ---------- Follows ----------

class FollowResponse(BaseModel):
    id: str
    follower_id: str
    following_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowStats(BaseModel):
    followers_count: int = 0
    following_count: int = 0


# ---------- Groups ----------

class GroupCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_public: bool = True


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_public: Optional[bool] = None


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    is_public: bool = True
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupMemberResponse(BaseModel):
    id: str
    group_id: str
    user_id: str
    role: str = "member"
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Posts ----------

class PostCreate(BaseModel):
    group_id: Optional[str] = None
    post_type: str = Field(default="update", max_length=30)
    title: Optional[str] = Field(None, max_length=255)
    content: str
    is_public: bool = True


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    is_public: Optional[bool] = None


class PostResponse(BaseModel):
    id: str
    user_id: str
    group_id: Optional[str] = None
    post_type: str
    title: Optional[str] = None
    content: str
    is_public: bool = True
    reaction_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReactionCreate(BaseModel):
    reaction: str = Field(default="like", max_length=20)


class ReactionResponse(BaseModel):
    id: str
    post_id: str
    user_id: str
    reaction: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
