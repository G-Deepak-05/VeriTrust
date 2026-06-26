from app.models.verification import VerificationResult
from app.repositories.api_key_repository import APIKeyRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.base_repository import BaseRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.verification_repository import VerificationRepository


async def test_org_repo_get_by_slug(db_session, test_org):
    repo = OrganizationRepository(db_session)
    org = await repo.get_by_slug(test_org.slug)
    assert org is not None
    assert org.id == test_org.id

    nonexistent = await repo.get_by_slug("non-existent-slug-xyz")
    assert nonexistent is None


async def test_user_repo_get_by_email(db_session, test_user):
    repo = UserRepository(db_session)
    user = await repo.get_by_email(test_user.email)
    assert user is not None
    assert user.id == test_user.id

    nonexistent = await repo.get_by_email("nonexistent-email@abc.com")
    assert nonexistent is None


async def test_api_key_repo_get_by_hash_and_org(db_session, test_org):
    repo = APIKeyRepository(db_session)

    # create key
    key = await repo.create(
        organization_id=test_org.id,
        name="test key",
        hashed_secret="some_hash_val",
        key_prefix="vt_live_ab12",
        is_active=True,
    )
    assert key.id is not None

    found = await repo.get_by_hash("some_hash_val")
    assert found is not None
    assert found.id == key.id

    # update last used
    await repo.update_last_used(key.id)

    keys = await repo.get_by_org(test_org.id)
    assert len(keys) > 0


async def test_audit_log_repo_by_actor(db_session, test_org, test_user):
    repo = AuditLogRepository(db_session)
    log = await repo.create(
        organization_id=test_org.id,
        actor_id=test_user.id,
        action="user.login",
        endpoint="/api/v1/auth/login",
        method="POST",
        status="success",
        ip_address="127.0.0.1",
    )
    assert log.id is not None

    items, total = await repo.get_by_actor(test_user.id)
    assert total > 0
    assert items[0].id == log.id


async def test_refresh_token_repo(db_session, test_user):
    repo = RefreshTokenRepository(db_session)
    token = await repo.create_token(
        user_id=test_user.id,
        hashed_token="hashed_refresh_token",
        session_id="session_xyz",
    )
    assert token.id is not None

    found = await repo.get_by_hash("hashed_refresh_token")
    assert found is not None
    assert found.id == token.id

    await repo.revoke(token)
    assert token.is_revoked is True

    await repo.revoke_all_for_user(test_user.id)
    await repo.revoke_session("session_xyz")


async def test_verification_repo_stats(db_session, test_org):
    repo = VerificationRepository(db_session)
    # create req
    req = await repo.create(
        organization_id=test_org.id,
        name="John Doe",
        email="john@doe.com",
    )

    # create result using session db directly or model
    res_repo = BaseRepository[VerificationResult](db_session)
    res_repo.model = VerificationResult
    res = await res_repo.create(
        request_id=req.id,
        risk_score=35,
        decision="REVIEW",
        reasons=[],
        rule_breakdown={},
    )
    assert res.id is not None

    stats = await repo.get_stats(test_org.id)
    assert stats["total"] == 1
    assert stats["review"] == 1
    assert stats["approval_rate"] == 0.0
