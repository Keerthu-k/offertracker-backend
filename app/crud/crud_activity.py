"""CRUD helpers for the Activity Log (automatic timeline).

Activity-log entries are **append-only** — users can read them but never
edit or delete them through the API.  They are created by helper functions
called from application / stage / outcome endpoints.
"""

from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDActivityLog(CRUDBase):
    """Activity-log queries."""

    def get_user_activity(
        self,
        db: Client,
        user_id: str,
        *,
        application_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return a user's activity timeline, newest first."""
        query = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
        )
        if application_id:
            query = query.eq("application_id", application_id)
        resp = (
            query
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
            .execute()
        )
        return resp.data or []


activity_log = CRUDActivityLog("activity_log")


# ------------------------------------------------------------------
# Convenience helper — call from any endpoint to log an action
# ------------------------------------------------------------------

def log_activity(
    db: Client,
    *,
    user_id: str,
    action: str,
    description: str,
    application_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write an activity-log entry.  Non-critical — exceptions are swallowed."""
    try:
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "action": action,
            "description": description,
        }
        if application_id:
            payload["application_id"] = application_id
        if metadata:
            payload["metadata"] = metadata
        resp = db.table("activity_log").insert(payload).execute()
        return resp.data[0] if resp.data else {}
    except Exception:
        return {}
