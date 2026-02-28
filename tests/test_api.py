import pytest
from httpx import AsyncClient


# ======================================================================
# Root
# ======================================================================


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Welcome to OfferTracker API"


# ======================================================================
# Full application lifecycle (resumes → apps → stages → outcome → reflection)
# ======================================================================


@pytest.mark.asyncio
async def test_full_application_lifecycle(client: AsyncClient):
    # 1. Create resume
    resp = await client.post("/api/v1/resumes/", json={"version_name": "v1.0.0"})
    assert resp.status_code == 200
    resume_id = resp.json()["id"]

    # 2. Create application
    resp = await client.post(
        "/api/v1/applications/",
        json={
            "company_name": "Lifecycle Inc",
            "role_title": "Engineer",
            "applied_source": "LinkedIn",
            "resume_version_id": resume_id,
            "status": "Applied",
        },
    )
    assert resp.status_code == 200
    app_id = resp.json()["id"]

    # 3. Add stage
    resp = await client.post(
        f"/api/v1/applications/{app_id}/stages",
        json={"application_id": app_id, "stage_name": "Technical Screen"},
    )
    assert resp.status_code == 200

    # 4. Set outcome
    resp = await client.post(
        f"/api/v1/applications/{app_id}/outcome",
        json={"application_id": app_id, "status": "Rejected"},
    )
    assert resp.status_code == 200

    # 5. Add reflection
    resp = await client.post(
        f"/api/v1/applications/{app_id}/reflection",
        json={
            "application_id": app_id,
            "what_failed": "Too slow",
            "skill_gaps": {"DSA": "medium"},
        },
    )
    assert resp.status_code == 200

    # 6. Fetch application and verify relations
    resp = await client.get(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["company_name"] == "Lifecycle Inc"
    assert data["role_title"] == "Engineer"
    assert data["applied_source"] == "LinkedIn"
    assert len(data["stages"]) == 1
    assert data["outcome"]["status"] == "Rejected"
    assert data["reflection"]["skill_gaps"]["DSA"] == "medium"


# ======================================================================
# DELETE endpoints
# ======================================================================


@pytest.mark.asyncio
async def test_delete_application(client: AsyncClient):
    resp = await client.post(
        "/api/v1/applications/",
        json={"company_name": "Delete Co", "role_title": "Dev"},
    )
    app_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Application deleted"

    # Verify the application is gone
    resp = await client.get(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_resume(client: AsyncClient):
    resp = await client.post("/api/v1/resumes/", json={"version_name": "deleteme"})
    resume_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/resumes/{resume_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/resumes/{resume_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_stage(client: AsyncClient):
    resp = await client.post(
        "/api/v1/applications/",
        json={"company_name": "Stage Co", "role_title": "Dev"},
    )
    app_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/stages",
        json={"application_id": app_id, "stage_name": "Phone Screen"},
    )
    stage_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/applications/{app_id}/stages/{stage_id}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Stage deleted"


@pytest.mark.asyncio
async def test_delete_outcome(client: AsyncClient):
    resp = await client.post(
        "/api/v1/applications/",
        json={"company_name": "Outcome Co", "role_title": "Dev"},
    )
    app_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/outcome",
        json={"application_id": app_id, "status": "Rejected"},
    )
    outcome_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/applications/{app_id}/outcome/{outcome_id}"
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Outcome deleted"


@pytest.mark.asyncio
async def test_delete_reflection(client: AsyncClient):
    resp = await client.post(
        "/api/v1/applications/",
        json={"company_name": "Reflect Co", "role_title": "Dev"},
    )
    app_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/reflection",
        json={"application_id": app_id, "what_worked": "Good prep"},
    )
    ref_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/applications/{app_id}/reflection/{ref_id}"
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Reflection deleted"


# ======================================================================
# UPDATE endpoints for stages / outcome / reflection
# ======================================================================


@pytest.mark.asyncio
async def test_update_stage(client: AsyncClient):
    resp = await client.post(
        "/api/v1/applications/",
        json={"company_name": "Stage Co", "role_title": "Dev"},
    )
    app_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/stages",
        json={"application_id": app_id, "stage_name": "Phone Screen"},
    )
    stage_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/applications/{app_id}/stages/{stage_id}",
        json={"stage_name": "On-Site Interview"},
    )
    assert resp.status_code == 200
    assert resp.json()["stage_name"] == "On-Site Interview"


@pytest.mark.asyncio
async def test_update_outcome(client: AsyncClient):
    resp = await client.post(
        "/api/v1/applications/",
        json={"company_name": "Outcome Co", "role_title": "Dev"},
    )
    app_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/outcome",
        json={"application_id": app_id, "status": "Rejected"},
    )
    outcome_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/applications/{app_id}/outcome/{outcome_id}",
        json={"status": "Offer"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Offer"


@pytest.mark.asyncio
async def test_update_reflection(client: AsyncClient):
    resp = await client.post(
        "/api/v1/applications/",
        json={"company_name": "Reflect Co", "role_title": "Dev"},
    )
    app_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/reflection",
        json={"application_id": app_id, "what_worked": "Good prep"},
    )
    ref_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/applications/{app_id}/reflection/{ref_id}",
        json={"what_failed": "Forgot to follow up"},
    )
    assert resp.status_code == 200
    assert resp.json()["what_failed"] == "Forgot to follow up"


# ======================================================================
# User profile
# ======================================================================


@pytest.mark.asyncio
async def test_user_profile(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


# ======================================================================
# Social — follow stats, groups, posts
# ======================================================================


@pytest.mark.asyncio
async def test_follow_stats(client: AsyncClient):
    resp = await client.get("/api/v1/social/follow-stats/test-user-id")
    assert resp.status_code == 200
    assert resp.json()["followers_count"] == 0


@pytest.mark.asyncio
async def test_create_group(client: AsyncClient):
    resp = await client.post(
        "/api/v1/social/groups",
        json={"name": "Job Hunters", "description": "A group for job seekers"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Job Hunters"
    assert data["member_count"] == 1


@pytest.mark.asyncio
async def test_create_post(client: AsyncClient):
    resp = await client.post(
        "/api/v1/social/posts",
        json={
            "post_type": "tip",
            "title": "Resume Tips",
            "content": "Use action verbs",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Resume Tips"


# ======================================================================
# Gamification
# ======================================================================


@pytest.mark.asyncio
async def test_gamification_stats(client: AsyncClient):
    resp = await client.get("/api/v1/progress/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_applications"] == 0
    assert data["streak_days"] == 0


@pytest.mark.asyncio
async def test_gamification_achievements_list(client: AsyncClient):
    resp = await client.get("/api/v1/progress/milestones")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2

