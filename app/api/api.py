from fastapi import APIRouter
from app.api.endpoints import resumes, applications

api_router = APIRouter()
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
