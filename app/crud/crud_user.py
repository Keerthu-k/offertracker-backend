"""User CRUD – extends CRUDBase with email / username lookups and streak helpers."""

from datetime import date
from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDUser(CRUDBase):

    def get_by_email(self, db: Client, email: str) -> Optional[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return resp.data

    def get_by_username(self, db: Client, username: str) -> Optional[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("username", username)
            .maybe_single()
            .execute()
        )
        return resp.data

    def ensure_profile(
        self,
        db: Client,
        *,
        user_id: str,
        email: str,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ensure a public.users profile exists for a Supabase Auth user."""
        existing = self.get(db, id=user_id)
        if existing:
            return existing

        resolved_username = (username or email.split("@")[0]).strip()
        resolved_display_name = (display_name or resolved_username).strip()

        payload = {
            "id": user_id,
            "email": email,
            "username": resolved_username,
            "display_name": resolved_display_name,
        }

        try:
            resp = db.table(self.table_name).insert(payload).execute()
            return resp.data[0] if resp.data else {}
        except Exception:
            # Backward compatibility for schemas where password_hash is still NOT NULL.
            payload["password_hash"] = "supa-auth"
            resp = db.table(self.table_name).insert(payload).execute()
            return resp.data[0] if resp.data else {}

    # ------------------------------------------------------------------
    # Streak
    # ------------------------------------------------------------------

    def update_streak(self, db: Client, user_id: str) -> Dict[str, Any]:
        """Increment daily streak if applicable."""
        user_row = self.get(db, id=user_id)
        if not user_row:
            return {}
        today = date.today()
        last_active = user_row.get("last_active_date")
        streak = user_row.get("streak_days", 0)

        if last_active:
            if isinstance(last_active, str):
                last_active = date.fromisoformat(last_active)
            diff = (today - last_active).days
            if diff == 1:
                streak += 1
            elif diff > 1:
                streak = 1
            # diff == 0 → already active today, keep current streak
        else:
            streak = 1

        resp = (
            db.table(self.table_name)
            .update({"streak_days": streak, "last_active_date": str(today)})
            .eq("id", user_id)
            .execute()
        )
        return resp.data[0] if resp.data else {}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_users(
        self, db: Client, query: str, skip: int = 0, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search public profiles by username or display_name (case-insensitive)."""
        resp = (
            db.table(self.table_name)
            .select(
                "id, username, display_name, bio, "
                "streak_days, created_at, is_profile_public, profile_visibility"
            )
            .or_(f"username.ilike.%{query}%,display_name.ilike.%{query}%")
            .range(skip, skip + limit - 1)
            .execute()
        )
        rows = resp.data or []
        public_rows = [
            row
            for row in rows
            if row.get("is_profile_public") or row.get("profile_visibility") == "public"
        ]
        for row in public_rows:
            row.pop("is_profile_public", None)
            row.pop("profile_visibility", None)
        return public_rows


user = CRUDUser("users")
