"""CRUD helpers for the Saved Jobs table."""

from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDSavedJob(CRUDBase):
    """Saved-job–specific queries."""

    def get_user_saved_jobs(
        self,
        db: Client,
        user_id: str,
        *,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return saved jobs with optional filters, newest first."""
        query = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
        )
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        resp = (
            query
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
            .execute()
        )
        return resp.data or []

    def count_user_saved_jobs(self, db: Client, user_id: str) -> int:
        resp = (
            db.table(self.table_name)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return resp.count or 0

    def count_converted(self, db: Client, user_id: str) -> int:
        """Count saved jobs that have been converted to applications."""
        resp = (
            db.table(self.table_name)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "Converted")
            .execute()
        )
        return resp.count or 0


saved_job = CRUDSavedJob("saved_jobs")
