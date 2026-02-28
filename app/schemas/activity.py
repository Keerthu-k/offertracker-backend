"""Pydantic schemas for the Activity Log (automatic timeline)."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


# ------------------------------------------------------------------ #
# Response only — activity log entries are created internally, never
# directly by the user.
# ------------------------------------------------------------------ #

class ActivityLogResponse(BaseModel):
    id: str
    user_id: str
    application_id: Optional[str] = None
    action: str
    description: str
    metadata: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
