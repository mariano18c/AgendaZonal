from sqlalchemy import Column, Integer, String
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(Integer, unique=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50))
    description = Column(String(255))
