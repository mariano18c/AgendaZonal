from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Index
from sqlalchemy.sql import func
from app.database import Base


class UtilityItem(Base):
    __tablename__ = "utility_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False, default="otro")  # farmacia_turno, emergencia, otro
    name = Column(String(200), nullable=False)
    address = Column(String(255))
    phone = Column(String(20))
    schedule = Column(String(200))
    lat = Column(Float)
    lon = Column(Float)
    city = Column(String(100))
    is_priority = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_utilities_type", "type"),
        Index("idx_utilities_active", "is_active"),
    )
