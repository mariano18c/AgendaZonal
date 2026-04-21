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
from app.services.badge_service import calculate_user_badges
from app.schemas.badge import BadgesResponse

router = APIRouter(tags=["provider"])


@router.get("/api/provider/dashboard")
def get_provider_dashboard(
    contacts_skip: int = Query(0, ge=0),
    contacts_limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Filter contacts by name"),
    sort: str | None = Query(None, description="Sort: leads_desc, name_asc"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dashboard metrics for a provider (user with contacts)."""
    # Get all contacts owned by this user
    query = db.query(Contact).filter(Contact.user_id == user.id)
    
    # Filter by name if provided
    if search:
        query = query.filter(Contact.name.ilike(f"%{search}%"))
    
    contacts = query.all()
    if not contacts:
        raise HTTPException(
            status_code=404,
            detail="No tienes contactos registrados. Creá un contacto primero."
        )
    
    # Sort contacts if requested
    if sort == "name_asc":
        contacts = sorted(contacts, key=lambda c: c.name.lower())
    elif sort == "leads_desc":
        # Need to count leads for each contact to sort
        lead_counts = {}
        for c in contacts:
            count = db.query(sqlfunc.count(LeadEvent.id)).filter(LeadEvent.contact_id == c.id).scalar() or 0
            lead_counts[c.id] = count
        contacts = sorted(contacts, key=lambda c: lead_counts.get(c.id, 0), reverse=True)
    
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

    # Average rating across all contacts
    ratings = [c.avg_rating for c in contacts if c.avg_rating and c.avg_rating > 0]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

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
        # Count leads for this contact
        leads_count = (
            db.query(sqlfunc.count(LeadEvent.id))
            .filter(LeadEvent.contact_id == c.id)
            .scalar() or 0
        )
        # Count active offers for this contact
        contact_active_offers = (
            db.query(sqlfunc.count(Offer.id))
            .filter(
                Offer.contact_id == c.id,
                Offer.is_active == True,
                Offer.expires_at > now,
            )
            .scalar() or 0
        )
        contact_summary.append({
            "id": c.id,
            "name": c.name,
            "avg_rating": c.avg_rating,
            "review_count": c.review_count,
            "verification_level": c.verification_level,
            "status": c.status,
            "leads_count": leads_count,
            "active_offers": contact_active_offers,
        })

    return {
        "contacts": contact_summary,
        "total_contacts": total_contacts,
        "leads_this_month": leads_this_month,
        "leads_last_month": leads_last_month,
        "avg_rating": avg_rating,
        "total_reviews": sum(c.review_count for c in contacts if c.review_count),
        "active_offers": active_offers,
        "leads_by_week": leads_by_week,
        "recent_reviews": review_list,
    }


@router.get("/api/provider/badges", response_model=BadgesResponse)
def get_provider_badges(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all badges for the current user (provider).
    
    Returns a list of all available badges with their earned status.
    """
    badges = calculate_user_badges(db, user)
    earned_count = sum(1 for b in badges if b.is_earned)
    
    return BadgesResponse(
        badges=badges,
        earned_count=earned_count,
        total_count=len(badges),
    )
