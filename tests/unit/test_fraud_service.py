"""
Unit tests for the fraud rule engine.
"""
import pytest
from unittest.mock import MagicMock

from app.services.fraud_service import FraudService, make_decision


class TestDecisionMapping:
    def test_approved_lower_bound(self):
        assert make_decision(0) == "APPROVED"

    def test_approved_upper_bound(self):
        assert make_decision(30) == "APPROVED"

    def test_review_lower_bound(self):
        assert make_decision(31) == "REVIEW"

    def test_review_upper_bound(self):
        assert make_decision(60) == "REVIEW"

    def test_reject_lower_bound(self):
        assert make_decision(61) == "REJECT"

    def test_reject_upper_bound(self):
        assert make_decision(100) == "REJECT"


class TestRuleEvaluation:
    @pytest.fixture
    def fraud_service(self, db_session):
        return FraudService(db_session)

    def _make_rule(self, name, rule_type, impact, is_active=True, config=None):
        rule = MagicMock()
        rule.rule_name = name
        rule.rule_type = rule_type
        rule.score_impact = impact
        rule.is_active = is_active
        rule.description = name
        rule.config = config or {}
        return rule

    def test_clean_email_no_flags(self, fraud_service):
        rules = [self._make_rule("disposable_email", "email", 25)]
        result = fraud_service.evaluate_rules(
            rules, email="john@gmail.com", phone=None, pan="ABCDE1234F",
            ip_address=None, device_id=None
        )
        assert result.total_score == 0
        assert len(result.reasons) == 0

    def test_disposable_email_flagged(self, fraud_service):
        rules = [self._make_rule("disposable_email", "email", 25)]
        result = fraud_service.evaluate_rules(
            rules, email="test@mailinator.com", phone=None, pan=None,
            ip_address=None, device_id=None
        )
        assert result.total_score == 25
        assert "disposable_email" in result.breakdown

    def test_invalid_pan_flagged(self, fraud_service):
        rules = [self._make_rule("invalid_pan_format", "document", 20)]
        result = fraud_service.evaluate_rules(
            rules, email="john@gmail.com", phone=None, pan="INVALID",
            ip_address=None, device_id=None
        )
        assert result.total_score == 20

    def test_valid_pan_not_flagged(self, fraud_service):
        rules = [self._make_rule("invalid_pan_format", "document", 20)]
        result = fraud_service.evaluate_rules(
            rules, email="john@gmail.com", phone=None, pan="ABCDE1234F",
            ip_address=None, device_id=None
        )
        assert result.total_score == 0

    def test_phone_reused_flagged(self, fraud_service):
        rules = [self._make_rule("phone_reused", "phone", 15)]
        result = fraud_service.evaluate_rules(
            rules, email="john@gmail.com", phone="+919999999999", pan=None,
            ip_address=None, device_id=None, phone_seen_before=True
        )
        assert result.total_score == 15

    def test_blacklisted_device_flagged(self, fraud_service):
        rules = [self._make_rule("blacklisted_device", "device", 30)]
        result = fraud_service.evaluate_rules(
            rules, email="john@gmail.com", phone=None, pan=None,
            ip_address=None, device_id="device_bad", device_blacklisted=True
        )
        assert result.total_score == 30

    def test_high_velocity_flagged(self, fraud_service):
        rules = [self._make_rule("high_velocity", "velocity", 25, config={"max_requests": 5})]
        result = fraud_service.evaluate_rules(
            rules, email="john@gmail.com", phone=None, pan=None,
            ip_address="103.44.1.1", device_id=None, ip_request_count=6
        )
        assert result.total_score == 25

    def test_score_clamped_at_100(self, fraud_service):
        rules = [
            self._make_rule("disposable_email", "email", 50),
            self._make_rule("invalid_pan_format", "document", 50),
            self._make_rule("blacklisted_device", "device", 50),
        ]
        result = fraud_service.evaluate_rules(
            rules, email="test@mailinator.com", phone=None, pan="BAD",
            ip_address=None, device_id="bad_device", device_blacklisted=True
        )
        assert result.total_score <= 100

    def test_inactive_rule_skipped(self, fraud_service):
        rules = [self._make_rule("disposable_email", "email", 25, is_active=False)]
        result = fraud_service.evaluate_rules(
            rules, email="test@mailinator.com", phone=None, pan=None,
            ip_address=None, device_id=None
        )
        assert result.total_score == 0

    def test_multiple_rules_accumulate(self, fraud_service):
        rules = [
            self._make_rule("disposable_email", "email", 25),
            self._make_rule("phone_reused", "phone", 15),
        ]
        result = fraud_service.evaluate_rules(
            rules, email="test@mailinator.com", phone="+919999999999", pan=None,
            ip_address=None, device_id=None, phone_seen_before=True
        )
        assert result.total_score == 40
        assert len(result.reasons) == 2
