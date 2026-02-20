from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app import crud, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.JobPostingResponse])
async def read_jobs(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve job postings."""
    jobs = await crud.job_posting.get_multi(db, skip=skip, limit=limit)
    return jobs

@router.post("/", response_model=schemas.JobPostingResponse)
async def create_job(
    *,
    db: AsyncSession = Depends(get_db),
    job_in: schemas.JobPostingCreate,
) -> Any:
    """Create new job posting."""
    company = await crud.company.get(db=db, id=job_in.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    job = await crud.job_posting.create(db=db, obj_in=job_in)
    return job

@router.get("/{id}", response_model=schemas.JobPostingWithCompanyResponse)
async def read_job(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
) -> Any:
    """Get job posting by ID."""
    job = await crud.job_posting.get(db=db, id=id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    # To include the company, ensure relationships are eagerly loaded, or access them within the transaction
    # Since we use lazy loading by default, we just access `job.company` which needs an active session.
    # We will let the Pydantic schema serialize it.
    await db.refresh(job, ["company"])
    return job

@router.put("/{id}", response_model=schemas.JobPostingResponse)
async def update_job(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    job_in: schemas.JobPostingUpdate,
) -> Any:
    """Update a job posting."""
    job = await crud.job_posting.get(db=db, id=id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    job = await crud.job_posting.update(db=db, db_obj=job, obj_in=job_in)
    return job
