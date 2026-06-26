import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_settings_development_weak_secret_key():
    # Should not raise any error
    settings = Settings(
        environment="development",
        secret_key="supersecretkey-change-in-production-min-32chars",
    )
    assert settings.secret_key == "supersecretkey-change-in-production-min-32chars"


def test_settings_production_strong_secret_key():
    # Should not raise any error
    settings = Settings(
        environment="production",
        secret_key="strong-secret-key-with-more-than-32-chars-minimum",
    )
    assert settings.secret_key == "strong-secret-key-with-more-than-32-chars-minimum"


def test_settings_production_weak_secret_key():
    # Should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            secret_key="supersecretkey-change-in-production-min-32chars",
        )
    assert (
        "SECURITY: `secret_key` must be set to a strong random value in production."
        in str(exc_info.value)
    )


def test_settings_production_short_secret_key():
    # Should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Settings(environment="production", secret_key="shortkey")
    assert (
        "SECURITY: `secret_key` must be set to a strong random value in production."
        in str(exc_info.value)
    )
