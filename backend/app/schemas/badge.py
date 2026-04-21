"""Badge schemas for user achievements."""
from pydantic import BaseModel, ConfigDict
from enum import Enum
from datetime import datetime


class BadgeType(str, Enum):
    """Types of badges a provider can earn."""
    PRIMER_LEAD = "primer_lead"          # Primer contacto recibido
    LEADS_10 = "leads_10"                 # 10 contactos recibidos
    ESTRELLAS_5 = "estrellas_5"            # Promedio de rating >= 5
    CONTACTOS_5 = "contactos_5"          # 5 contactos guardados por otros usuarios
    STREAK = "streak"                     # 7 días consecutivos con actividad
    OFERTANTE = "ofertante"               # Primera oferta enviada


class BadgeSchema(BaseModel):
    """Schema for a single badge."""
    model_config = ConfigDict(from_attributes=True)

    type: BadgeType
    name: str
    description: str
    icon: str
    earned_at: datetime | None = None
    is_earned: bool = False


class BadgesResponse(BaseModel):
    """Response containing all badges for a user."""
    badges: list[BadgeSchema]
    earned_count: int
    total_count: int