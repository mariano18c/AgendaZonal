from sqlalchemy import Column, Integer, String, ForeignKey, Index
from app.database import Base


class ContactPhoto(Base):
    """Multiple photos per contact (max 5)."""
    __tablename__ = "contact_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_path = Column(String(500), nullable=False)
    caption = Column(String(200))
    sort_order = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_photos_contact_order", "contact_id", "sort_order"),
    )
