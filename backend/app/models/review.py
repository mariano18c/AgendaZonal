from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, CheckConstraint, Index
from sqlalchemy.sql import func
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    photo_path = Column(String(500))
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    # Reply from contact owner
    reply_text = Column(Text)
    reply_at = Column(DateTime)
    reply_by = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
        CheckConstraint("length(comment) <= 500", name="ck_review_comment_length"),
        Index("idx_reviews_approved", "is_approved"),
        # Un usuario solo puede reseñar un contacto una vez
        {"sqlite_autoincrement": True},
    )
