"""PushSubscription model for Web Push notifications."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Float
from app.database import Base


class PushSubscription(Base):
    """Stores Web Push subscriptions from browsers.

    Each subscription represents a browser endpoint that can receive
    push notifications via the Web Push Protocol + VAPID.
    """
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False, unique=True)
    p256dh = Column(String(200), nullable=False)
    auth = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
