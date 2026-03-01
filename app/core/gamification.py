"""Progress tracking — streak updates and milestone checks.

The philosophy: milestones should feel like natural acknowledgments of effort,
not game badges. No points, no levels. Just quiet, thoughtful recognition
that you are showing up and doing the work.
"""

from typing import Any, Dict, List

from supabase import Client

from app.core.logging import logger


def track_progress_and_check_milestones(
    db: Client, user_id: str, action: str
) -> Dict[str, Any]:
    """Update the user's streak and check for newly-reached milestones.

    This function is designed to be non-critical — it should never crash
    the calling endpoint.  All errors are logged and swallowed.
    """
    from app.crud.crud_user import user as crud_user
    from app.crud.crud_gamification import (
        milestone as crud_milestone,
        user_milestone as crud_user_milestone,
    )

    try:
        # 1. Update daily streak
        crud_user.update_streak(db, user_id)
    except Exception as exc:
        logger.warning("streak update failed for user %s: %s", user_id, exc)

    # 2. Check every milestone the user hasn't reached yet
    newly_reached: List[str] = []
    try:
        all_milestones = crud_milestone.get_all(db)
    except Exception as exc:
        logger.warning("Failed to load milestones: %s", exc)
        return {"milestones_reached": []}

    for ms in all_milestones:
        try:
            if crud_user_milestone.has_milestone(db, user_id, ms["id"]):
                continue  # already reached

            criteria = ms.get("criteria", {})
            if _check_criteria(db, user_id, criteria):
                crud_user_milestone.award(db, user_id, ms["id"])
                newly_reached.append(ms["name"])
        except Exception as exc:
            logger.warning(
                "Milestone check failed for %s (user %s): %s",
                ms.get("name", "?"), user_id, exc,
            )

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
        try:
            resp = (
                db.table("users")
                .select("streak_days")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
            user_row = resp.data if resp is not None else None
        except Exception:
            return False
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
        "add_contact": "contacts",
        "create_tag": "tags",
        "save_job": "saved_jobs",
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

    # Prep-notes milestone: count stages with non-null prep_notes
    if crit_action == "add_prep_notes":
        apps_resp = (
            db.table("applications")
            .select("id")
            .eq("user_id", user_id)
            .execute()
        )
        app_ids = [a["id"] for a in (apps_resp.data or [])]
        if not app_ids:
            return False
        resp = (
            db.table("application_stages")
            .select("id", count="exact")
            .in_("application_id", app_ids)
            .neq("prep_notes", "null")
            .execute()
        )
        return (resp.count or 0) >= crit_count

    # Converted saved jobs milestone
    if crit_action == "convert_saved_job":
        resp = (
            db.table("saved_jobs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "Converted")
            .execute()
        )
        return (resp.count or 0) >= crit_count

    # Salary tracking milestone: count applications with salary data
    if crit_action == "track_salary":
        resp = (
            db.table("applications")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .not_.is_("salary_min", "null")
            .execute()
        )
        return (resp.count or 0) >= crit_count

    return False
