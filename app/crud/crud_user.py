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
                "id, username, display_name, bio, avatar_url, "
                "streak_days, created_at"
            )
            .or_(f"username.ilike.%{query}%,display_name.ilike.%{query}%")
            .eq("is_profile_public", True)
            .range(skip, skip + limit - 1)
            .execute()
        )
        return resp.data or []


user = CRUDUser("users")
