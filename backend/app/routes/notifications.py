"""Notifications router — list, manage, and push subscriptions."""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.auth import get_current_user
from app.config import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_CLAIM_EMAIL
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# VAPID public key (no auth required — frontend needs it to subscribe)
# ---------------------------------------------------------------------------

@router.get("/vapid-public-key")
def get_vapid_public_key():
    """Return the VAPID public key for push subscription."""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"public_key": VAPID_PUBLIC_KEY}


# ---------------------------------------------------------------------------
# Push subscription management
# ---------------------------------------------------------------------------

class SubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict  # { p256dh: str, auth: str }
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None


@router.post("/subscribe")
@limiter.limit("10/minute")
def subscribe_push(
    request: Request,
    body: SubscriptionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Subscribe to push notifications."""
    if not VAPID_PRIVATE_KEY:
        raise HTTPException(status_code=503, detail="Push notifications not configured")

    p256dh = body.keys.get("p256dh", "")
    auth = body.keys.get("auth", "")

    if not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Missing keys: p256dh and auth required")

    # Upsert: update if endpoint exists, create otherwise
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == body.endpoint
    ).first()

    if existing:
        existing.user_id = user.id
        existing.p256dh = p256dh
        existing.auth = auth
        existing.latitude = body.latitude
        existing.longitude = body.longitude
        existing.city = body.city
    else:
        subscription = PushSubscription(
            user_id=user.id,
            endpoint=body.endpoint,
            p256dh=p256dh,
            auth=auth,
            latitude=body.latitude,
            longitude=body.longitude,
            city=body.city
        )
        db.add(subscription)

    db.commit()
    logger.info(f"Push subscription saved for user {user.id}")
    return {"message": "Suscripción guardada"}


@router.post("/unsubscribe")
@limiter.limit("10/minute")
def unsubscribe_push(
    request: Request,
    body: SubscriptionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Unsubscribe from push notifications."""
    deleted = db.query(PushSubscription).filter(
        PushSubscription.endpoint == body.endpoint,
        PushSubscription.user_id == user.id,
    ).delete()
    db.commit()
    return {"message": "Suscripción eliminada" if deleted else "No encontrada"}


# ---------------------------------------------------------------------------
# Push sending helper
# ---------------------------------------------------------------------------

def send_push_to_user(db: Session, user_id: int, title: str, body: str, url: str = "/"):
    """Send a push notification to all subscriptions of a user.

    Args:
        db: Database session
        user_id: Target user ID
        title: Notification title
        body: Notification body text
        url: URL to open on click

    Returns:
        Number of successful sends
    """
    if not VAPID_PRIVATE_KEY:
        logger.warning("Push not configured — skipping notification")
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error("pywebpush not installed — run: pip install pywebpush")
        return 0

    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).all()

    if not subscriptions:
        return 0

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
    })

    success_count = 0
    expired = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth,
                    },
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_CLAIM_EMAIL,
                },
            )
            success_count += 1
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                # Subscription expired or gone
                expired.append(sub.id)
                logger.info(f"Push subscription {sub.id} expired (HTTP {e.response.status_code})")
            else:
                logger.warning(f"Push send failed for subscription {sub.id}: {e}")

    # Clean up expired subscriptions
    if expired:
        db.query(PushSubscription).filter(PushSubscription.id.in_(expired)).delete()
        db.commit()

    return success_count


def send_push_to_zone(db: Session, title: str, body: str, city: str | None = None, url: str = "/"):
    """Send a push notification to users in a specific city/zone.

    Args:
        db: Database session
        title: Notification title
        body: Notification body text
        city: Target city name (optional)
        url: URL to open on click

    Returns:
        Number of successful sends
    """
    if not VAPID_PRIVATE_KEY:
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return 0

    query = db.query(PushSubscription)
    if city:
        query = query.filter(PushSubscription.city.ilike(f"%{city}%"))
    
    subscriptions = query.all()
    if not subscriptions:
        return 0

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
    })

    success_count = 0
    expired = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth,
                    },
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_CLAIM_EMAIL,
                },
            )
            success_count += 1
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                expired.append(sub.id)
            else:
                logger.warning(f"Push send failed: {e}")

    if expired:
        db.query(PushSubscription).filter(PushSubscription.id.in_(expired)).delete()
        db.commit()

    return success_count


def send_push_to_all(db: Session, title: str, body: str, url: str = "/"):
    """Send a push notification to ALL subscribed users.

    Args:
        db: Database session
        title: Notification title
        body: Notification body text
        url: URL to open on click

    Returns:
        Number of successful sends
    """
    if not VAPID_PRIVATE_KEY:
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return 0

    subscriptions = db.query(PushSubscription).all()
    if not subscriptions:
        return 0

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
    })

    success_count = 0
    expired = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth,
                    },
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_CLAIM_EMAIL,
                },
            )
            success_count += 1
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                expired.append(sub.id)
            else:
                logger.warning(f"Push send failed: {e}")

    if expired:
        db.query(PushSubscription).filter(PushSubscription.id.in_(expired)).delete()
        db.commit()

    return success_count


def send_push_to_roles(db: Session, roles: list[str], title: str, body: str, url: str = "/"):
    """Send a push notification to users with specific roles.

    Args:
        db: Database session
        roles: List of roles to send to (e.g. ['admin', 'moderator'])
        title: Notification title
        body: Notification body text
        url: URL to open on click

    Returns:
        Number of successful sends
    """
    if not VAPID_PRIVATE_KEY:
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return 0

    # Get users with the specified roles
    users = db.query(User.id).filter(User.role.in_(roles)).all()
    user_ids = [u.id for u in users]

    if not user_ids:
        return 0

    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.user_id.in_(user_ids)
    ).all()

    if not subscriptions:
        return 0

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
    })

    success_count = 0
    expired = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth,
                    },
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_CLAIM_EMAIL,
                },
            )
            success_count += 1
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                expired.append(sub.id)
            else:
                logger.warning(f"Push send failed: {e}")

    if expired:
        db.query(PushSubscription).filter(PushSubscription.id.in_(expired)).delete()
        db.commit()

    return success_count


# ---------------------------------------------------------------------------
# Existing notification endpoints
# ---------------------------------------------------------------------------

@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the number of unread notifications for the current user."""
    count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List notifications for the current user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )


@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    notif.is_read = True
    db.commit()
    return {"message": "Marcada como leída"}


@router.put("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "Todas marcadas como leídas"}
