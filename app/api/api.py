from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    users,
    resumes,
    applications,
    social,
    gamification,
    upload,
    contacts,
    tags,
    reminders,
    documents,
    analytics,
    saved_jobs,
)

api_router = APIRouter()

# Public auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Protected resource routes
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["reminders"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(gamification.router, prefix="/progress", tags=["progress"])
api_router.include_router(saved_jobs.router, prefix="/saved-jobs", tags=["saved-jobs"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
