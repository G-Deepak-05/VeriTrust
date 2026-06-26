"""
Integration tests for verification endpoints.
"""
import pytest


VALID_PAYLOAD = {
    "name": "John Doe",
    "email": "john@gmail.com",
    "phone": "+919999999999",
    "pan": "ABCDE1234F",
    "ip_address": "103.44.12.34",
    "device_id": "device_123",
}

DISPOSABLE_EMAIL_PAYLOAD = {
    "name": "Scammer",
    "email": "scam@mailinator.com",
    "phone": "+919999999999",
    "pan": "INVALID",
    "ip_address": "103.44.12.34",
    "device_id": "device_bad",
}


class TestSubmitVerification:
    async def test_submit_clean_request(self, client, test_api_key, test_fraud_rules):
        _, full_key = test_api_key
        response = await client.post(
            "/api/v1/verify",
            json=VALID_PAYLOAD,
            headers={"X-Api-Key": full_key},
        )
        assert response.status_code == 201
        data = response.json()
        assert "verification_id" in data
        assert "risk_score" in data
        assert data["decision"] in ("APPROVED", "REVIEW", "REJECT")
        assert isinstance(data["reasons"], list)
        assert data["processing_ms"] >= 0

    async def test_submit_suspicious_request(self, client, test_api_key, test_fraud_rules):
        _, full_key = test_api_key
        response = await client.post(
            "/api/v1/verify",
            json=DISPOSABLE_EMAIL_PAYLOAD,
            headers={"X-Api-Key": full_key},
        )
        assert response.status_code == 201
        data = response.json()
        # Should get a higher score due to disposable email + invalid PAN
        assert data["risk_score"] > 0
        assert len(data["reasons"]) > 0

    async def test_submit_no_api_key(self, client):
        response = await client.post("/api/v1/verify", json=VALID_PAYLOAD)
        assert response.status_code == 401

    async def test_submit_invalid_api_key(self, client):
        response = await client.post(
            "/api/v1/verify",
            json=VALID_PAYLOAD,
            headers={"X-Api-Key": "invalid_key"},
        )
        assert response.status_code == 401


class TestGetVerification:
    async def test_get_verification_result(self, client, test_api_key, test_fraud_rules):
        _, full_key = test_api_key
        headers = {"X-Api-Key": full_key}

        # Submit first
        create_resp = await client.post(
            "/api/v1/verify", json=VALID_PAYLOAD, headers=headers
        )
        verification_id = create_resp.json()["verification_id"]

        # Fetch detail
        get_resp = await client.get(
            f"/api/v1/verify/{verification_id}", headers=headers
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["verification_id"] == verification_id
        assert "rule_breakdown" in data
        assert "email" in data

    async def test_get_nonexistent_verification(self, client, test_api_key):
        import uuid
        _, full_key = test_api_key
        response = await client.get(
            f"/api/v1/verify/{uuid.uuid4()}",
            headers={"X-Api-Key": full_key},
        )
        assert response.status_code == 404


class TestVerificationHistory:
    async def test_history_returns_list(self, client, test_api_key, test_fraud_rules):
        _, full_key = test_api_key
        headers = {"X-Api-Key": full_key}

        # Submit a verification
        await client.post("/api/v1/verify", json=VALID_PAYLOAD, headers=headers)

        # Get history
        response = await client.get("/api/v1/verify/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] >= 1
