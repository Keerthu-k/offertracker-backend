"""Progress tracking — streak updates and milestone checks.

The philosophy: milestones should feel like natural acknowledgments of effort,
not game badges. No points, no levels. Just quiet, thoughtful recognition
that you are showing up and doing the work.
"""

from typing import Any, Dict, List

from supabase import Client


def track_progress_and_check_milestones(
    db: Client, user_id: str, action: str
) -> Dict[str, Any]:
    """Update the user's streak and check for newly-reached milestones."""
    from app.crud.crud_user import user as crud_user
    from app.crud.crud_gamification import (
        milestone as crud_milestone,
        user_milestone as crud_user_milestone,
    )

    # 1. Update daily streak
    crud_user.update_streak(db, user_id)

    # 2. Check every milestone the user hasn't reached yet
    newly_reached: List[str] = []
    all_milestones = crud_milestone.get_all(db)

    for ms in all_milestones:
        if crud_user_milestone.has_milestone(db, user_id, ms["id"]):
            continue  # already reached

        criteria = ms.get("criteria", {})
        if _check_criteria(db, user_id, criteria):
            crud_user_milestone.award(db, user_id, ms["id"])
            newly_reached.append(ms["name"])

    return {"milestones_reached": newly_reached}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _check_criteria(db: Client, user_id: str, criteria: Dict) -> bool:
    """Evaluate whether a user currently satisfies *criteria*."""
    crit_action = criteria.get("action", "")
    crit_count = criteria.get("count", 0)
    crit_days = criteria.get("days", 0)

    # "Getting Started" is awarded explicitly at registration — never via this path
    if crit_action == "register":
        return False

    # Streak-based milestones
    if crit_action == "streak":
        user_row = (
            db.table("users")
            .select("streak_days")
            .eq("id", user_id)
            .maybe_single()
            .execute()
            .data
        )
        return bool(user_row and user_row.get("streak_days", 0) >= crit_days)

    # Follow count
    if crit_action == "follow":
        resp = (
            db.table("follows")
            .select("id", count="exact")
            .eq("follower_id", user_id)
            .execute()
        )
        return (resp.count or 0) >= crit_count

    # Group membership count
    if crit_action == "join_group":
        resp = (
            db.table("group_members")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return (resp.count or 0) >= crit_count

    # Count-based milestones that map directly to a table with user_id FK
    direct_tables = {
        "create_application": "applications",
        "create_post": "shared_posts",
    }
    if crit_action in direct_tables:
        table = direct_tables[crit_action]
        resp = (
            db.table(table)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return (resp.count or 0) >= crit_count

    # Milestones that require joining through the user's applications
    if crit_action in ("create_reflection", "outcome_offer"):
        apps_resp = (
            db.table("applications")
            .select("id")
            .eq("user_id", user_id)
            .execute()
        )
        app_ids = [a["id"] for a in (apps_resp.data or [])]
        if not app_ids:
            return False

        if crit_action == "create_reflection":
            resp = (
                db.table("reflections")
                .select("id", count="exact")
                .in_("application_id", app_ids)
                .execute()
            )
            return (resp.count or 0) >= crit_count

        if crit_action == "outcome_offer":
            resp = (
                db.table("outcomes")
                .select("id", count="exact")
                .in_("application_id", app_ids)
                .eq("status", "Offer")
                .execute()
            )
            return (resp.count or 0) >= crit_count

    return False
