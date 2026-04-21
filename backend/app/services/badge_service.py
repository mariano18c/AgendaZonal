"""Badge calculation service for user achievements."""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, distinct

from app.models.contact import Contact
from app.models.lead_event import LeadEvent
from app.models.review import Review
from app.models.offer import Offer
from app.models.user import User
from app.schemas.badge import BadgeType, BadgeSchema


# Badge definitions with metadata
BADGE_DEFINITIONS = {
    BadgeType.PRIMER_LEAD: {
        "name": "Primer Lead",
        "description": "Primer contacto recibido",
        "icon": "📩",
    },
    BadgeType.LEADS_10: {
        "name": "10 Leads",
        "description": "10 contactos recibidos",
        "icon": "📨",
    },
    BadgeType.ESTRELLAS_5: {
        "name": "5 Estrellas",
        "description": "Promedio de rating >= 5",
        "icon": "⭐",
    },
    BadgeType.CONTACTOS_5: {
        "name": "5 Contactos",
        "description": "5 contactos guardados por otros usuarios",
        "icon": "🔖",
    },
    BadgeType.STREAK: {
        "name": "Streak",
        "description": "7 días consecutivos con actividad",
        "icon": "🔥",
    },
    BadgeType.OFERTANTE: {
        "name": "Ofertante",
        "description": "Primera oferta enviada",
        "icon": "🏷️",
    },
}


def calculate_user_badges(db: Session, user: User) -> list[BadgeSchema]:
    """Calculate all badges for a user based on their activity.
    
    Args:
        db: Database session
        user: The user to calculate badges for
        
    Returns:
        List of BadgeSchema objects with earned status
    """
    badges = []
    
    # Get all contacts owned by the user
    contacts = db.query(Contact).filter(Contact.user_id == user.id).all()
    contact_ids = [c.id for c in contacts]
    
    # If user has no contacts, return all badges as not earned
    if not contact_ids:
        return _create_empty_badges()
    
    # --- Badge 1: PRIMER_LEAD ---
    primer_lead = _check_primer_lead(db, contact_ids)
    
    # --- Badge 2: LEADS_10 ---
    leads_10 = _check_leads_10(db, contact_ids)
    
    # --- Badge 3: ESTRELLAS_5 ---
    estrellas_5 = _check_estrellas_5(db, contacts)
    
    # --- Badge 4: CONTACTOS_5 ---
    contactos_5 = _check_contactos_5(db, contact_ids)
    
    # --- Badge 5: STREAK ---
    streak = _check_streak(db, user.id, contact_ids)
    
    # --- Badge 6: OFERTANTE ---
    ofertante = _check_ofertante(db, contact_ids)
    
    # Collect all badges
    badges.extend([primer_lead, leads_10, estrellas_5, contactos_5, streak, ofertante])
    
    return badges


def _check_primer_lead(db: Session, contact_ids: list[int]) -> BadgeSchema:
    """Check if user has received at least one lead."""
    lead_count = (
        db.query(sqlfunc.count(LeadEvent.id))
        .filter(LeadEvent.contact_id.in_(contact_ids))
        .scalar() or 0
    )
    
    earned_at = None
    if lead_count >= 1:
        # Get the first lead date
        first_lead = (
            db.query(LeadEvent)
            .filter(LeadEvent.contact_id.in_(contact_ids))
            .order_by(LeadEvent.created_at.asc())
            .first()
        )
        earned_at = first_lead.created_at if first_lead else None
    
    return BadgeSchema(
        type=BadgeType.PRIMER_LEAD,
        name=BADGE_DEFINITIONS[BadgeType.PRIMER_LEAD]["name"],
        description=BADGE_DEFINITIONS[BadgeType.PRIMER_LEAD]["description"],
        icon=BADGE_DEFINITIONS[BadgeType.PRIMER_LEAD]["icon"],
        is_earned=lead_count >= 1,
        earned_at=earned_at,
    )


