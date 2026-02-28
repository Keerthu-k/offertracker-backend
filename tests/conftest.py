import copy
import re as regex_module
import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# In-memory fake "database" used by the mock Supabase client
# ---------------------------------------------------------------------------
_tables: dict[str, list[dict]] = {}

TEST_USER = {
    "id": "test-user-id",
    "email": "test@example.com",
    "username": "testuser",
    "display_name": "Test User",
    "password_hash": "$2b$12$placeholder",
    "bio": None,
    "is_profile_public": True,
    "streak_days": 0,
    "last_active_date": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


def _reset_tables():
    """Clear all in-memory tables and seed defaults."""
    _tables.clear()
    for name in (
        "users",
        "resume_versions",
        "applications",
        "application_stages",
        "outcomes",
        "reflections",
        "follows",
        "groups",
        "group_members",
        "milestones",
        "user_milestones",
        "shared_posts",
        "post_reactions",
    ):
        _tables[name] = []

    # Seed the test user
    _tables["users"].append(dict(TEST_USER))

    # Seed milestones
    _tables["milestones"].extend(
        [
            {
                "id": "ms-getting-started",
                "name": "Getting Started",
                "description": "You created your account and took the first step.",
                "criteria": {"action": "register"},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "id": "ms-first-app",
                "name": "First Application",
                "description": "You applied to your first role. The journey begins.",
                "criteria": {"action": "create_application", "count": 1},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        ]
    )


# ---------------------------------------------------------------------------
# Tiny helpers that mimic supabase-py chained query builder
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _FakeInsertBuilder:
    def __init__(self, table_name: str, rows: list[dict]):
        self._table = table_name
        self._store = rows

    def __call__(self, payload):
        self._payload = payload
        return self

    def execute(self):
        row = copy.deepcopy(self._payload)
        row.setdefault("id", str(uuid.uuid4()))
        now = datetime.now(timezone.utc).isoformat()
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        # Table-specific defaults
        if self._table == "applications":
            row.setdefault("applied_date", str(date.today()))
            row.setdefault("status", "Applied")
        if self._table == "application_stages":
            row.setdefault("stage_date", str(date.today()))
        if self._table == "group_members":
            row.setdefault("joined_at", now)
        if self._table == "user_milestones":
            row.setdefault("reached_at", now)
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
                row["updated_at"] = datetime.now(timezone.utc).isoformat()
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
        to_delete = [
            row
            for row in self._store
            if all(row.get(c) == v for c, v in self._filters)
        ]
        for row in to_delete:
            self._store.remove(row)
        return _FakeResponse(to_delete)


class _FakeSelectBuilder:
    """Handles .select('*'), .select('*, child_table(*)') and count modes."""

    def __init__(
        self, table_name: str, select_expr: str, count_mode: str | None = None
    ):
        self._table = table_name
        self._select = select_expr
        self._count_mode = count_mode
        self._filters: list[tuple] = []
        self._or_filter: str | None = None
        self._in_filters: list[tuple] = []
        self._range_start: int | None = None
        self._range_end: int | None = None
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._single = False

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def or_(self, expr):
        self._or_filter = expr
        return self

    def in_(self, col, values):
        self._in_filters.append((col, values))
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
        rows = copy.deepcopy(_tables.get(self._table, []))

        # Apply eq filters
        for col, val in self._filters:
            rows = [r for r in rows if r.get(col) == val]

        # Apply in_ filters
        for col, values in self._in_filters:
            rows = [r for r in rows if r.get(col) in values]

        # Apply or_ filter (simplified ilike support)
        if self._or_filter:
            parts = self._or_filter.split(",")
            matched = []
            for row in rows:
                for part in parts:
                    m = regex_module.match(r"(\w+)\.ilike\.%(.+)%", part.strip())
                    if m:
                        field, val = m.groups()
                        if val.lower() in str(row.get(field, "")).lower():
                            matched.append(row)
                            break
            rows = matched

        # Embed related tables if requested
        related = regex_module.findall(r"(\w+)\(\*\)", self._select)
        for rel in related:
            rel_rows = _tables.get(rel, [])
            for row in rows:
                matches = []
                parent_id = row.get("id")
                for r in rel_rows:
                    # Related row has FK pointing to parent
                    if any(
                        r.get(k) == parent_id
                        for k in r
                        if k.endswith("_id") and k != "id"
                    ):
                        matches.append(copy.deepcopy(r))
                        continue
                    # Parent has FK pointing to related row
                    rel_id = r.get("id")
                    if rel_id and any(
                        row.get(k) == rel_id
                        for k in row
                        if k.endswith("_id") and k != "id"
                    ):
                        matches.append(copy.deepcopy(r))
                row[rel] = matches

        # Ordering
        if self._order_col:
            rows = sorted(
                rows,
                key=lambda r: r.get(self._order_col, ""),
                reverse=self._order_desc,
            )

        # Range
        if self._range_start is not None and self._range_end is not None:
            rows = rows[self._range_start : self._range_end + 1]

        count = len(rows) if self._count_mode else None

        if self._single:
            return _FakeResponse(rows[0] if rows else None, count=count)

        return _FakeResponse(rows, count=count)


class _FakeStorageBucket:
    def upload(self, path, content, options=None):
        return {"Key": path}

    def get_public_url(self, path):
        return f"https://fake-storage.supabase.co/resumes/{path}"


class _FakeStorage:
    def from_(self, bucket):
        return _FakeStorageBucket()


class _FakeTableBuilder:
    def __init__(self, table_name: str):
        self._table = table_name
        if table_name not in _tables:
            _tables[table_name] = []

    def select(self, expr="*", count=None):
        return _FakeSelectBuilder(self._table, expr, count_mode=count)

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

    def __init__(self):
        self.storage = _FakeStorage()

    def table(self, name: str):
        return _FakeTableBuilder(name)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _override_get_supabase():
    return FakeSupabaseClient()


def _override_get_current_user():
    return dict(TEST_USER)


app.dependency_overrides[get_supabase] = _override_get_supabase
app.dependency_overrides[get_current_user] = _override_get_current_user


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
