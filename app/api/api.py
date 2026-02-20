from fastapi import APIRouter
from app.api.endpoints import companies, jobs, resumes, applications

api_router = APIRouter()
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
