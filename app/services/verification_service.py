"""
Verification pipeline service — 10-step identity verification workflow.
"""
import time
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.verification import VerificationRequest, VerificationResult
from app.repositories.fraud_rule_repository import FraudRuleRepository
from app.repositories.verification_repository import VerificationRepository
from app.schemas.verification import (
    VerificationDetailResponse,
    VerificationHistoryItem,
    VerificationInput,
    VerificationResponse,
)
from app.services.fraud_service import FraudService, make_decision
from app.utils.validators import is_disposable_email, is_valid_pan, is_valid_phone

logger = get_logger(__name__)

# Redis key templates
_DEVICE_KEY = "vt:device:{device_id}"
_PHONE_KEY = "vt:phone:{phone}"
_IP_VELOCITY_KEY = "vt:ip_velocity:{ip}"
_DEVICE_BLACKLIST_KEY = "vt:device_blacklist"


class VerificationService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self.db = db
        self.redis = redis
        self.repo = VerificationRepository(db)
        self.fraud_service = FraudService(db)
        self.fraud_rule_repo = FraudRuleRepository(db)

    async def submit(
        self, org_id: uuid.UUID, data: VerificationInput
    ) -> VerificationResponse:
        """
        Run the full 10-step verification pipeline.

        Returns risk score, decision, and reasons synchronously.
        """
        start_ms = time.monotonic()

        # Step 1: Persist the request
        vr = await self.repo.create(
            organization_id=org_id,
            name=data.name,
            email=data.email,
            phone=data.phone,
            pan=data.pan,
            ip_address=data.ip_address,
            device_id=data.device_id,
            status="processing",
        )

        # Steps 2-6: Enrichment checks (Redis lookups)
        phone_seen = await self._check_phone_seen(data.phone)
        device_blacklisted = await self._check_device_blacklisted(data.device_id)
        ip_count = await self._get_ip_velocity(data.ip_address)

        # Step 7: Load fraud rules
        rules = await self.fraud_rule_repo.get_active_rules(org_id)

        # Step 8: Evaluate rules
        rule_result = self.fraud_service.evaluate_rules(
            rules,
            email=data.email,
            phone=data.phone,
            pan=data.pan,
            ip_address=data.ip_address,
            device_id=data.device_id,
            phone_seen_before=phone_seen,
            device_blacklisted=device_blacklisted,
            ip_request_count=ip_count,
        )

        # Step 9: Decision
        decision = make_decision(rule_result.total_score)
        processing_ms = int((time.monotonic() - start_ms) * 1000)

        # Step 10: Persist result
        from app.models.verification import VerificationResult as VRModel
        result_obj = VRModel(
            request_id=vr.id,
            risk_score=rule_result.total_score,
            decision=decision,
            reasons=rule_result.reasons,
            processing_ms=processing_ms,
            rule_breakdown=rule_result.breakdown,
        )
        self.db.add(result_obj)
        await self.repo.update(vr, status="completed")

        # Update Redis counters (fire-and-forget style)
        await self._update_redis_counters(data)

        logger.info(
            "Verification completed",
            verification_id=str(vr.id),
            score=rule_result.total_score,
            decision=decision,
            processing_ms=processing_ms,
        )

        # Dispatch audit log via Celery
        try:
            from app.workers.tasks import write_audit_log_task
            write_audit_log_task.delay(
                action="verification.completed",
                resource_id=str(vr.id),
                org_id=str(org_id),
                metadata={"decision": decision, "score": rule_result.total_score},
            )
        except Exception:
            pass  # Never fail on audit log

        return VerificationResponse(
            verification_id=vr.id,
            risk_score=rule_result.total_score,
            decision=decision,
            reasons=rule_result.reasons,
            processing_ms=processing_ms,
            created_at=vr.created_at,
        )

    async def get_verification(
        self, verification_id: uuid.UUID, org_id: uuid.UUID
    ) -> VerificationDetailResponse:
        vr = await self.repo.get(verification_id)
        if not vr or vr.organization_id != org_id:
            raise NotFoundError("Verification", str(verification_id))

        result = vr.result
        return VerificationDetailResponse(
            verification_id=vr.id,
            risk_score=result.risk_score if result else 0,
            decision=result.decision if result else "PENDING",
            reasons=result.reasons if result else [],
            processing_ms=result.processing_ms if result else 0,
            created_at=vr.created_at,
            name=vr.name,
            email=vr.email,
            phone=vr.phone,
            pan=vr.pan,
            ip_address=vr.ip_address,
            device_id=vr.device_id,
            status=vr.status,
            rule_breakdown=result.rule_breakdown if result else {},
        )

    async def get_history(
        self, org_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[VerificationHistoryItem], int]:
        offset = (page - 1) * page_size
        items, total = await self.repo.get_by_org(org_id, offset=offset, limit=page_size)
        history = []
        for item in items:
            result = item.result
            history.append(
                VerificationHistoryItem(
                    verification_id=item.id,
                    email=item.email,
                    risk_score=result.risk_score if result else 0,
                    decision=result.decision if result else "PENDING",
                    status=item.status,
                    created_at=item.created_at,
                )
            )
        return history, total

    # ─── Redis Helpers ────────────────────────────────────────────────────────
    async def _check_phone_seen(self, phone: str | None) -> bool:
        if not phone:
            return False
        key = _PHONE_KEY.format(phone=phone)
        count = await self.redis.get(key)
        return int(count or 0) > 0

    async def _check_device_blacklisted(self, device_id: str | None) -> bool:
        if not device_id:
            return False
        return bool(await self.redis.sismember(_DEVICE_BLACKLIST_KEY, device_id))

    async def _get_ip_velocity(self, ip: str | None) -> int:
        if not ip:
            return 0
        key = _IP_VELOCITY_KEY.format(ip=ip)
        count = await self.redis.get(key)
        return int(count or 0)

    async def _update_redis_counters(self, data: VerificationInput) -> None:
        """Increment phone and IP velocity counters in Redis."""
        pipe = self.redis.pipeline()
        if data.phone:
            key = _PHONE_KEY.format(phone=data.phone)
            pipe.incr(key)
            pipe.expire(key, 86400 * 30)  # 30 days
        if data.ip_address:
            key = _IP_VELOCITY_KEY.format(ip=data.ip_address)
            pipe.incr(key)
            pipe.expire(key, 3600)  # 1 hour window
        await pipe.execute()
