from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    address = Column(String(255))
    city = Column(String(100))
    neighborhood = Column(String(100))
    category_id = Column(Integer, ForeignKey("categories.id"))
    description = Column(String(500))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Nuevos campos
    schedule = Column(String(200))  # Rango horario y días (ej: "Lun-Vie 8:00-18:00")
    website = Column(String(255))  # Sitio web
    photo_path = Column(String(500))  # Ruta local de la foto
    latitude = Column(Float)  # Latitud para Google Maps
    longitude = Column(Float)  # Longitud para Google Maps
    maps_url = Column(String(500))  # URL directa de Google Maps
    
    # Campo de validación
    is_verified = Column(Boolean, default=False)  # Si fue verificado por un usuario registrado
    verified_by = Column(Integer, ForeignKey("users.id"))  # Usuario que verificó
    verified_at = Column(DateTime)  # Cuándo fue verificado
    pending_changes_count = Column(Integer, default=0)  # Contador de cambios pendientes
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ContactHistory(Base):
    __tablename__ = "contact_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))  # Usuario que hizo el cambio
    field_name = Column(String(50), nullable=False)  # Campo que cambió
    old_value = Column(Text)  # Valor anterior
    new_value = Column(Text)  # Valor nuevo
    changed_at = Column(DateTime, server_default=func.now())  # Cuándo se hizo el cambio
