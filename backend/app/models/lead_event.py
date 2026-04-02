from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # NULL si anónimo
    source = Column(String(20), nullable=False, default="whatsapp")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_leads_date", "created_at"),
    )
