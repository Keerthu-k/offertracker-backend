from app.crud.crud_base import CRUDBase
from app.models.job import JobPosting
from app.schemas.job import JobPostingCreate, JobPostingUpdate

class CRUDJobPosting(CRUDBase[JobPosting, JobPostingCreate, JobPostingUpdate]):
    pass

job_posting = CRUDJobPosting(JobPosting)
