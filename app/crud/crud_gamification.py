"""CRUD helpers for milestones — progress markers and community view."""

from typing import Any, Dict, List

from supabase import Client

from app.crud.crud_base import CRUDBase


class CRUDMilestone(CRUDBase):

    def get_all(self, db: Client) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .order("created_at")
            .execute()
        )
        return resp.data or []


class CRUDUserMilestone(CRUDBase):

    def get_user_milestones(
        self, db: Client, user_id: str
    ) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*, milestones(*)")
            .eq("user_id", user_id)
            .order("reached_at", desc=True)
            .execute()
        )
        rows = resp.data or []
        for row in rows:
            row["milestone"] = row.pop("milestones", None)
        return rows

    def has_milestone(
        self, db: Client, user_id: str, milestone_id: str
    ) -> bool:
        resp = (
            db.table(self.table_name)
            .select("id")
            .eq("user_id", user_id)
            .eq("milestone_id", milestone_id)
            .maybe_single()
            .execute()
        )
        return resp.data is not None

    def award(
        self, db: Client, user_id: str, milestone_id: str
    ) -> Dict[str, Any]:
        return self.create(
            db=db,
            data={"user_id": user_id, "milestone_id": milestone_id},
        )


def get_active_community(db: Client, limit: int = 20) -> List[Dict[str, Any]]:
    """Active community members (public profiles, sorted by recent activity)."""
    resp = (
        db.table("users")
        .select(
            "id, username, display_name, avatar_url, streak_days"
        )
        .eq("is_profile_public", True)
        .order("last_active_date", desc=True)
        .range(0, limit - 1)
        .execute()
    )
    rows = resp.data or []
    return [
        {"user_id": r["id"], **{k: v for k, v in r.items() if k != "id"}}
        for r in rows
    ]


milestone = CRUDMilestone("milestones")
user_milestone = CRUDUserMilestone("user_milestones")
