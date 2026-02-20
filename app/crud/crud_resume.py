from app.crud.crud_base import CRUDBase
from app.models.resume import ResumeVersion
from app.schemas.resume import ResumeVersionCreate, ResumeVersionUpdate

class CRUDResumeVersion(CRUDBase[ResumeVersion, ResumeVersionCreate, ResumeVersionUpdate]):
    pass

resume_version = CRUDResumeVersion(ResumeVersion)
