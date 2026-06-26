"""
Integration tests for organization endpoints.
"""


class TestCreateOrganization:
    async def test_create_org(self, client, auth_headers):
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "New Corp", "description": "A new org"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Corp"
        assert "slug" in data
        assert "id" in data

    async def test_create_org_unauthenticated(self, client):
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "New Corp"},
        )
        assert response.status_code == 401


class TestGetOrganization:
    async def test_get_existing_org(self, client, auth_headers, test_org):
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_org.id)
        assert data["slug"] == "test-corp"

    async def test_get_nonexistent_org(self, client, auth_headers):
        import uuid

        response = await client.get(
            f"/api/v1/organizations/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateOrganization:
    async def test_update_org_as_owner(self, client, db_session, test_org, test_user):
        from app.core.security import create_access_token

        # Make test_user the owner
        from app.repositories.organization_repository import OrganizationRepository

        repo = OrganizationRepository(db_session)
        await repo.update(test_org, owner_id=test_user.id)

        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.put(
            f"/api/v1/organizations/{test_org.id}",
            json={"name": "Updated Corp"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Corp"


class TestHealth:
    async def test_health_check(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "postgres" in data
        assert "redis" in data
