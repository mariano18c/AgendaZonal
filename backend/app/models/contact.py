from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text, Index
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
    
    # Campos de ubicación y horario
    schedule = Column(String(200))  # Rango horario y días (ej: "Lun-Vie 8:00-18:00")
    website = Column(String(255))  # Sitio web
    photo_path = Column(String(500))  # Ruta local de la foto
    latitude = Column(Float)  # Latitud para geo queries
    longitude = Column(Float)  # Longitud para geo queries
    maps_url = Column(String(500))  # URL directa de Google Maps
    
    # Verificación (legacy + nuevo sistema de niveles)
    is_verified = Column(Boolean, default=False)  # DEPRECATED: usar verification_level
    verified_by = Column(Integer, ForeignKey("users.id"))
    verified_at = Column(DateTime)
    verification_level = Column(Integer, default=0)  # 0=sin_verificar, 1=básico, 2=documentado, 3=premium
    
    # Estado del contacto
    status = Column(String(20), default="active")  # active, flagged, suspended
    
    # Reseñas (cacheado)
    avg_rating = Column(Float, default=0)  # Promedio de ratings aprobados
    review_count = Column(Integer, default=0)  # Cantidad de reseñas aprobadas
    
    # Cambios pendientes
    pending_changes_count = Column(Integer, default=0)
    
    # Redes sociales y descripción larga
    instagram = Column(String(100))  # @usuario o URL
    facebook = Column(String(255))   # URL de Facebook
    about = Column(Text)             # Descripción larga (hasta 2000 chars)
    
    # Slug para URLs amigables
    slug = Column(String(200), index=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_contacts_geo", "latitude", "longitude"),
        Index("idx_contacts_status", "status"),
        Index("idx_contacts_verification", "verification_level"),
        Index("idx_contacts_rating", "avg_rating"),
    )


class ContactHistory(Base):
    __tablename__ = "contact_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))  # Usuario que hizo el cambio
    field_name = Column(String(50), nullable=False)  # Campo que cambió
    old_value = Column(Text)  # Valor anterior
    new_value = Column(Text)  # Valor nuevo
    changed_at = Column(DateTime, server_default=func.now())  # Cuándo se hizo el cambio
