from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class ContactChange(Base):
    __tablename__ = "contact_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))  # NULL if user not registered
    field_name = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text, nullable=False)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
