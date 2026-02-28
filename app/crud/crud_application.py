from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDApplication(CRUDBase):
    """Application-specific helpers (e.g. fetch with nested relations)."""

    def get_with_relations(self, db: Client, id: str) -> Optional[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*, application_stages(*), outcomes(*), reflections(*)")
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            return None
        row = resp.data
        row["stages"] = row.pop("application_stages", []) or []
        outcomes = row.pop("outcomes", None) or []
        row["outcome"] = (
            outcomes[0]
            if isinstance(outcomes, list) and outcomes
            else (outcomes if not isinstance(outcomes, list) else None)
        )
        reflections_list = row.pop("reflections", None) or []
        row["reflection"] = (
            reflections_list[0]
            if isinstance(reflections_list, list) and reflections_list
            else (reflections_list if not isinstance(reflections_list, list) else None)
        )
        return row

    def get_multi_with_relations(
        self, db: Client, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*, application_stages(*), outcomes(*), reflections(*)")
            .eq("user_id", user_id)
            .range(skip, skip + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )
        rows: list = resp.data or []
        for row in rows:
            row["stages"] = row.pop("application_stages", []) or []
            outcomes = row.pop("outcomes", None) or []
            row["outcome"] = outcomes[0] if outcomes else None
            reflections_list = row.pop("reflections", None) or []
            row["reflection"] = reflections_list[0] if reflections_list else None
        return rows


application = CRUDApplication("applications")
application_stage = CRUDBase("application_stages")
outcome = CRUDBase("outcomes")
reflection = CRUDBase("reflections")
