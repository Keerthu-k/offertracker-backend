from app.schemas.enums import (
    ApplicationStatus, StageType, StageResult,
    JobType, WorkMode, Priority, Source,
    ContactType, DocumentType, ReminderType,
    ActivityAction,
    PostType, ReactionType, GroupRole,
)
from app.schemas.resume import ResumeVersionCreate, ResumeVersionUpdate, ResumeVersionResponse
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    ApplicationStageCreate, ApplicationStageUpdate, ApplicationStageResponse,
    OutcomeCreate, OutcomeUpdate, OutcomeResponse,
    ReflectionCreate, ReflectionUpdate, ReflectionResponse,
)
from app.schemas.user import (
    UserRegister, UserLogin, UserUpdate, UserResponse, UserPublicProfile, TokenResponse,
)
from app.schemas.social import (
    FollowResponse, FollowStats,
    GroupCreate, GroupUpdate, GroupResponse, GroupMemberResponse,
    PostCreate, PostUpdate, PostResponse,
    ReactionCreate, ReactionResponse,
)
from app.schemas.gamification import (
    MilestoneResponse, UserMilestoneResponse, CommunityMemberEntry, UserStatsResponse,
    PipelineBreakdown, SourceEffectiveness, WeeklyTrend, SalaryInsight,
    AnalyticsDashboardResponse,
)
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.schemas.tag import TagCreate, TagUpdate, TagResponse, ApplicationTagResponse
from app.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderResponse
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from app.schemas.activity import ActivityLogResponse
from app.schemas.saved_job import SavedJobCreate, SavedJobUpdate, SavedJobResponse

__all__ = [
    # Enums
    "ApplicationStatus", "StageType", "StageResult",
    "JobType", "WorkMode", "Priority", "Source",
    "ContactType", "DocumentType", "ReminderType",
    "ActivityAction",
    "PostType", "ReactionType", "GroupRole",
    # Resume
    "ResumeVersionCreate", "ResumeVersionUpdate", "ResumeVersionResponse",
    # Application
    "ApplicationCreate", "ApplicationUpdate", "ApplicationResponse",
    "ApplicationStageCreate", "ApplicationStageUpdate", "ApplicationStageResponse",
    "OutcomeCreate", "OutcomeUpdate", "OutcomeResponse",
    "ReflectionCreate", "ReflectionUpdate", "ReflectionResponse",
    # User
    "UserRegister", "UserLogin", "UserUpdate", "UserResponse",
    "UserPublicProfile", "TokenResponse",
    # Social
    "FollowResponse", "FollowStats",
    "GroupCreate", "GroupUpdate", "GroupResponse", "GroupMemberResponse",
    "PostCreate", "PostUpdate", "PostResponse",
    "ReactionCreate", "ReactionResponse",
    # Progress & Analytics
    "MilestoneResponse", "UserMilestoneResponse",
    "CommunityMemberEntry", "UserStatsResponse",
    "PipelineBreakdown", "SourceEffectiveness", "WeeklyTrend",
    "SalaryInsight", "AnalyticsDashboardResponse",
    # Contacts
    "ContactCreate", "ContactUpdate", "ContactResponse",
    # Tags
    "TagCreate", "TagUpdate", "TagResponse", "ApplicationTagResponse",
    # Reminders
    "ReminderCreate", "ReminderUpdate", "ReminderResponse",
    # Documents
    "DocumentCreate", "DocumentUpdate", "DocumentResponse",
    # Activity
    "ActivityLogResponse",
    # Saved Jobs
    "SavedJobCreate", "SavedJobUpdate", "SavedJobResponse",
]
