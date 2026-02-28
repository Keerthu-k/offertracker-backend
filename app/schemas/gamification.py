from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
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
    total_contacts: int = 0
    total_reminders_pending: int = 0


# ------------------------------------------------------------------ #
# Analytics — pipeline funnel, source effectiveness, trends
# ------------------------------------------------------------------ #

class PipelineBreakdown(BaseModel):
    """Count of applications per status."""
    status: str
    count: int


class SourceEffectiveness(BaseModel):
    """Performance metrics per application source."""
    source: str
    applied: int = 0
    interviews: int = 0
    offers: int = 0


class WeeklyTrend(BaseModel):
    """Application activity per ISO week."""
    week: str
    applications: int = 0
    stages: int = 0


class SalaryInsight(BaseModel):
    """Aggregated salary data across applications and offers."""
    applications_with_salary: int = 0
    average_expected_min: Optional[float] = None
    average_expected_max: Optional[float] = None
    offers_with_salary: int = 0
    average_offered: Optional[float] = None
    highest_offer: Optional[int] = None
    currency: str = "USD"


class AnalyticsDashboardResponse(BaseModel):
    """Comprehensive analytics dashboard for the applicant."""
    pipeline: List[PipelineBreakdown] = []
    response_rate: float = 0.0
    interview_rate: float = 0.0
    offer_rate: float = 0.0
    source_breakdown: List[SourceEffectiveness] = []
    weekly_trend: List[WeeklyTrend] = []
    salary_insights: SalaryInsight = SalaryInsight()
    top_companies: List[Dict[str, Any]] = []
