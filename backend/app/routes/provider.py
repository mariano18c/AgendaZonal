"""Provider dashboard router — metrics for contact owners."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.database import get_db
from app.models.contact import Contact
from app.models.lead_event import LeadEvent
from app.models.offer import Offer
from app.models.review import Review
from app.models.user import User
from app.auth import get_current_user

router = APIRouter(tags=["provider"])


@router.get("/api/provider/dashboard")
def get_provider_dashboard(
    contacts_skip: int = Query(0, ge=0),
    contacts_limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dashboard metrics for a provider (user with contacts)."""
    # Get all contacts owned by this user
    contacts = db.query(Contact).filter(Contact.user_id == user.id).all()
    if not contacts:
        raise HTTPException(
            status_code=404,
            detail="No tienes contactos registrados. Creá un contacto primero."
        )

    contact_ids = [c.id for c in contacts]
    now = datetime.now(timezone.utc)

    # Leads this month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    leads_this_month = (
        db.query(sqlfunc.count(LeadEvent.id))
        .filter(
            LeadEvent.contact_id.in_(contact_ids),
            LeadEvent.created_at >= month_start,
        )
        .scalar() or 0
    )

    # Leads last month
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start
    leads_last_month = (
        db.query(sqlfunc.count(LeadEvent.id))
        .filter(
            LeadEvent.contact_id.in_(contact_ids),
            LeadEvent.created_at >= last_month_start,
            LeadEvent.created_at < last_month_end,
        )
        .scalar() or 0
    )

    # Active offers
    active_offers = (
        db.query(sqlfunc.count(Offer.id))
        .filter(
            Offer.contact_id.in_(contact_ids),
            Offer.is_active == True,
            Offer.expires_at > now,
        )
        .scalar() or 0
    )

    # Leads by week (last 4 weeks)
    leads_by_week = []
    for i in range(4):
        week_end = now - timedelta(weeks=i)
        week_start = week_end - timedelta(weeks=1)
        count = (
            db.query(sqlfunc.count(LeadEvent.id))
            .filter(
                LeadEvent.contact_id.in_(contact_ids),
                LeadEvent.created_at >= week_start,
                LeadEvent.created_at < week_end,
            )
            .scalar() or 0
        )
        leads_by_week.append({
            "week_start": week_start.strftime("%d/%m"),
            "count": count,
        })
    leads_by_week.reverse()

    # Recent reviews (last 10)
    recent_reviews = (
        db.query(Review)
        .filter(Review.contact_id.in_(contact_ids))
        .order_by(Review.created_at.desc())
        .limit(10)
        .all()
    )
    review_list = []
    for r in recent_reviews:
        reviewer = db.query(User).filter(User.id == r.user_id).first()
        contact = db.query(Contact).filter(Contact.id == r.contact_id).first()
        review_list.append({
            "id": r.id,
            "contact_name": contact.name if contact else "Desconocido",
            "username": reviewer.username if reviewer else "Usuario",
            "rating": r.rating,
            "comment": r.comment,
            "is_approved": r.is_approved,
            "created_at": r.created_at,
        })

    # Per-contact summary with pagination
    total_contacts = len(contacts)
    paginated_contacts = contacts[contacts_skip:contacts_skip + contacts_limit]
    contact_summary = []
    for c in paginated_contacts:
        contact_summary.append({
            "id": c.id,
            "name": c.name,
            "avg_rating": c.avg_rating,
            "review_count": c.review_count,
            "verification_level": c.verification_level,
            "status": c.status,
        })

    return {
        "contacts": contact_summary,
        "total_contacts": total_contacts,
        "leads_this_month": leads_this_month,
        "leads_last_month": leads_last_month,
        "active_offers": active_offers,
        "leads_by_week": leads_by_week,
        "recent_reviews": review_list,
    }
