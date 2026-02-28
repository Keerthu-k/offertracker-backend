from app.crud.crud_resume import resume_version
from app.crud.crud_application import application, application_stage, outcome, reflection
from app.crud.crud_user import user
from app.crud.crud_social import follow, group, group_member, post, reaction
from app.crud.crud_gamification import milestone, user_milestone
from app.crud.crud_contact import contact
from app.crud.crud_tag import tag, application_tag
from app.crud.crud_reminder import reminder
from app.crud.crud_document import document
from app.crud.crud_activity import activity_log
from app.crud.crud_saved_job import saved_job

__all__ = [
    "resume_version",
    "application",
    "application_stage",
    "outcome",
    "reflection",
    "user",
    "follow",
    "group",
    "group_member",
    "post",
    "reaction",
    "milestone",
    "user_milestone",
    "contact",
    "tag",
    "application_tag",
    "reminder",
    "document",
    "activity_log",
    "saved_job",
]
