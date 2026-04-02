from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, CheckConstraint, Index
from sqlalchemy.sql import func
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(20), nullable=False)
    details = Column(Text)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "reason IN ('spam', 'falso', 'inapropiado', 'cerrado')",
            name="ck_report_reason"
        ),
        Index("idx_reports_unresolved", "is_resolved"),
    )
