"""CRUD helpers for the Reminders system."""

from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDReminder(CRUDBase):
    """Reminder-specific queries."""

    def get_user_reminders(
        self,
        db: Client,
        user_id: str,
        *,
        is_completed: Optional[bool] = None,
        reminder_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve reminders with optional filters, ordered by remind_at."""
        query = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
        )
        if is_completed is not None:
            query = query.eq("is_completed", is_completed)
        if reminder_type:
            query = query.eq("reminder_type", reminder_type)
        resp = (
            query
            .order("remind_at")
            .range(skip, skip + limit - 1)
            .execute()
        )
        return resp.data or []

    def get_upcoming(
        self, db: Client, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Upcoming incomplete reminders, soonest first."""
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_completed", False)
            .order("remind_at")
            .range(0, limit - 1)
            .execute()
        )
        return resp.data or []

    def mark_completed(
        self, db: Client, reminder_id: str
    ) -> Dict[str, Any]:
        """Mark a reminder as completed with a timestamp."""
        from datetime import datetime, timezone

        resp = (
            db.table(self.table_name)
            .update({
                "is_completed": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", reminder_id)
            .execute()
        )
        return resp.data[0] if resp.data else {}

    def count_pending(self, db: Client, user_id: str) -> int:
        resp = (
            db.table(self.table_name)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("is_completed", False)
            .execute()
        )
        return resp.count or 0


reminder = CRUDReminder("reminders")
