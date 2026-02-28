"""Progress endpoints — milestones, community, stats."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.crud.crud_gamification import (
    milestone as crud_milestone,
    user_milestone as crud_user_milestone,
    get_active_community,
)
from app.schemas.gamification import (
    MilestoneResponse,
    UserMilestoneResponse,
    CommunityMemberEntry,
    UserStatsResponse,
)

router = APIRouter()


@router.get("/milestones", response_model=List[MilestoneResponse])
def list_milestones(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List all available milestones."""
    return crud_milestone.get_all(db)


@router.get("/milestones/mine", response_model=List[UserMilestoneResponse])
def my_milestones(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List milestones reached by the current user."""
    return crud_user_milestone.get_user_milestones(db, current_user["id"])


@router.get("/community", response_model=List[CommunityMemberEntry])
def community(
    *,
    db: Client = Depends(get_supabase),
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Active community members (public profiles, recently active)."""
    return get_active_community(db, limit=limit)


@router.get("/stats", response_model=UserStatsResponse)
def my_stats(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get the current user's progress summary."""
    user_id = current_user["id"]

    # Count applications
    apps_resp = (
        db.table("applications")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    total_applications = apps_resp.count or 0
    app_ids = [a["id"] for a in (apps_resp.data or [])]

    total_offers = 0
    total_rejections = 0
    total_reflections = 0
    total_stages = 0

    if app_ids:
        offer_resp = (
            db.table("outcomes")
            .select("id", count="exact")
            .in_("application_id", app_ids)
            .eq("status", "Offer")
            .execute()
        )
        total_offers = offer_resp.count or 0

        rej_resp = (
            db.table("outcomes")
            .select("id", count="exact")
            .in_("application_id", app_ids)
            .eq("status", "Rejected")
            .execute()
        )
        total_rejections = rej_resp.count or 0

        ref_resp = (
            db.table("reflections")
            .select("id", count="exact")
            .in_("application_id", app_ids)
            .execute()
        )
        total_reflections = ref_resp.count or 0

        stage_resp = (
            db.table("application_stages")
            .select("id", count="exact")
            .in_("application_id", app_ids)
            .execute()
        )
        total_stages = stage_resp.count or 0

    # Milestones count
    ms_resp = (
        db.table("user_milestones")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )

    return {
        "total_applications": total_applications,
        "total_offers": total_offers,
        "total_rejections": total_rejections,
        "total_reflections": total_reflections,
        "total_stages": total_stages,
        "streak_days": current_user.get("streak_days", 0),
        "milestones_reached": ms_resp.count or 0,
    }
