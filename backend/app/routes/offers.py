"""Offers CRUD router — flash offers with expiration."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.offer import Offer
from app.models.contact import Contact
from app.models.user import User
from app.schemas.offer import OfferCreate, OfferResponse
from app.auth import get_current_user

router = APIRouter(tags=["offers"])


def check_owner(contact_id: int, user: User, db: Session):
    """Verify the user owns the contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if contact.user_id != user.id and user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    return contact


@router.get("/api/contacts/{contact_id}/offers", response_model=list[OfferResponse])
def list_offers(
    contact_id: int,
    db: Session = Depends(get_db),
):
    """List active (non-expired) offers for a contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    now = datetime.now(timezone.utc)
    offers = (
        db.query(Offer)
        .filter(
            Offer.contact_id == contact_id,
            Offer.is_active == True,
            Offer.expires_at > now,
        )
        .order_by(Offer.expires_at.asc())
        .all()
    )
    return offers


@router.post("/api/contacts/{contact_id}/offers", response_model=OfferResponse, status_code=201)
def create_offer(
    contact_id: int,
    data: OfferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a flash offer for a contact (owner only)."""
    check_owner(contact_id, user, db)

    # Validate expires_at is in the future
    now = datetime.now(timezone.utc)
    if data.expires_at <= now:
        raise HTTPException(status_code=400, detail="La fecha de expiración debe ser futura")

    offer = Offer(
        contact_id=contact_id,
        title=data.title,
        description=data.description,
        discount_pct=data.discount_pct,
        expires_at=data.expires_at,
        is_active=True,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.put("/api/contacts/{contact_id}/offers/{offer_id}", response_model=OfferResponse)
def update_offer(
    contact_id: int,
    offer_id: int,
    data: OfferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an offer (owner only)."""
    check_owner(contact_id, user, db)

    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.contact_id == contact_id,
    ).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    offer.title = data.title
    offer.description = data.description
    offer.discount_pct = data.discount_pct
    offer.expires_at = data.expires_at
    db.commit()
    db.refresh(offer)
    return offer


@router.delete("/api/contacts/{contact_id}/offers/{offer_id}", status_code=204)
def delete_offer(
    contact_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete an offer (owner only)."""
    check_owner(contact_id, user, db)

    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.contact_id == contact_id,
    ).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    db.delete(offer)
    db.commit()
    return None
