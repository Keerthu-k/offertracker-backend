"""
Generic CRUD helpers that talk to Supabase via the Python client.
Each method receives a `supabase.Client` and operates on a table name.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from supabase import Client

T = TypeVar("T")


class CRUDBase:
    def __init__(self, table_name: str):
        self.table_name = table_name

    # ---------- READ ----------
    def get(self, db: Client, id: str) -> Optional[Dict[str, Any]]:
        resp = db.table(self.table_name).select("*").eq("id", id).maybe_single().execute()
        return resp.data

    def get_multi(
        self, db: Client, *, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .range(skip, skip + limit - 1)
            .execute()
        )
        return resp.data or []

    # ---------- CREATE ----------
    def create(self, db: Client, *, data: Dict[str, Any]) -> Dict[str, Any]:
        # Filter out None values so DB defaults kick in
        payload = {k: v for k, v in data.items() if v is not None}
        resp = db.table(self.table_name).insert(payload).execute()
        return resp.data[0]

    # ---------- UPDATE ----------
    def update(self, db: Client, *, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {k: v for k, v in data.items() if v is not None}
        resp = db.table(self.table_name).update(payload).eq("id", id).execute()
        return resp.data[0]

    # ---------- DELETE ----------
    def remove(self, db: Client, *, id: str) -> Optional[Dict[str, Any]]:
        resp = db.table(self.table_name).delete().eq("id", id).execute()
        return resp.data[0] if resp.data else None
