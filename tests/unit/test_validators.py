"""
Unit tests for validation utilities.
"""
import pytest

from app.utils.validators import (
    is_disposable_email,
    is_private_ip,
    is_valid_ip,
    is_valid_pan,
    is_valid_phone,
)


class TestPANValidation:
    def test_valid_pan(self):
        assert is_valid_pan("ABCDE1234F") is True

    def test_valid_pan_uppercase(self):
        assert is_valid_pan("PQRST5678G") is True

    def test_invalid_pan_lowercase(self):
        assert is_valid_pan("abcde1234f") is False

    def test_invalid_pan_too_short(self):
        assert is_valid_pan("ABCD1234F") is False

    def test_invalid_pan_wrong_format(self):
        assert is_valid_pan("1234567890") is False

    def test_invalid_pan_special_chars(self):
        assert is_valid_pan("ABCDE123@F") is False

    def test_empty_pan(self):
        assert is_valid_pan("") is False


class TestDisposableEmail:
    def test_disposable_mailinator(self):
        assert is_disposable_email("test@mailinator.com") is True

    def test_disposable_guerrillamail(self):
        assert is_disposable_email("hello@guerrillamail.com") is True

    def test_disposable_yopmail(self):
        assert is_disposable_email("user@yopmail.com") is True

    def test_legitimate_gmail(self):
        assert is_disposable_email("user@gmail.com") is False

    def test_legitimate_corporate(self):
        assert is_disposable_email("john@acme.com") is False

    def test_missing_at_sign(self):
        assert is_disposable_email("notanemail") is False

    def test_empty_email(self):
        assert is_disposable_email("") is False


class TestIPValidation:
    def test_valid_public_ip(self):
        assert is_valid_ip("8.8.8.8") is True

    def test_valid_ipv6(self):
        assert is_valid_ip("2001:db8::1") is True

    def test_invalid_ip(self):
        assert is_valid_ip("999.999.999.999") is False

    def test_private_ip_192(self):
        assert is_private_ip("192.168.1.1") is True

    def test_private_ip_10(self):
        assert is_private_ip("10.0.0.1") is True

    def test_loopback(self):
        assert is_private_ip("127.0.0.1") is True

    def test_public_ip_not_private(self):
        assert is_private_ip("8.8.8.8") is False
