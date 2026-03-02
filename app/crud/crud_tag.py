"""CRUD helpers for the Tags system."""

from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDTag(CRUDBase):
    """Tag-specific queries."""

    def get_user_tags(
        self, db: Client, user_id: str
    ) -> List[Dict[str, Any]]:
        """Return all tags belonging to a user."""
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .order("name")
            .execute()
        )
        return resp.data or []

    def get_by_name(
        self, db: Client, user_id: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Look up a tag by name (unique per user)."""
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .eq("name", name)
            .maybe_single()
            .execute()
        )
        return resp.data if resp else None

    def count_user_tags(self, db: Client, user_id: str) -> int:
        resp = (
            db.table(self.table_name)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return resp.count or 0


class CRUDApplicationTag(CRUDBase):
    """Join-table helpers for application ↔ tag associations."""

    def get_tags_for_application(
        self, db: Client, application_id: str
    ) -> List[Dict[str, Any]]:
        """Return tags assigned to an application, including tag details."""
        resp = (
            db.table(self.table_name)
            .select("*, tags(*)")
            .eq("application_id", application_id)
            .execute()
        )
        rows = resp.data or []
        for row in rows:
            row["tag"] = row.pop("tags", None)
        return rows

    def get_applications_for_tag(
        self, db: Client, tag_id: str
    ) -> List[Dict[str, Any]]:
        """Return application_tag rows for a given tag."""
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("tag_id", tag_id)
            .execute()
        )
        return resp.data or []

    def assign(
        self, db: Client, application_id: str, tag_id: str
    ) -> Dict[str, Any]:
        """Assign a tag to an application."""
        return self.create(
            db=db,
            data={"application_id": application_id, "tag_id": tag_id},
        )

    def unassign(
        self, db: Client, application_id: str, tag_id: str
    ) -> bool:
        """Remove a tag from an application."""
        resp = (
            db.table(self.table_name)
            .delete()
            .eq("application_id", application_id)
            .eq("tag_id", tag_id)
            .execute()
        )
        return bool(resp.data)


tag = CRUDTag("tags")
application_tag = CRUDApplicationTag("application_tags")
