import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_full_application_lifecycle(client: AsyncClient):
    # 1. Create resume
    resp = await client.post("/api/v1/resumes/", json={"version_name": "v1.0.0"})
    resume_id = resp.json()["id"]

    # 2. Create application directly with company and role info
    resp = await client.post(
        "/api/v1/applications/",
        json={
            "company_name": "Lifecycle Inc", 
            "role_title": "Engineer", 
            "applied_source": "LinkedIn",
            "resume_version_id": resume_id, 
            "status": "Applied"
        }
    )
    assert resp.status_code == 200
    app_id = resp.json()["id"]

    # 3. Add stage
    resp = await client.post(
        f"/api/v1/applications/{app_id}/stages",
        json={"application_id": app_id, "stage_name": "Technical Screen"}
    )
    assert resp.status_code == 200

    # 4. Set outcome
    resp = await client.post(
        f"/api/v1/applications/{app_id}/outcome",
        json={"application_id": app_id, "status": "Rejected"}
    )
    assert resp.status_code == 200

    # 5. Add reflection
    resp = await client.post(
        f"/api/v1/applications/{app_id}/reflection",
        json={"application_id": app_id, "what_failed": "Too slow", "skill_gaps": {"DSA": "medium"}}
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

