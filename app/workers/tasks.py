"""
Celery background tasks.
"""

import asyncio
from uuid import UUID

from app.workers.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.write_audit_log_task", queue="audit", max_retries=3)
def write_audit_log_task(
    action: str,
    status: str = "success",
    endpoint: str | None = None,
    method: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    actor_id: str | None = None,
    org_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Persist an audit log entry to the database."""

    async def _write():
        from app.db.session import AsyncSessionLocal
        from app.models.audit_log import AuditLog

        async with AsyncSessionLocal() as session:
            log = AuditLog(
                action=action,
                status=status,
                endpoint=endpoint,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
                actor_id=UUID(actor_id) if actor_id else None,
                organization_id=UUID(org_id) if org_id else None,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata_=metadata or {},
            )
            session.add(log)
            await session.commit()

    _run_async(_write())


@celery_app.task(name="app.workers.tasks.send_email_task", queue="email", max_retries=3)
def send_email_task(
    to: str,
    subject: str,
    body_html: str,
    body_text: str | None = None,
) -> None:
    """Send an email via Mailpit SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from app.core.config import settings

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    msg["To"] = to

    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(settings.mailpit_host, settings.mailpit_port) as smtp:
        smtp.sendmail(settings.email_from, to, msg.as_string())


@celery_app.task(name="app.workers.tasks.update_device_cache_task", queue="default")
def update_device_cache_task(device_id: str, org_id: str) -> None:
    """Register a device_id in Redis for future checks."""
    import redis

    from app.core.config import settings

    r = redis.from_url(settings.redis_url)
    key = f"vt:device:{device_id}"
    r.incr(key)
    r.expire(key, 86400 * 90)  # 90 days
    r.close()
