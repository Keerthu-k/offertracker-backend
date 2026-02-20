from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app import crud, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.ApplicationResponse])
async def read_applications(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve applications."""
    applications = await crud.application.get_multi(db, skip=skip, limit=limit)
    # Note: For nested relationships like stages, outcome, reflection, you need eager loading
    # if you want them returned in a single query. Otherwise, accessing them here might trigger
    # lazy load exceptions in async context. Let's assume we do eager loading in complex cases,
    # or just return basic info here. In a real app we'd define a specific CRUD method for this.
    return applications

@router.post("/", response_model=schemas.ApplicationResponse)
async def create_application(
    *,
    db: AsyncSession = Depends(get_db),
    application_in: schemas.ApplicationCreate,
) -> Any:
    """Create new application."""
    job = await crud.job_posting.get(db=db, id=application_in.job_posting_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    
    if application_in.resume_version_id:
        resume = await crud.resume_version.get(db=db, id=application_in.resume_version_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume version not found")

    application = await crud.application.create(db=db, obj_in=application_in)
    await db.refresh(application, ["stages", "outcome", "reflection"])
    return application

@router.get("/{id}", response_model=schemas.ApplicationResponse)
async def read_application(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
) -> Any:
    """Get application by ID."""
    application = await crud.application.get(db=db, id=id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Eagerly load the nested items or refresh
    await db.refresh(application, ["stages", "outcome", "reflection"])
    return application

@router.put("/{id}", response_model=schemas.ApplicationResponse)
async def update_application(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    application_in: schemas.ApplicationUpdate,
) -> Any:
    """Update an application."""
    application = await crud.application.get(db=db, id=id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    application = await crud.application.update(db=db, db_obj=application, obj_in=application_in)
    return application

# --- Stages ---
@router.post("/{id}/stages", response_model=schemas.ApplicationStageResponse)
async def add_stage(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    stage_in: schemas.ApplicationStageCreate,
) -> Any:
    """Add a stage to an application."""
    if id != stage_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    application = await crud.application.get(db=db, id=id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    stage = await crud.application_stage.create(db=db, obj_in=stage_in)
    return stage

# --- Outcomes ---
@router.post("/{id}/outcome", response_model=schemas.OutcomeResponse)
async def set_outcome(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    outcome_in: schemas.OutcomeCreate,
) -> Any:
    """Set the outcome of an application."""
    if id != outcome_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    outcome = await crud.outcome.create(db=db, obj_in=outcome_in)
    return outcome

# --- Reflections ---
@router.post("/{id}/reflection", response_model=schemas.ReflectionResponse)
async def add_reflection(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    reflection_in: schemas.ReflectionCreate,
) -> Any:
    """Add a reflection to an application."""
    if id != reflection_in.application_id:
        raise HTTPException(status_code=400, detail="Path ID does not match body ID")
    reflection = await crud.reflection.create(db=db, obj_in=reflection_in)
    return reflection
