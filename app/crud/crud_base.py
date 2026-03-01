"""
Generic CRUD helpers that talk to Supabase via the Python client.
Each method receives a `supabase.Client` and operates on a table name.

All methods include error handling and logging.  When a Supabase call
fails, a `DatabaseError` is raised so the endpoint layer can translate
it into an appropriate HTTP response.
"""

from typing import Any, Dict, List, Optional

from supabase import Client

from app.core.logging import logger


class DatabaseError(Exception):
    """Raised when a Supabase operation fails unexpectedly."""

    def __init__(self, message: str, table: str = "", operation: str = ""):
        self.table = table
        self.operation = operation
        super().__init__(message)


class CRUDBase:
    def __init__(self, table_name: str):
        self.table_name = table_name

    # ---------- READ ----------
    def get(self, db: Client, id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = (
                db.table(self.table_name)
                .select("*")
                .eq("id", id)
                .maybe_single()
                .execute()
            )
            if resp is None:
                return None
            return resp.data
        except Exception as exc:
            logger.error("DB get(%s, id=%s) failed: %s", self.table_name, id, exc)
            raise DatabaseError(
                f"Failed to fetch record from {self.table_name}",
                table=self.table_name,
                operation="get",
            ) from exc

    def get_multi(
        self, db: Client, *, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            resp = (
                db.table(self.table_name)
                .select("*")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return resp.data or []
        except Exception as exc:
            logger.error("DB get_multi(%s) failed: %s", self.table_name, exc)
            raise DatabaseError(
                f"Failed to list records from {self.table_name}",
                table=self.table_name,
                operation="get_multi",
            ) from exc

    def get_by_field(
        self, db: Client, *, field: str, value: Any
    ) -> Optional[Dict[str, Any]]:
        try:
            resp = (
                db.table(self.table_name)
                .select("*")
                .eq(field, value)
                .maybe_single()
                .execute()
            )
            if resp is None:
                return None
            return resp.data
        except Exception as exc:
            logger.error(
                "DB get_by_field(%s, %s=%s) failed: %s",
                self.table_name, field, value, exc,
            )
            raise DatabaseError(
                f"Failed to fetch record from {self.table_name} by {field}",
                table=self.table_name,
                operation="get_by_field",
            ) from exc

    def get_multi_by_field(
        self, db: Client, *, field: str, value: Any, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            resp = (
                db.table(self.table_name)
                .select("*")
                .eq(field, value)
                .range(skip, skip + limit - 1)
                .execute()
            )
            return resp.data or []
        except Exception as exc:
            logger.error(
                "DB get_multi_by_field(%s, %s=%s) failed: %s",
                self.table_name, field, value, exc,
            )
            raise DatabaseError(
                f"Failed to list records from {self.table_name} by {field}",
                table=self.table_name,
                operation="get_multi_by_field",
            ) from exc

    # ---------- CREATE ----------
    def create(self, db: Client, *, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Filter out None values so DB defaults kick in
            payload = {k: v for k, v in data.items() if v is not None}
            resp = db.table(self.table_name).insert(payload).execute()
            if not resp.data:
                logger.error(
                    "DB create(%s) returned empty data. Payload: %s",
                    self.table_name, payload,
                )
                raise DatabaseError(
                    f"Insert into {self.table_name} returned no data",
                    table=self.table_name,
                    operation="create",
                )
            return resp.data[0]
        except DatabaseError:
            raise
        except Exception as exc:
            logger.error("DB create(%s) failed: %s", self.table_name, exc)
            raise DatabaseError(
                f"Failed to create record in {self.table_name}",
                table=self.table_name,
                operation="create",
            ) from exc

    # ---------- UPDATE ----------
    def update(self, db: Client, *, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            payload = {k: v for k, v in data.items() if v is not None}
            resp = db.table(self.table_name).update(payload).eq("id", id).execute()
            if not resp.data:
                logger.warning(
                    "DB update(%s, id=%s) matched no rows. Payload: %s",
                    self.table_name, id, payload,
                )
                raise DatabaseError(
                    f"No record found in {self.table_name} with id={id} to update",
                    table=self.table_name,
                    operation="update",
                )
            return resp.data[0]
        except DatabaseError:
            raise
        except Exception as exc:
            logger.error("DB update(%s, id=%s) failed: %s", self.table_name, id, exc)
            raise DatabaseError(
                f"Failed to update record in {self.table_name}",
                table=self.table_name,
                operation="update",
            ) from exc

    # ---------- DELETE ----------
    def remove(self, db: Client, *, id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = db.table(self.table_name).delete().eq("id", id).execute()
            return resp.data[0] if resp.data else None
        except Exception as exc:
            logger.error("DB remove(%s, id=%s) failed: %s", self.table_name, id, exc)
            raise DatabaseError(
                f"Failed to delete record from {self.table_name}",
                table=self.table_name,
                operation="remove",
            ) from exc
