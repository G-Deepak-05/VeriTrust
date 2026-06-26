"""
Integration tests for API key endpoints.
"""
import pytest


class TestCreateAPIKey:
    async def test_create_key_success(self, client, auth_headers):
        response = await client.post(
            "/api/v1/apikeys",
            json={"name": "Production Key", "permissions": {}},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"].startswith("vt_live_")
        assert "id" in data
        assert data["message"] == "Store this key securely — it will not be shown again."

    async def test_create_key_unauthenticated(self, client):
        response = await client.post(
            "/api/v1/apikeys",
            json={"name": "Test Key"},
        )
        assert response.status_code == 401


class TestListAPIKeys:
    async def test_list_keys(self, client, auth_headers, test_api_key):
        response = await client.get("/api/v1/apikeys", headers=auth_headers)
        assert response.status_code == 200
        keys = response.json()
        assert isinstance(keys, list)
        # Secret must never be in list response
        for key in keys:
            assert "key" not in key or key.get("key") is None

    async def test_list_keys_unauthenticated(self, client):
        response = await client.get("/api/v1/apikeys")
        assert response.status_code == 401


class TestRevokeAPIKey:
    async def test_revoke_key(self, client, auth_headers, test_api_key):
        key_model, _ = test_api_key
        response = await client.delete(
            f"/api/v1/apikeys/{key_model.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_revoke_nonexistent_key(self, client, auth_headers):
        import uuid
        response = await client.delete(
            f"/api/v1/apikeys/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404
