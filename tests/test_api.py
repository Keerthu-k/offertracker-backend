import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_and_read_company(client: AsyncClient):
    response = await client.post(
        "/api/v1/companies/",
        json={"name": "Test Company", "industry": "Tech", "website": "https://test.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Company"
    assert "id" in data
    
    company_id = data["id"]
    
    response = await client.get(f"/api/v1/companies/{company_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Company"

@pytest.mark.asyncio
async def test_full_application_lifecycle(client: AsyncClient):
    # 1. Create company
    resp = await client.post("/api/v1/companies/", json={"name": "Lifecycle Inc"})
    company_id = resp.json()["id"]

    # 2. Create job
    resp = await client.post("/api/v1/jobs/", json={"title": "Engineer", "company_id": company_id})
    job_id = resp.json()["id"]

    # 3. Create resume
    resp = await client.post("/api/v1/resumes/", json={"version_name": "v1.0.0"})
    resume_id = resp.json()["id"]

    # 4. Create application
    resp = await client.post(
        "/api/v1/applications/",
        json={"job_posting_id": job_id, "resume_version_id": resume_id, "status": "Applied"}
    )
    assert resp.status_code == 200
    app_id = resp.json()["id"]

    # 5. Add stage
    resp = await client.post(
        f"/api/v1/applications/{app_id}/stages",
        json={"application_id": app_id, "stage_name": "Technical Screen"}
    )
    assert resp.status_code == 200

    # 6. Set outcome
    resp = await client.post(
        f"/api/v1/applications/{app_id}/outcome",
        json={"application_id": app_id, "status": "Rejected"}
    )
    assert resp.status_code == 200

    # 7. Add reflection
    resp = await client.post(
        f"/api/v1/applications/{app_id}/reflection",
        json={"application_id": app_id, "what_failed": "Too slow", "skill_gaps": {"DSA": "medium"}}
    )
    assert resp.status_code == 200

    # 8. Fetch application and verify relations
    resp = await client.get(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["stages"]) == 1
    assert data["outcome"]["status"] == "Rejected"
    assert data["reflection"]["skill_gaps"]["DSA"] == "medium"
