"""Analytics & Dashboard endpoints.

Gives job seekers data-driven insights into their search:
- Pipeline funnel (applications per status)
- Response, interview, and offer rates
- Source effectiveness (which channels work best)
- Weekly application trends
- Salary insights across applications and offers
- Activity timeline
"""

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.crud.crud_activity import activity_log as crud_activity_log
from app.schemas.activity import ActivityLogResponse
from app.schemas.gamification import (
    AnalyticsDashboardResponse,
    PipelineBreakdown,
    SourceEffectiveness,
    WeeklyTrend,
    SalaryInsight,
)

router = APIRouter()


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
def get_dashboard(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Comprehensive analytics dashboard for the applicant."""
    user_id = current_user["id"]

    # ------------------------------------------------------------------
    # 1. Fetch all applications for this user (lightweight: only needed cols)
    # ------------------------------------------------------------------
    apps_resp = (
        db.table("applications")
        .select("id, status, applied_source, applied_date, company_name, "
                "salary_min, salary_max, salary_currency")
        .eq("user_id", user_id)
        .execute()
    )
    apps = apps_resp.data or []
    total = len(apps)

    if total == 0:
        return AnalyticsDashboardResponse()

    app_ids = [a["id"] for a in apps]

    # ------------------------------------------------------------------
    # 2. Pipeline breakdown (count per status)
    # ------------------------------------------------------------------
    status_counter = Counter(a.get("status", "Applied") for a in apps)
    pipeline = [
        PipelineBreakdown(status=s, count=c)
        for s, c in status_counter.most_common()
    ]

    # ------------------------------------------------------------------
    # 3. Rates — based on status values
    # ------------------------------------------------------------------
    non_saved = [a for a in apps if a.get("status") != "Open"]
    total_tracked = len(non_saved)

    responded_statuses = {"Shortlisted", "Interview", "Offer", "Rejected", "Closed"}
    interview_statuses = {"Interview", "Offer", "Closed"}
    offer_statuses = {"Offer", "Closed"}

    responded = sum(
        1 for a in non_saved
        if a.get("status") in responded_statuses
    )
    interviewed = sum(
        1 for a in non_saved if a.get("status") in interview_statuses
    )
    offers = sum(
        1 for a in non_saved if a.get("status") in offer_statuses
    )

    response_rate = responded / total_tracked if total_tracked else 0.0
    interview_rate = interviewed / total_tracked if total_tracked else 0.0
    offer_rate = offers / total_tracked if total_tracked else 0.0

    # ------------------------------------------------------------------
    # 4. Source effectiveness
    # ------------------------------------------------------------------
    source_apps: Dict[str, List[Dict]] = defaultdict(list)
    for a in apps:
        src = a.get("applied_source") or "Unknown"
        source_apps[src].append(a)

    # Fetch stages and outcomes for deeper analysis
    stages_resp = (
        db.table("application_stages")
        .select("application_id")
        .in_("application_id", app_ids)
        .execute()
    )
    interviewed_app_ids = {s["application_id"] for s in (stages_resp.data or [])}

    outcomes_resp = (
        db.table("outcomes")
        .select("application_id, status")
        .in_("application_id", app_ids)
        .execute()
    )
    offer_app_ids = {
        o["application_id"]
        for o in (outcomes_resp.data or [])
        if o.get("status") == "Offer"
    }

    source_breakdown = []
    for src, src_apps in sorted(source_apps.items(), key=lambda x: -len(x[1])):
        src_ids = {a["id"] for a in src_apps}
        source_breakdown.append(
            SourceEffectiveness(
                source=src,
                applied=len(src_apps),
                interviews=len(src_ids & interviewed_app_ids),
                offers=len(src_ids & offer_app_ids),
            )
        )

    # ------------------------------------------------------------------
    # 5. Weekly trend (last 12 weeks)
    # ------------------------------------------------------------------
    today = date.today()
    twelve_weeks_ago = today - timedelta(weeks=12)

    # Build a map of ISO week → counts
    stages_with_dates = (
        db.table("application_stages")
        .select("stage_date")
        .in_("application_id", app_ids)
        .execute()
    ).data or []

    week_apps: Counter = Counter()
    week_stages: Counter = Counter()
    for a in apps:
        ad = a.get("applied_date")
        if ad:
            try:
                d = date.fromisoformat(str(ad))
                if d >= twelve_weeks_ago:
                    iso = d.isocalendar()
                    wk = f"{iso[0]}-W{iso[1]:02d}"
                    week_apps[wk] += 1
            except (ValueError, TypeError):
                pass
    for s in stages_with_dates:
        sd = s.get("stage_date")
        if sd:
            try:
                d = date.fromisoformat(str(sd))
                if d >= twelve_weeks_ago:
                    iso = d.isocalendar()
                    wk = f"{iso[0]}-W{iso[1]:02d}"
                    week_stages[wk] += 1
            except (ValueError, TypeError):
                pass

    all_weeks = sorted(set(week_apps.keys()) | set(week_stages.keys()))
    weekly_trend = [
        WeeklyTrend(
            week=wk,
            applications=week_apps.get(wk, 0),
            stages=week_stages.get(wk, 0),
        )
        for wk in all_weeks
    ]

    # ------------------------------------------------------------------
    # 6. Salary insights
    # ------------------------------------------------------------------
    apps_with_salary = [
        a for a in apps
        if a.get("salary_min") is not None or a.get("salary_max") is not None
    ]
    avg_min = (
        sum(a["salary_min"] for a in apps_with_salary if a.get("salary_min"))
        / max(len([a for a in apps_with_salary if a.get("salary_min")]), 1)
        if apps_with_salary else None
    )
    avg_max = (
        sum(a["salary_max"] for a in apps_with_salary if a.get("salary_max"))
        / max(len([a for a in apps_with_salary if a.get("salary_max")]), 1)
        if apps_with_salary else None
    )

    # Offered salary from outcomes
    offer_outcomes = (
        db.table("outcomes")
        .select("salary, salary_currency")
        .in_("application_id", app_ids)
        .eq("status", "Offer")
        .execute()
    ).data or []
    offers_with_salary = [o for o in offer_outcomes if o.get("salary")]
    avg_offered = (
        sum(o["salary"] for o in offers_with_salary) / len(offers_with_salary)
        if offers_with_salary else None
    )
    highest_offer = (
        max(o["salary"] for o in offers_with_salary)
        if offers_with_salary else None
    )

    salary_insights = SalaryInsight(
        applications_with_salary=len(apps_with_salary),
        average_expected_min=round(avg_min, 2) if avg_min else None,
        average_expected_max=round(avg_max, 2) if avg_max else None,
        offers_with_salary=len(offers_with_salary),
        average_offered=round(avg_offered, 2) if avg_offered else None,
        highest_offer=highest_offer,
    )

    # ------------------------------------------------------------------
    # 7. Top companies
    # ------------------------------------------------------------------
    company_counter = Counter(a.get("company_name", "") for a in apps)
    top_companies = [
        {"company": name, "count": cnt}
        for name, cnt in company_counter.most_common(10)
        if name
    ]

    return AnalyticsDashboardResponse(
        pipeline=pipeline,
        response_rate=round(response_rate, 4),
        interview_rate=round(interview_rate, 4),
        offer_rate=round(offer_rate, 4),
        source_breakdown=source_breakdown,
        weekly_trend=weekly_trend,
        salary_insights=salary_insights,
        top_companies=top_companies,
    )


# ======================================================================
# Activity timeline
# ======================================================================


@router.get("/activity", response_model=List[ActivityLogResponse])
def get_activity_log(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    application_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """Get the user's activity timeline, optionally filtered by application."""
    return crud_activity_log.get_user_activity(
        db,
        current_user["id"],
        application_id=application_id,
        skip=skip,
        limit=limit,
    )


# ======================================================================
# Interview Question Bank — aggregate all questions across applications
# ======================================================================


@router.get("/questions")
def get_interview_questions(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Aggregate all interview questions the user has encountered.

    Builds a personal question bank from the ``questions_asked`` field
    across all interview stages, grouped by stage type.
    """
    user_id = current_user["id"]

    # Get all application IDs for the user
    apps_resp = (
        db.table("applications")
        .select("id, company_name, role_title")
        .eq("user_id", user_id)
        .execute()
    )
    apps = apps_resp.data or []
    if not apps:
        return {"questions": [], "total": 0}

    app_map = {a["id"]: a for a in apps}
    app_ids = list(app_map.keys())

    # Fetch stages with questions
    stages_resp = (
        db.table("application_stages")
        .select("application_id, stage_name, stage_type, questions_asked")
        .in_("application_id", app_ids)
        .execute()
    )
    stages = stages_resp.data or []

    questions: List[Dict[str, Any]] = []
    for stage in stages:
        qs = stage.get("questions_asked")
        if not qs:
            continue
        app_info = app_map.get(stage["application_id"], {})
        if isinstance(qs, list):
            for q in qs:
                questions.append({
                    "question": q,
                    "stage_type": stage.get("stage_type") or stage.get("stage_name"),
                    "company": app_info.get("company_name"),
                    "role": app_info.get("role_title"),
                })

    return {"questions": questions, "total": len(questions)}
