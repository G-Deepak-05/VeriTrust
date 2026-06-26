from app.core.security import create_access_token


class TestExtraEndpoints:
    async def test_audit_logs(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/audit", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_dashboard_stats(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_verifications" in data

    async def test_dashboard_analytics(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/dashboard/analytics?period=7d", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_fraud_rules_list(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/fraud/rules", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_fraud_rule_crud(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Create a rule
        rule_data = {
            "rule_name": "test_rule_temp",
            "rule_type": "email",
            "description": "Just a test rule",
            "score_impact": 10,
            "is_active": True,
            "config": {},
        }
        res_create = await client.post("/api/v1/fraud/rules", json=rule_data, headers=headers)
        assert res_create.status_code == 201
        created = res_create.json()
        rule_id = created["id"]

        # Update a rule
        res_update = await client.put(
            f"/api/v1/fraud/rules/{rule_id}",
            json={"score_impact": 15},
            headers=headers,
        )
        assert res_update.status_code == 200
        assert res_update.json()["score_impact"] == 15

        # Delete a rule
        res_delete = await client.delete(f"/api/v1/fraud/rules/{rule_id}", headers=headers)
        assert res_delete.status_code == 200

    async def test_fraud_simulate(self, client, test_user):
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
        )
        headers = {"Authorization": f"Bearer {token}"}

        sim_data = {
            "name": "Simulated User",
            "email": "test@gmail.com",
            "pan": "ABCDE1234F",
            "phone": "+919999999999",
            "ip_address": "8.8.8.8",
            "device_id": "dev_123",
        }
        response = await client.post("/api/v1/fraud/simulate", json=sim_data, headers=headers)
        assert response.status_code == 200
        assert "risk_score" in response.json()
