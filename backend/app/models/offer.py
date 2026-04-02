from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, CheckConstraint, Index
from sqlalchemy.sql import func
from app.database import Base


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))
    discount_pct = Column(Integer)  # 1-99, nullable
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("discount_pct >= 1 AND discount_pct <= 99", name="ck_offer_discount"),
        Index("idx_offers_active", "is_active", "expires_at"),
    )
