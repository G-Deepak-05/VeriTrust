"""
Integration tests for authentication endpoints.
"""


class TestRegister:
    async def test_register_success(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "organization_name": "Example Corp",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client):
        payload = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "organization_name": "Example Corp",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    async def test_register_weak_password(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "John Doe",
                "email": "john@example.com",
                "password": "weakpass",  # No uppercase, no digit
                "organization_name": "Example Corp",
            },
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@testcorp.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@testcorp.com", "password": "WrongPass999!"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "AnyPass123!"},
        )
        assert response.status_code == 401


class TestRefreshToken:
    async def test_refresh_success(self, client, test_user):
        # Login to get tokens
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@testcorp.com", "password": "TestPass123!"},
        )
        tokens = login_resp.json()

        # Use refresh token
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert new_tokens["access_token"] != tokens["access_token"]
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_token_rotation_prevents_reuse(self, client, test_user):
        """Using a refresh token twice must fail on the second attempt."""
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@testcorp.com", "password": "TestPass123!"},
        )
        original_refresh = login_resp.json()["refresh_token"]

        # First use — should succeed
        first_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert first_resp.status_code == 200

        # Second use of same token — must fail (reuse detection)
        second_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert second_resp.status_code == 401


class TestGetMe:
    async def test_me_returns_user(self, client, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@testcorp.com"
        assert data["role"] == "admin"

    async def test_me_unauthenticated(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
