"""CRUD helpers for Application Documents."""

from typing import Any, Dict, List

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDDocument(CRUDBase):
    """Document-specific queries."""

    def get_for_application(
        self, db: Client, application_id: str
    ) -> List[Dict[str, Any]]:
        """Return all documents attached to an application."""
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("application_id", application_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []


document = CRUDDocument("application_documents")
