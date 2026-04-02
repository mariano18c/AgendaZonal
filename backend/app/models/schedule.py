from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index, CheckConstraint
from app.database import Base


class Schedule(Base):
    """Structured schedule per contact. One row per day."""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Lunes ... 6=Domingo
    open_time = Column(String(5))  # "08:00" or NULL if closed
    close_time = Column(String(5))  # "18:00" or NULL if closed

    __table_args__ = (
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_schedule_day"),
        Index("idx_schedules_contact", "contact_id", "day_of_week"),
    )
