"""Multi-tenant cross-organization isolation tests."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_cross_organization_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    test_org: Organization,
    test_user: User,
    auth_headers: dict[str, str],
):
    # Create Second Organization & User B
    org_b = Organization(name="Competitor Security Corp")
    db_session.add(org_b)
    await db_session.flush()

    user_b = User(
        organization_id=org_b.id,
        email="analyst@competitor.com",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.ANALYST,
        is_active=True,
    )
    db_session.add(user_b)
    await db_session.flush()

    token_b = create_access_token(
        subject=user_b.id,
        organization_id=org_b.id,
        role=user_b.role.value,
        email=user_b.email,
    )
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. User A creates an incident in Org A
    inc_a = await client.post(
        "/api/v1/incidents",
        json={"title": "Confidential Breach Org A", "severity": "critical"},
        headers=auth_headers,
    )
    assert inc_a.status_code == 201
    inc_a_id = inc_a.json()["id"]

    # 2. User B in Org B attempts to access Org A's incident -> MUST return 404
    cross_get = await client.get(f"/api/v1/incidents/{inc_a_id}", headers=headers_b)
    assert cross_get.status_code == 404

    # 3. User B lists incidents -> Org A's incident must NOT appear
    list_b = await client.get("/api/v1/incidents", headers=headers_b)
    assert list_b.status_code == 200
    b_items = list_b.json()["items"]
    assert all(item["id"] != inc_a_id for item in b_items)
