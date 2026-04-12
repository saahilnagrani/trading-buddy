import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification, PushSubscription

router = APIRouter()


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    account_id: uuid.UUID | None
    order_id: uuid.UUID | None
    is_read: bool
    created_at: str

    model_config = {"from_attributes": True}


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str
    user_agent: str | None = None


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    type: str | None = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).order_by(desc(Notification.created_at)).limit(limit)
    if type:
        query = query.where(Notification.type == type)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    result = await db.execute(query)
    notifs = result.scalars().all()
    return [
        NotificationResponse(
            id=n.id,
            type=n.type,
            title=n.title,
            body=n.body,
            account_id=n.account_id,
            order_id=n.order_id,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        )
        for n in notifs
    ]


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(func.count(Notification.id)).where(Notification.is_read.is_(False))
    )
    return {"count": result.scalar() or 0}


@router.put("/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"status": "ok"}


@router.put("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification).where(Notification.is_read.is_(False)).values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}


@router.post("/subscribe", status_code=201)
async def subscribe_push(req: PushSubscribeRequest, db: AsyncSession = Depends(get_db)):
    # Upsert by endpoint
    existing = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == req.endpoint)
    )
    sub = existing.scalar_one_or_none()
    if sub:
        sub.p256dh_key = req.p256dh_key
        sub.auth_key = req.auth_key
        sub.user_agent = req.user_agent
    else:
        sub = PushSubscription(
            endpoint=req.endpoint,
            p256dh_key=req.p256dh_key,
            auth_key=req.auth_key,
            user_agent=req.user_agent,
        )
        db.add(sub)
    await db.commit()
    return {"status": "subscribed"}


@router.delete("/subscribe")
async def unsubscribe_push(endpoint: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    sub = result.scalar_one_or_none()
    if sub:
        await db.delete(sub)
        await db.commit()
    return {"status": "unsubscribed"}
