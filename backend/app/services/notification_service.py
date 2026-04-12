"""Notification service with web push support.

Stores notifications in the DB and sends web push to all registered subscriptions.
"""

import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.notification import Notification, PushSubscription

logger = logging.getLogger(__name__)


async def send_notification(
    type: str,
    title: str,
    body: str | None = None,
    account_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    db: AsyncSession | None = None,
):
    """Create a notification and send web push to all subscribers."""
    close_session = False
    if db is None:
        db = async_session()
        close_session = True

    try:
        # Store in DB
        notif = Notification(
            type=type,
            title=title,
            body=body,
            account_id=account_id,
            order_id=order_id,
        )
        db.add(notif)
        await db.commit()

        # Send web push
        result = await db.execute(select(PushSubscription))
        subscriptions = result.scalars().all()

        if not subscriptions:
            return

        payload = json.dumps({
            "title": title,
            "body": body or "",
            "type": type,
            "notification_id": str(notif.id),
        })

        try:
            from pywebpush import webpush, WebPushException
            from app.config import settings

            vapid_private_key = getattr(settings, "vapid_private_key", "")
            vapid_email = getattr(settings, "vapid_email", "mailto:admin@tradingbuddy.app")

            if not vapid_private_key:
                logger.debug("VAPID key not configured, skipping web push")
                return

            for sub in subscriptions:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {
                                "p256dh": sub.p256dh_key,
                                "auth": sub.auth_key,
                            },
                        },
                        data=payload,
                        vapid_private_key=vapid_private_key,
                        vapid_claims={"sub": vapid_email},
                    )
                except WebPushException as e:
                    if e.response and e.response.status_code in (404, 410):
                        # Subscription expired, remove it
                        await db.delete(sub)
                        await db.commit()
                        logger.info(f"Removed expired push subscription")
                    else:
                        logger.error(f"Web push failed: {e}")
                except Exception as e:
                    logger.error(f"Web push error: {e}")

        except ImportError:
            logger.debug("pywebpush not installed, skipping web push")

    finally:
        if close_session:
            await db.close()
