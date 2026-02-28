"""CRUD helpers for the Contacts / Networking tracker."""

from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDContact(CRUDBase):
    """Contact-specific queries."""

    def get_user_contacts(
        self,
        db: Client,
        user_id: str,
        *,
        application_id: Optional[str] = None,
        contact_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve contacts with optional filters."""
        query = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
        )
        if application_id:
            query = query.eq("application_id", application_id)
        if contact_type:
            query = query.eq("contact_type", contact_type)
        resp = (
            query
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
            .execute()
        )
        return resp.data or []

    def count_user_contacts(self, db: Client, user_id: str) -> int:
        resp = (
            db.table(self.table_name)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return resp.count or 0


contact = CRUDContact("contacts")
