import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.core.database import get_supabase
from app.main import app


# ---------------------------------------------------------------------------
# In-memory fake "database" used by the mock Supabase client
# ---------------------------------------------------------------------------
_tables: dict[str, list[dict]] = {}


def _reset_tables():
    """Clear all in-memory tables."""
    _tables.clear()
    for name in (
        "resume_versions",
        "applications",
        "application_stages",
        "outcomes",
        "reflections",
    ):
        _tables[name] = []


# ---------------------------------------------------------------------------
# Tiny helpers that mimic supabase-py chained query builder
# ---------------------------------------------------------------------------
import uuid
from datetime import datetime, date


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeFilterBuilder:
    """Simulates .eq() / .maybe_single() / .execute() chains."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def maybe_single(self):
        return self  # execute will handle it

    def range(self, start, end):
        self._rows = self._rows[start : end + 1]
        return self

    def order(self, col, *, desc=False):
        self._rows = sorted(
            self._rows, key=lambda r: r.get(col, ""), reverse=desc
        )
        return self

    def execute(self):
        # If maybe_single was called we want to return single or None
        if len(self._rows) <= 1:
            return _FakeResponse(self._rows[0] if self._rows else None)
        return _FakeResponse(self._rows)


class _FakeInsertBuilder:
    def __init__(self, table_name: str, rows: list[dict]):
        self._table = table_name
        self._store = rows

    def __call__(self, payload):
        self._payload = payload
        return self

    def execute(self):
        import copy

        row = copy.deepcopy(self._payload)
        row.setdefault("id", str(uuid.uuid4()))
        now = datetime.utcnow().isoformat()
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        # date defaults
        if self._table == "applications":
            row.setdefault("applied_date", str(date.today()))
            row.setdefault("status", "Applied")
        if self._table == "application_stages":
            row.setdefault("stage_date", str(date.today()))
        self._store.append(row)
        return _FakeResponse([row])


class _FakeUpdateBuilder:
    def __init__(self, store: list[dict]):
        self._store = store
        self._payload: dict = {}
        self._filters: list[tuple] = []

    def __call__(self, payload):
        self._payload = payload
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def execute(self):
        for row in self._store:
            if all(row.get(c) == v for c, v in self._filters):
                row.update({k: v for k, v in self._payload.items() if v is not None})
                row["updated_at"] = datetime.utcnow().isoformat()
                return _FakeResponse([row])
        return _FakeResponse([])


class _FakeDeleteBuilder:
    def __init__(self, store: list[dict]):
        self._store = store
        self._filters: list[tuple] = []

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def execute(self):
        to_delete = []
        for row in self._store:
            if all(row.get(c) == v for c, v in self._filters):
                to_delete.append(row)
        for row in to_delete:
            self._store.remove(row)
        return _FakeResponse(to_delete)


class _FakeSelectBuilder:
    """Handles .select('*') and .select('*, child_table(*)') patterns."""

    def __init__(self, table_name: str, select_expr: str):
        self._table = table_name
        self._select = select_expr
        self._rows: list[dict] = []
        self._filters: list[tuple] = []
        self._range_start: int | None = None
        self._range_end: int | None = None
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._single = False

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def maybe_single(self):
        self._single = True
        return self

    def range(self, start, end):
        self._range_start = start
        self._range_end = end
        return self

    def order(self, col, *, desc=False):
        self._order_col = col
        self._order_desc = desc
        return self

    def execute(self):
        import copy

        rows = copy.deepcopy(_tables.get(self._table, []))

        # Apply filters
        for col, val in self._filters:
            rows = [r for r in rows if r.get(col) == val]

        # Embed related tables if requested (e.g. "*, application_stages(*)")
        import re

        related = re.findall(r"(\w+)\(\*\)", self._select)
        for rel in related:
            rel_rows = _tables.get(rel, [])
            # determine FK column (convention: singular of parent + _id)
            fk_col = self._table.rstrip("s") + "_id"  # e.g. application_id
            if fk_col == "application_id" or True:
                fk_col = self._table.rstrip("s") + "_id"
            for row in rows:
                row[rel] = [
                    copy.deepcopy(r)
                    for r in rel_rows
                    if r.get(fk_col) == row.get("id")
                    or r.get("application_id") == row.get("id")
                ]

        # Ordering
        if self._order_col:
            rows = sorted(
                rows, key=lambda r: r.get(self._order_col, ""), reverse=self._order_desc
            )

        # Range
        if self._range_start is not None and self._range_end is not None:
            rows = rows[self._range_start : self._range_end + 1]

        if self._single:
            return _FakeResponse(rows[0] if rows else None)

        return _FakeResponse(rows)


class _FakeTableBuilder:
    def __init__(self, table_name: str):
        self._table = table_name
        if table_name not in _tables:
            _tables[table_name] = []

    def select(self, expr="*"):
        return _FakeSelectBuilder(self._table, expr)

    def insert(self, payload):
        builder = _FakeInsertBuilder(self._table, _tables[self._table])
        return builder(payload)

    def update(self, payload):
        builder = _FakeUpdateBuilder(_tables[self._table])
        return builder(payload)

    def delete(self):
        return _FakeDeleteBuilder(_tables[self._table])


class FakeSupabaseClient:
    """Mimics the subset of supabase.Client used by our CRUD layer."""

    def table(self, name: str):
        return _FakeTableBuilder(name)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _override_get_supabase():
    return FakeSupabaseClient()


app.dependency_overrides[get_supabase] = _override_get_supabase


@pytest.fixture(autouse=True)
def reset_db():
    _reset_tables()
    yield
    _reset_tables()


@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
