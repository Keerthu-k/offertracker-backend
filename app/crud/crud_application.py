from app.crud.crud_base import CRUDBase
from app.models.application import Application, ApplicationStage, Outcome, Reflection
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate,
    ApplicationStageCreate, ApplicationStageUpdate,
    OutcomeCreate, OutcomeUpdate,
    ReflectionCreate, ReflectionUpdate
)

class CRUDApplication(CRUDBase[Application, ApplicationCreate, ApplicationUpdate]):
    pass

class CRUDApplicationStage(CRUDBase[ApplicationStage, ApplicationStageCreate, ApplicationStageUpdate]):
    pass

class CRUDOutcome(CRUDBase[Outcome, OutcomeCreate, OutcomeUpdate]):
    pass

class CRUDReflection(CRUDBase[Reflection, ReflectionCreate, ReflectionUpdate]):
    pass

application = CRUDApplication(Application)
application_stage = CRUDApplicationStage(ApplicationStage)
outcome = CRUDOutcome(Outcome)
reflection = CRUDReflection(Reflection)
