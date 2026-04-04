"""Reviews router — CRUD, moderation, verification levels."""
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from app.rate_limit import limiter
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from PIL import Image

from app.database import get_db
from app.models.review import Review
from app.models.contact import Contact, ContactHistory
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewReplyCreate, ReviewResponse, ReviewListResponse, VerifyLevelRequest
from app.auth import get_current_user
from app.routes.contacts import get_current_user_optional

router = APIRouter(tags=["reviews"])

# Image settings for review photos
REVIEW_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "images"
REVIEW_MAX_IMAGE_SIZE = (800, 800)
REVIEW_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


def recalculate_rating(db: Session, contact_id: int):
    """Recalculate avg_rating and review_count for a contact."""
    approved = db.query(Review).filter(
        Review.contact_id == contact_id,
        Review.is_approved == True,
    ).all()

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact:
        if approved:
            contact.avg_rating = round(sum(r.rating for r in approved) / len(approved), 1)
        else:
            contact.avg_rating = 0
        contact.review_count = len(approved)


def review_to_response(review: Review) -> dict:
    """Convert Review model to response dict with username."""
    data = {
        "id": review.id,
        "contact_id": review.contact_id,
        "user_id": review.user_id,
        "rating": review.rating,
        "comment": review.comment,
        "photo_path": review.photo_path,
        "is_approved": review.is_approved,
        "approved_by": review.approved_by,
        "approved_at": review.approved_at,
        "created_at": review.created_at,
        "username": None,
    }
    # Lazy load user to get username
    if review.user_id:
        # We'll fetch this in the endpoint
        pass
    return data


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get("/api/contacts/{contact_id}/reviews", response_model=ReviewListResponse)
def list_reviews(
    contact_id: int,
    skip: int = 0,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """List approved reviews for a contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    query = db.query(Review).filter(
        Review.contact_id == contact_id,
        Review.is_approved == True,
    ).order_by(Review.created_at.desc())

    total = query.count()
    reviews = query.offset(skip).limit(limit).all()

    # Enrich with username and reply info — batch fetch to avoid N+1
    user_ids = {r.user_id for r in reviews} | {r.reply_by for r in reviews if r.reply_by}
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    result = []
    for r in reviews:
        user = users_map.get(r.user_id)
        reply_user = users_map.get(r.reply_by) if r.reply_by else None
        data = ReviewResponse(
            id=r.id,
            contact_id=r.contact_id,
            user_id=r.user_id,
            rating=r.rating,
            comment=r.comment,
            photo_path=r.photo_path,
            is_approved=r.is_approved,
            approved_by=r.approved_by,
            approved_at=r.approved_at,
            created_at=r.created_at,
            username=user.username if user else "Usuario",
            reply_text=r.reply_text,
            reply_at=r.reply_at,
            reply_by_username=reply_user.username if reply_user else None,
        )
        result.append(data)

    return ReviewListResponse(
        reviews=result,
        total=total,
        avg_rating=contact.avg_rating,
    )


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------

@router.post("/api/contacts/{contact_id}/reviews", response_model=ReviewResponse, status_code=201)
@limiter.limit("5/hour")
def create_review(
    contact_id: int,
    data: ReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a review for a contact. One review per user per contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    # Can't review yourself
    if contact.user_id == user.id:
        raise HTTPException(status_code=400, detail="No puedes reseñar tu propio contacto")

    # Check for existing review
    existing = db.query(Review).filter(
        Review.contact_id == contact_id,
        Review.user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya has reseñado este contacto")

    review = Review(
        contact_id=contact_id,
        user_id=user.id,
        rating=data.rating,
        comment=data.comment,
        is_approved=False,  # Requires moderation
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return ReviewResponse(
        id=review.id,
        contact_id=review.contact_id,
        user_id=review.user_id,
        rating=review.rating,
        comment=review.comment,
        photo_path=review.photo_path,
        is_approved=review.is_approved,
        approved_by=review.approved_by,
        approved_at=review.approved_at,
        created_at=review.created_at,
        username=user.username,
    )


@router.post("/api/reviews/{review_id}/photo", response_model=ReviewResponse)
def upload_review_photo(
    review_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a photo for a review (only by the review author)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    if review.user_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el autor puede subir fotos")

    # Validate JPEG
    if not file.filename.lower().endswith(('.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos JPG")

    content = file.file.read()
    if len(content) > REVIEW_MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="El archivo es demasiado grande (máximo 2MB)")

    JPEG_MAGIC = b'\xFF\xD8\xFF'
    if not content.startswith(JPEG_MAGIC):
        raise HTTPException(status_code=400, detail="El archivo no es un JPEG válido")

    file.file.seek(0)
    REVIEW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"review_{review_id}.jpg"
    filepath = REVIEW_UPLOAD_DIR / filename

    try:
        image = Image.open(file.file)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        if image.width > REVIEW_MAX_IMAGE_SIZE[0] or image.height > REVIEW_MAX_IMAGE_SIZE[1]:
            image.thumbnail(REVIEW_MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        image.save(filepath, 'JPEG', quality=85)
        review.photo_path = f"/uploads/images/{filename}"
        db.commit()
        db.refresh(review)
    except Exception as e:
        logging.error(f"Error uploading review photo: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar la imagen")

    user_obj = db.query(User).filter(User.id == review.user_id).first()
    return ReviewResponse(
        id=review.id, contact_id=review.contact_id, user_id=review.user_id,
        rating=review.rating, comment=review.comment, photo_path=review.photo_path,
        is_approved=review.is_approved, created_at=review.created_at,
        username=user_obj.username if user_obj else "Usuario",
    )


# ---------------------------------------------------------------------------
# Reply endpoint (contact owner only)
# ---------------------------------------------------------------------------

@router.post("/api/reviews/{review_id}/reply", response_model=ReviewResponse)
def reply_to_review(
    review_id: int,
    data: ReviewReplyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reply to a review (only the contact owner can reply)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    # Only contact owner can reply
    contact = db.query(Contact).filter(Contact.id == review.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if contact.user_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el propietario del contacto puede responder")

    review.reply_text = data.reply_text
    review.reply_at = datetime.now(timezone.utc)
    review.reply_by = user.id
    db.commit()
    db.refresh(review)

    reviewer = db.query(User).filter(User.id == review.user_id).first()
    return ReviewResponse(
        id=review.id, contact_id=review.contact_id, user_id=review.user_id,
        rating=review.rating, comment=review.comment, photo_path=review.photo_path,
        is_approved=review.is_approved, approved_by=review.approved_by,
        approved_at=review.approved_at, created_at=review.created_at,
        username=reviewer.username if reviewer else "Usuario",
        reply_text=review.reply_text,
        reply_at=review.reply_at,
        reply_by_username=user.username,
    )


# ---------------------------------------------------------------------------
# Admin/Moderator endpoints
# ---------------------------------------------------------------------------

@router.get("/api/admin/reviews/pending")
def list_pending_reviews(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List reviews pending moderation (mod/admin only)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    query = db.query(Review).filter(Review.is_approved == False).order_by(Review.created_at.desc())
    total = query.count()
    reviews = query.offset(skip).limit(limit).all()

    result = []
    for r in reviews:
        reviewer = db.query(User).filter(User.id == r.user_id).first()
        contact = db.query(Contact).filter(Contact.id == r.contact_id).first()
        result.append({
            "id": r.id,
            "contact_id": r.contact_id,
            "contact_name": contact.name if contact else "Desconocido",
            "user_id": r.user_id,
            "username": reviewer.username if reviewer else "Usuario",
            "rating": r.rating,
            "comment": r.comment,
            "photo_path": r.photo_path,
            "created_at": r.created_at,
        })

    return {"reviews": result, "total": total}


@router.post("/api/admin/reviews/{review_id}/approve", response_model=ReviewResponse)
def approve_review(
    review_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Approve a review (mod/admin only). Recalculates contact rating."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    if review.is_approved:
        raise HTTPException(status_code=400, detail="La reseña ya está aprobada")

    review.is_approved = True
    review.approved_by = user.id
    review.approved_at = datetime.now(timezone.utc)

    recalculate_rating(db, review.contact_id)
    db.commit()
    db.refresh(review)

    reviewer = db.query(User).filter(User.id == review.user_id).first()
    return ReviewResponse(
        id=review.id, contact_id=review.contact_id, user_id=review.user_id,
        rating=review.rating, comment=review.comment, photo_path=review.photo_path,
        is_approved=review.is_approved, approved_by=review.approved_by,
        approved_at=review.approved_at, created_at=review.created_at,
        username=reviewer.username if reviewer else "Usuario",
    )


@router.post("/api/admin/reviews/{review_id}/reject", response_model=ReviewResponse)
def reject_review(
    review_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject a review (mod/admin only). Deletes the review so user can submit a new one."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    was_approved = review.is_approved
    contact_id = review.contact_id

    # Delete the review entirely so the user can submit a new one
    db.delete(review)
    db.commit()

    # Recalculate rating if it was approved (had impact on average)
    if was_approved:
        recalculate_rating(db, contact_id)
        db.commit()

    return ReviewResponse(
        id=review_id, contact_id=contact_id, user_id=review.user_id,
        rating=review.rating, comment=review.comment, photo_path=review.photo_path,
        is_approved=False, created_at=review.created_at,
        username="Usuario",
    )


# ---------------------------------------------------------------------------
# Verification level endpoint (in reviews router for convenience)
# ---------------------------------------------------------------------------

@router.put("/api/admin/contacts/{contact_id}/verification")
def set_verification_level(
    contact_id: int,
    data: VerifyLevelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set verification level for a contact (mod/admin only)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    old_level = contact.verification_level
    contact.verification_level = data.verification_level

    # Sync legacy field
    contact.is_verified = data.verification_level >= 1
    if data.verification_level >= 1 and not contact.verified_by:
        contact.verified_by = user.id
        contact.verified_at = datetime.now(timezone.utc)
    elif data.verification_level == 0:
        contact.verified_by = None
        contact.verified_at = None

    # Log to history
    from app.routes.contacts import save_history
    save_history(db, contact_id, user.id, "verification_level", str(old_level), str(data.verification_level))

    db.commit()
    db.refresh(contact)

    return {
        "id": contact.id,
        "name": contact.name,
        "verification_level": contact.verification_level,
        "is_verified": contact.is_verified,
    }