def _check_leads_10(db: Session, contact_ids: list[int]) -> BadgeSchema:
    """Check if user has received at least 10 leads."""
    lead_count = (
        db.query(sqlfunc.count(LeadEvent.id))
        .filter(LeadEvent.contact_id.in_(contact_ids))
        .scalar() or 0
    )
    
    earned_at = None
    if lead_count >= 10:
        # Get the 10th lead date
        tenth_lead = (
            db.query(LeadEvent)
            .filter(LeadEvent.contact_id.in_(contact_ids))
            .order_by(LeadEvent.created_at.asc())
            .offset(9)
            .first()
        )
        earned_at = tenth_lead.created_at if tenth_lead else None
    
    return BadgeSchema(
        type=BadgeType.LEADS_10,
        name=BADGE_DEFINITIONS[BadgeType.LEADS_10]["name"],
        description=BADGE_DEFINITIONS[BadgeType.LEADS_10]["description"],
        icon=BADGE_DEFINITIONS[BadgeType.LEADS_10]["icon"],
        is_earned=lead_count >= 10,
        earned_at=earned_at,
    )


def _check_estrellas_5(db: Session, contacts: list[Contact]) -> BadgeSchema:
    """Check if user has average rating >= 5 (all contacts must have 5 stars)."""
    # Get all approved reviews for user's contacts
    contact_ids = [c.id for c in contacts]
    
    # Calculate the overall average rating from contacts
    ratings = [c.avg_rating for c in contacts if c.avg_rating and c.avg_rating > 0]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    earned_at = None
    if avg_rating >= 5 and ratings:
        # Get the date when the average first reached 5
        # For simplicity, we get the latest review date when avg is 5+
        latest_review = (
            db.query(Review)
            .filter(
                Review.contact_id.in_(contact_ids),
                Review.is_approved == True,
            )
            .order_by(Review.created_at.desc())
            .first()
        )
        earned_at = latest_review.created_at if latest_review else None
    
    return BadgeSchema(
        type=BadgeType.ESTRELLAS_5,
        name=BADGE_DEFINITIONS[BadgeType.ESTRELLAS_5]["name"],
        description=BADGE_DEFINITIONS[BadgeType.ESTRELLAS_5]["description"],
        icon=BADGE_DEFINITIONS[BadgeType.ESTRELLAS_5]["icon"],
        is_earned=avg_rating >= 5 and len(ratings) > 0,
        earned_at=earned_at,
    )


def _check_contactos_5(db: Session, contact_ids: list[int]) -> BadgeSchema:
    """Check if user's contacts have been saved 5+ times by other users.
    
    This is based on unique user_ids in lead_events for each contact,
    representing how many different users showed interest.
    """
    # Count distinct users who created leads for each contact
    total_saves = 0
    earned_at = None
    
    for contact_id in contact_ids:
        distinct_users = (
            db.query(sqlfunc.count(distinct(LeadEvent.user_id)))
            .filter(
                LeadEvent.contact_id == contact_id,
                LeadEvent.user_id.isnot(None),
            )
            .scalar() or 0
        )
        total_saves += distinct_users
    
    if total_saves >= 5:
        # Get the 5th save date
        fifth_save = (
            db.query(LeadEvent)
            .filter(
                LeadEvent.contact_id.in_(contact_ids),
                LeadEvent.user_id.isnot(None),
            )
            .order_by(LeadEvent.created_at.asc())
            .offset(4)
            .first()
        )
        earned_at = fifth_save.created_at if fifth_save else None
    
    return BadgeSchema(
        type=BadgeType.CONTACTOS_5,
        name=BADGE_DEFINITIONS[BadgeType.CONTACTOS_5]["name"],
        description=BADGE_DEFINITIONS[BadgeType.CONTACTOS_5]["description"],
        icon=BADGE_DEFINITIONS[BadgeType.CONTACTOS_5]["icon"],
        is_earned=total_saves >= 5,
        earned_at=earned_at,
    )


