"""CRUD helpers for social features – follows, groups, posts, reactions."""

from typing import Any, Dict, List, Optional

from supabase import Client

from app.crud.crud_base import CRUDBase


# ------------------------------------------------------------------
# Follows
# ------------------------------------------------------------------

class CRUDFollow(CRUDBase):

    def get_follow(
        self, db: Client, follower_id: str, following_id: str
    ) -> Optional[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("follower_id", follower_id)
            .eq("following_id", following_id)
            .maybe_single()
            .execute()
        )
        return resp.data

    def get_followers(
        self, db: Client, user_id: str, skip: int = 0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("following_id", user_id)
            .range(skip, skip + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []

    def get_following(
        self, db: Client, user_id: str, skip: int = 0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("follower_id", user_id)
            .range(skip, skip + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []

    def count_followers(self, db: Client, user_id: str) -> int:
        resp = (
            db.table(self.table_name)
            .select("id", count="exact")
            .eq("following_id", user_id)
            .execute()
        )
        return resp.count or 0

    def count_following(self, db: Client, user_id: str) -> int:
        resp = (
            db.table(self.table_name)
            .select("id", count="exact")
            .eq("follower_id", user_id)
            .execute()
        )
        return resp.count or 0

    def unfollow(self, db: Client, follower_id: str, following_id: str) -> bool:
        resp = (
            db.table(self.table_name)
            .delete()
            .eq("follower_id", follower_id)
            .eq("following_id", following_id)
            .execute()
        )
        return bool(resp.data)


# ------------------------------------------------------------------
# Groups
# ------------------------------------------------------------------

class CRUDGroup(CRUDBase):

    def get_with_member_count(self, db: Client, id: str) -> Optional[Dict[str, Any]]:
        group = self.get(db, id=id)
        if not group:
            return None
        members_resp = (
            db.table("group_members")
            .select("id", count="exact")
            .eq("group_id", id)
            .execute()
        )
        group["member_count"] = members_resp.count or 0
        return group

    def get_public_groups(
        self, db: Client, skip: int = 0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("is_public", True)
            .range(skip, skip + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []

    def get_user_groups(self, db: Client, user_id: str) -> List[Dict[str, Any]]:
        """Return groups that *user_id* belongs to."""
        resp = (
            db.table("group_members")
            .select("*, groups(*)")
            .eq("user_id", user_id)
            .execute()
        )
        rows = resp.data or []
        return [r.get("groups", r) for r in rows if r.get("groups")]


# ------------------------------------------------------------------
# Posts
# ------------------------------------------------------------------

class CRUDPost(CRUDBase):

    def get_feed(
        self,
        db: Client,
        *,
        group_id: str | None = None,
        public_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = db.table(self.table_name).select("*")
        if group_id:
            query = query.eq("group_id", group_id)
        elif public_only:
            query = query.eq("is_public", True)
        resp = (
            query
            .range(skip, skip + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []

    def get_user_posts(
        self, db: Client, user_id: str, skip: int = 0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        resp = (
            db.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .range(skip, skip + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []


# ------------------------------------------------------------------
# Module-level instances
# ------------------------------------------------------------------

follow = CRUDFollow("follows")
group = CRUDGroup("groups")
group_member = CRUDBase("group_members")
post = CRUDPost("shared_posts")
reaction = CRUDBase("post_reactions")
