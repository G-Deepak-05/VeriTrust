import uuid

from app.core.security import create_access_token


class TestUsersEndpoints:
    async def test_list_users_success(self, client, db_session, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["total"] > 0
        assert data["data"][0]["email"] == test_user.email

    async def test_list_users_unauthenticated(self, client):
        response = await client.get("/api/v1/users")
        assert response.status_code == 401

    async def test_get_user_success(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/v1/users/{test_user.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    async def test_get_user_not_found(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/users/{fake_id}", headers=headers)
        assert response.status_code == 404