def _check_streak(db: Session, user_id: int, contact_ids: list[int]) -> BadgeSchema:
    """Check if user has 7 consecutive days with activity.
    
    Activity includes: leads, reviews, or offers created.
    """
    now = datetime.now(timezone.utc)
    
    # Get all activity dates in the last 30 days
    activity_dates = set()
    
    # Lead events
    lead_dates = (
        db.query(sqlfunc.date(LeadEvent.created_at))
        .filter(
            LeadEvent.contact_id.in_(contact_ids),
            LeadEvent.created_at >= now - timedelta(days=30),
        )
        .distinct()
        .all()
    )
    for (date,) in lead_dates:
        if date:
            activity_dates.add(date)
    
    # Reviews (on user's contacts)
    review_dates = (
        db.query(sqlfunc.date(Review.created_at))
        .filter(
            Review.contact_id.in_(contact_ids),
            Review.created_at >= now - timedelta(days=30),
        )
        .distinct()
        .all()
    )
    for (date,) in review_dates:
        if date:
            activity_dates.add(date)
    
    # Offers (created by user for their contacts)
    offer_dates = (
        db.query(sqlfunc.date(Offer.created_at))
        .filter(
            Offer.contact_id.in_(contact_ids),
            Offer.created_at >= now - timedelta(days=30),
        )
        .distinct()
    )
    for (date,) in offer_dates:
        if date:
            activity_dates.add(date)
    
    # Sort dates and find longest streak
    if not activity_dates:
        return BadgeSchema(
            type=BadgeType.STREAK,
            name=BADGE_DEFINITIONS[BadgeType.STREAK]["name"],
            description=BADGE_DEFINITIONS[BadgeType.STREAK]["description"],
            icon=BADGE_DEFINITIONS[BadgeType.STREAK]["icon"],
            is_earned=False,
            earned_at=None,
        )
    
    sorted_dates = sorted(activity_dates)
    max_streak = 1
    current_streak = 1
    streak_end_date = sorted_dates[0]
    
    for i in range(1, len(sorted_dates)):
        prev_date = sorted_dates[i - 1]
        curr_date = sorted_dates[i]
        
        # Check if consecutive days
        if (curr_date - prev_date).days == 1:
            current_streak += 1
            if current_streak >= max_streak:
                max_streak = current_streak
                streak_end_date = curr_date
        else:
            current_streak = 1
    
    earned_at = None
    if max_streak >= 7:
        # Convert date to datetime
        earned_at = datetime.combine(streak_end_date, datetime.min.time())
        earned_at = earned_at.replace(tzinfo=timezone.utc)
    
    return BadgeSchema(
        type=BadgeType.STREAK,
        name=BADGE_DEFINITIONS[BadgeType.STREAK]["name"],
        description=BADGE_DEFINITIONS[BadgeType.STREAK]["description"],
        icon=BADGE_DEFINITIONS[BadgeType.STREAK]["icon"],
        is_earned=max_streak >= 7,
        earned_at=earned_at,
    )


def _check_ofertante(db: Session, contact_ids: list[int]) -> BadgeSchema:
    """Check if user has sent at least one offer."""
    offer_count = (
        db.query(sqlfunc.count(Offer.id))
        .filter(Offer.contact_id.in_(contact_ids))
        .scalar() or 0
    )
    
    earned_at = None
    if offer_count >= 1:
        first_offer = (
            db.query(Offer)
            .filter(Offer.contact_id.in_(contact_ids))
            .order_by(Offer.created_at.asc())
            .first()
        )
        earned_at = first_offer.created_at if first_offer else None
    
    return BadgeSchema(
        type=BadgeType.OFERTANTE,
        name=BADGE_DEFINITIONS[BadgeType.OFERTANTE]["name"],
        description=BADGE_DEFINITIONS[BadgeType.OFERTANTE]["description"],
        icon=BADGE_DEFINITIONS[BadgeType.OFERTANTE]["icon"],
        is_earned=offer_count >= 1,
        earned_at=earned_at,
    )


def _create_empty_badges() -> list[BadgeSchema]:
    """Create empty badge list when user has no contacts."""
    badges = []
    for badge_type in BadgeType:
        definition = BADGE_DEFINITIONS[badge_type]
        badges.append(BadgeSchema(
            type=badge_type,
            name=definition["name"],
            description=definition["description"],
            icon=definition["icon"],
            is_earned=False,
            earned_at=None,
        ))
    return badges
