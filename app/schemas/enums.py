"""Enumeration types for OfferTracker.

Every enum uses ``str`` + ``Enum`` so values serialise directly as
human-readable strings in JSON responses and are accepted as plain
strings in request bodies.
"""

from enum import Enum


# ------------------------------------------------------------------ #
# Application lifecycle — 7 clear, sequential statuses
# ------------------------------------------------------------------ #

class ApplicationStatus(str, Enum):
    """Where an application sits in the hiring pipeline.

    Happy path:  Open → Applied → Shortlisted → Interview → Offer → Closed
    At any point the application may be Rejected or Closed.
    """
    OPEN         = "Open"
    APPLIED      = "Applied"
    SHORTLISTED  = "Shortlisted"
    INTERVIEW    = "Interview"
    OFFER        = "Offer"
    REJECTED     = "Rejected"
    CLOSED       = "Closed"


# ------------------------------------------------------------------ #
# Interview stages
# ------------------------------------------------------------------ #

class StageType(str, Enum):
    """Classification of an interview round."""
    RECRUITER_CALL   = "Recruiter Call"
    PHONE_SCREEN     = "Phone Screen"
    TECHNICAL        = "Technical"
    CODING_CHALLENGE = "Coding Challenge"
    TAKE_HOME        = "Take-Home"
    SYSTEM_DESIGN    = "System Design"
    BEHAVIORAL       = "Behavioral"
    PANEL            = "Panel"
    ONSITE           = "Onsite"
    FINAL_ROUND      = "Final Round"
    OTHER            = "Other"


class StageResult(str, Enum):
    """Result of a single interview stage."""
    PENDING   = "Pending"
    PASSED    = "Passed"
    FAILED    = "Failed"
    CANCELLED = "Cancelled"


# ------------------------------------------------------------------ #
# Job descriptors
# ------------------------------------------------------------------ #

class JobType(str, Enum):
    """Employment arrangement."""
    FULL_TIME  = "Full-time"
    PART_TIME  = "Part-time"
    CONTRACT   = "Contract"
    INTERNSHIP = "Internship"
    FREELANCE  = "Freelance"


class WorkMode(str, Enum):
    """Work location model."""
    REMOTE  = "Remote"
    HYBRID  = "Hybrid"
    ON_SITE = "On-site"


class Priority(str, Enum):
    """Importance level for sorting and focus."""
    HIGH   = "High"
    MEDIUM = "Medium"
    LOW    = "Low"


class Source(str, Enum):
    """Where the user discovered the job opportunity."""
    LINKEDIN        = "LinkedIn"
    INDEED          = "Indeed"
    GLASSDOOR       = "Glassdoor"
    COMPANY_WEBSITE = "Company Website"
    REFERRAL        = "Referral"
    JOB_BOARD       = "Job Board"
    RECRUITER       = "Recruiter"
    NETWORKING      = "Networking"
    CAREER_FAIR     = "Career Fair"
    OTHER           = "Other"


# ------------------------------------------------------------------ #
# Contacts & networking
# ------------------------------------------------------------------ #

class ContactType(str, Enum):
    """Relationship type for a networking contact."""
    RECRUITER      = "Recruiter"
    HIRING_MANAGER = "Hiring Manager"
    REFERRAL       = "Referral"
    HR             = "HR"
    PEER           = "Peer"
    OTHER          = "Other"


# ------------------------------------------------------------------ #
# Documents
# ------------------------------------------------------------------ #

class DocumentType(str, Enum):
    """Type of document attached to an application."""
    RESUME       = "Resume"
    COVER_LETTER = "Cover Letter"
    PORTFOLIO    = "Portfolio"
    REFERENCE    = "Reference"
    OTHER        = "Other"


# ------------------------------------------------------------------ #
# Reminders
# ------------------------------------------------------------------ #

class ReminderType(str, Enum):
    """Category of reminder."""
    FOLLOW_UP = "Follow-up"
    DEADLINE  = "Deadline"
    INTERVIEW = "Interview"
    GENERAL   = "General"


# ------------------------------------------------------------------ #
# Activity log
# ------------------------------------------------------------------ #

class ActivityAction(str, Enum):
    """Action recorded in the activity timeline."""
    APPLICATION_CREATED = "Application Created"
    APPLICATION_UPDATED = "Application Updated"
    STATUS_CHANGED      = "Status Changed"
    STAGE_ADDED         = "Stage Added"
    STAGE_UPDATED       = "Stage Updated"
    OFFER_ADDED         = "Offer Added"
    REFLECTION_ADDED    = "Reflection Added"
    CONTACT_ADDED       = "Contact Added"
    DOCUMENT_ADDED      = "Document Added"
    REMINDER_CREATED    = "Reminder Created"
    REMINDER_COMPLETED  = "Reminder Completed"
    TAG_ASSIGNED        = "Tag Assigned"


# ------------------------------------------------------------------ #
# Social / community
# ------------------------------------------------------------------ #

class PostType(str, Enum):
    """Content type for shared posts."""
    UPDATE      = "Update"
    TIP         = "Tip"
    MILESTONE   = "Milestone"
    QUESTION    = "Question"
    RESOURCE    = "Resource"
    CELEBRATION = "Celebration"


class ReactionType(str, Enum):
    """Reaction type on a post."""
    LIKE       = "Like"
    CELEBRATE  = "Celebrate"
    SUPPORT    = "Support"
    INSIGHTFUL = "Insightful"


class GroupRole(str, Enum):
    """Role within a group."""
    ADMIN  = "admin"
    MEMBER = "member"
