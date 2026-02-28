from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    users,
    resumes,
    applications,
    social,
    gamification,
    upload,
)

api_router = APIRouter()

# Public auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Protected resource routes
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(gamification.router, prefix="/progress", tags=["progress"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
