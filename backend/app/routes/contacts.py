import os
import logging
import jwt
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from PIL import Image
from app.database import get_db
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange
from app.models.user import User
from app.schemas.contact import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactHistoryResponse,
    ContactChangeCreate,
    ContactChangeResponse,
    VerifyContactRequest,
    TransferOwnershipRequest,
    ScheduleEntry,
)
from app.config import JWT_SECRET, JWT_ALGORITHM
from app.auth import get_current_user
from app.geo import bounding_box, haversine_km, validate_coordinates
from app.rate_limit import limiter

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

# Fields to track in history
TRACKED_FIELDS = [
    "name", "phone", "email", "address", "city", "neighborhood",
    "category_id", "description", "schedule", "website", "photo_path",
    "latitude", "longitude", "maps_url", "instagram", "facebook", "about",
]

# S-07: Protected fields that cannot be updated directly
PROTECTED_FIELDS = [
    "id", "user_id", "is_verified", "verified_by", "verified_at",
    "pending_changes_count", "created_at", "updated_at",
]

# Image upload settings
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "images"
MAX_IMAGE_SIZE = (1024, 1024)

# Maximum pending changes per contact
MAX_PENDING_CHANGES = 3


def escape_like(value: str) -> str:
    """Escape special LIKE characters to prevent wildcard injection"""
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def save_history(db: Session, contact_id: int, user_id: int, field_name: str, old_value, new_value):
    """Save a change to the history table"""
    if str(old_value) != str(new_value):
        history = ContactHistory(
            contact_id=contact_id,
            user_id=user_id,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
        )
        db.add(history)


def resize_image(image: Image.Image, max_size: tuple) -> Image.Image:
    """Resize image while maintaining aspect ratio"""
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image


def get_current_user_optional(
    authorization: str = Header(None), db: Session = Depends(get_db)
) -> User | None:
    """Get current user or None if not authenticated.
    
    Logs invalid tokens for audit purposes instead of silently ignoring them.
    """
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            logging.debug("Optional auth: token missing 'sub' claim")
            return None
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError:
        logging.debug("Optional auth: token expired")
        return None
    except jwt.InvalidTokenError:
        logging.debug("Optional auth: invalid token")
        return None
    except (ValueError, AttributeError):
        logging.debug("Optional auth: malformed authorization header")
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    return user


def can_edit_field(user, contact, field_name, current_value):
    """
    Determine if user can edit a field
    
    Returns: (can_edit, needs_verification)
    """
    # No user (not logged in)
    if not user:
        if current_value is None or current_value == "":
            return True, True
        return False, False
    
    # Owner of contact
    if user.id == contact.user_id:
        return True, False
    
    # Moderator or admin
    if user.role in ['moderator', 'admin']:
        return True, False
    
    # Registered user but not owner
    if current_value is None or current_value == "":
        return True, True
    
    return False, False


def can_verify_change(user, contact):
    """Determine if user can verify changes"""
    if not user:
        return False
    
    if user.id == contact.user_id:
        return True
    
    if user.role in ['moderator', 'admin']:
        return True
    
    return False


@router.get("")
def list_contacts(
    skip: int = 0,
    limit: int = Query(default=20, le=100),
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Contact).filter(Contact.status != "suspended")
    if category_id is not None:
        query = query.filter(Contact.category_id == category_id)
    
    total = query.count()
    contacts = query.offset(skip).limit(limit).all()
    
    return {"contacts": contacts, "total": total}


@router.get("/search")
@limiter.limit("30/minute")
def search_contacts(
    request: Request,
    q: str | None = None,
    category_id: int | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = Query(default=10, ge=1, le=100),
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    """Search contacts with optional geo filtering.

    If lat+lon provided: filters by radius, sorts by distance, includes distance_km.
    If only q/category_id: standard text search (backward compatible).
    Can combine geo + text + category filters.
    """
    query = db.query(Contact).filter(Contact.status != "suspended")

    # Text search
    if q:
        safe_q = escape_like(q)
        search = f"%{safe_q}%"
        query = query.filter(
            or_(
                Contact.name.ilike(search),
                Contact.city.ilike(search),
                Contact.neighborhood.ilike(search),
                Contact.description.ilike(search),
                Contact.schedule.ilike(search),
                Contact.phone.ilike(search),
            )
        )

    # Category filter
    if category_id is not None:
        query = query.filter(Contact.category_id == category_id)

    # Geo filtering
    use_geo = lat is not None and lon is not None
    if use_geo:
        if not validate_coordinates(lat, lon):
            raise HTTPException(status_code=400, detail="Coordenadas inválidas")

        # Bounding box pre-filter (fast, uses numeric comparison)
        bbox = bounding_box(lat, lon, radius_km)
        query = query.filter(
            Contact.latitude.isnot(None),
            Contact.longitude.isnot(None),
            Contact.latitude >= bbox.lat_min,
            Contact.latitude <= bbox.lat_max,
            Contact.longitude >= bbox.lon_min,
            Contact.longitude <= bbox.lon_max,
        )

    # Require at least one filter (same as before)
    if not q and category_id is None and not use_geo:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar 'q', 'category_id', o coordenadas (lat+lon)"
        )

    # Get total count before pagination
    total = query.count()

    # For geo search, fetch more from DB since bounding box is larger than circle.
    # The user-specified limit is applied AFTER distance filtering.
    if use_geo:
        db_limit = min(limit * 5, 2500)  # Fetch up to 5x requested, max 2500
        results = query.offset(skip).limit(db_limit).all()
    else:
        results = query.offset(skip).limit(limit).all()

    # If geo search, calculate precise distances, sort, then apply limit
    if use_geo:
        results_with_distance = []
        for contact in results:
            if contact.latitude is not None and contact.longitude is not None:
                dist = haversine_km(lat, lon, contact.latitude, contact.longitude)
                if dist <= radius_km:
                    # Attach distance dynamically (not stored in DB)
                    contact.distance_km = round(dist, 1)
                    results_with_distance.append(contact)
        # Sort by distance
        results_with_distance.sort(key=lambda c: c.distance_km)
        # Apply user-specified limit AFTER distance filtering
        return {"contacts": results_with_distance[:limit], "total": len(results_with_distance)}

    return {"contacts": results, "total": total}


@router.get("/export")
@limiter.limit("5/minute")
def export_contacts(
    request: Request,
    format: str = Query("csv", pattern="^(csv|json)$"),
    category_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export contacts as CSV or JSON."""
    query = db.query(Contact)
    if category_id is not None:
        query = query.filter(Contact.category_id == category_id)
    contacts = query.all()

    if format == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=[ContactResponse.model_validate(c).model_dump(mode="json") for c in contacts],
            headers={"Content-Disposition": "attachment; filename=contactos.json"},
        )

    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "phone", "email", "address", "city", "neighborhood",
                     "category_id", "description", "schedule", "website"])
    for c in contacts:
        writer.writerow([c.name, c.phone, c.email, c.address, c.city, c.neighborhood,
                         c.category_id, c.description, c.schedule, c.website])
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contactos.csv"},
    )


@router.get("/pending")
def list_pending_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List contacts with pending changes (only for users with permission)"""
    # Get contacts owned by user or if user is moderator/admin
    if user.role in ['moderator', 'admin']:
        query = db.query(Contact).filter(Contact.pending_changes_count > 0)
    else:
        query = db.query(Contact).filter(
            Contact.user_id == user.id,
            Contact.pending_changes_count > 0
        )

    total = query.count()
    contacts = query.order_by(Contact.updated_at.desc()).offset(skip).limit(limit).all()

    return {
        "contacts": contacts,
        "total": total,
    }


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contact


@router.get("/{contact_id}/history")
def get_contact_history(
    contact_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the change history for a contact (requires authentication)"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    query = db.query(ContactHistory).filter(ContactHistory.contact_id == contact_id)
    total = query.count()
    history = query.order_by(ContactHistory.changed_at.desc()).offset(skip).limit(limit).all()

    return {
        "history": history,
        "total": total,
    }


@router.get("/{contact_id}/changes", response_model=list[ContactChangeResponse])
def get_contact_changes(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get pending changes for a contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    # Check permission
    if not can_verify_change(user, contact):
        raise HTTPException(status_code=403, detail="No tiene permisos para ver los cambios")
    
    return (
        db.query(ContactChange)
        .filter(ContactChange.contact_id == contact_id, ContactChange.is_verified == False)
        .order_by(ContactChange.created_at.desc())
        .all()
    )


@router.post("", response_model=ContactResponse, status_code=201)
@limiter.limit("10/minute")
def create_contact(
    request: Request,
    data: ContactCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact = Contact(**data.model_dump(), user_id=user.id)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/{contact_id}/edit", response_model=ContactResponse)
def edit_contact(
    contact_id: int,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Edit a contact with permission checks and pending changes"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    update_data = data.model_dump(exclude_unset=True)
    direct_updates = {}
    pending_changes = []
    
    for field_name, new_value in update_data.items():
        if field_name not in TRACKED_FIELDS:
            continue
            
        current_value = getattr(contact, field_name)
        can_edit, needs_verification = can_edit_field(current_user, contact, field_name, current_value)
        
        if not can_edit:
            raise HTTPException(
                status_code=403, 
                detail=f"No tiene permisos para editar el campo '{field_name}'"
            )
        
        if str(current_value) != str(new_value):
            if needs_verification:
                # Check if max pending changes reached
                if contact.pending_changes_count >= MAX_PENDING_CHANGES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El contacto ya tiene el máximo de {MAX_PENDING_CHANGES} cambios pendientes"
                    )
                pending_changes.append((field_name, current_value, new_value))
            else:
                direct_updates[field_name] = new_value
    
    # Apply direct updates (no verification needed)
    for field_name, new_value in direct_updates.items():
        old_value = getattr(contact, field_name)
        save_history(db, contact_id, current_user.id if current_user else None, field_name, old_value, new_value)
        setattr(contact, field_name, new_value)
    
    # Create pending changes
    for field_name, old_value, new_value in pending_changes:
        change = ContactChange(
            contact_id=contact_id,
            user_id=current_user.id if current_user else None,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value),
        )
        db.add(change)
        contact.pending_changes_count += 1
    
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Direct update (owner/moderator/admin only)"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    # Check permission
    if not can_verify_change(user, contact):
        raise HTTPException(status_code=403, detail="No tiene permisos para editar este contacto")

    update_data = data.model_dump(exclude_unset=True)
    
    # S-07: Exclude protected fields
    for protected in PROTECTED_FIELDS:
        update_data.pop(protected, None)
    
    # Track changes in history
    for key, new_value in update_data.items():
        if key in TRACKED_FIELDS:
            old_value = getattr(contact, key)
            save_history(db, contact_id, user.id, key, old_value, new_value)
        setattr(contact, key, new_value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}/changes/{change_id}")
def delete_contact_change(
    contact_id: int,
    change_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a pending change (only by the user who created it)"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    change = db.query(ContactChange).filter(
        ContactChange.id == change_id,
        ContactChange.contact_id == contact_id,
        ContactChange.is_verified == False
    ).first()
    
    if not change:
        raise HTTPException(status_code=404, detail="Cambio no encontrado")
    
    # Only the user who created the change can delete it
    if change.user_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el usuario que sugirió el cambio puede eliminarlo")
    
    db.delete(change)
    contact.pending_changes_count = max(0, contact.pending_changes_count - 1)
    db.commit()
    
    return {"message": "Cambio eliminado"}


@router.post("/{contact_id}/changes/{change_id}/verify", response_model=ContactChangeResponse)
def verify_change(
    contact_id: int,
    change_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verify a pending change"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    if not can_verify_change(user, contact):
        raise HTTPException(status_code=403, detail="No tiene permisos para verificar cambios")
    
    change = db.query(ContactChange).filter(
        ContactChange.id == change_id,
        ContactChange.contact_id == contact_id,
        ContactChange.is_verified == False
    ).first()
    
    if not change:
        raise HTTPException(status_code=404, detail="Cambio no encontrado")
    
    # Apply the change
    field_name = change.field_name
    old_value = getattr(contact, field_name)
    new_value = change.new_value

    # Convert type if needed
    try:
        if field_name in ['latitude', 'longitude'] and new_value:
            new_value = float(new_value)
        elif field_name == 'category_id' and new_value:
            new_value = int(new_value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Valor invalido para el campo '{field_name}'")

    setattr(contact, field_name, new_value)
    
    # Save to history
    save_history(db, contact_id, change.user_id, field_name, old_value, new_value)
    
    # Mark change as verified
    change.is_verified = True
    change.verified_by = user.id
    change.verified_at = datetime.now(timezone.utc)
    
    # Decrement pending count
    contact.pending_changes_count = max(0, contact.pending_changes_count - 1)
    
    db.commit()
    db.refresh(change)
    return change


@router.post("/{contact_id}/changes/{change_id}/reject", response_model=ContactChangeResponse)
def reject_change(
    contact_id: int,
    change_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject a pending change"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    if not can_verify_change(user, contact):
        raise HTTPException(status_code=403, detail="No tiene permisos para rechazar cambios")
    
    change = db.query(ContactChange).filter(
        ContactChange.id == change_id,
        ContactChange.contact_id == contact_id,
        ContactChange.is_verified == False
    ).first()
    
    if not change:
        raise HTTPException(status_code=404, detail="Cambio no encontrado")
    
    # Mark as rejected (verified=True but not applied)
    change.is_verified = True
    change.verified_by = user.id
    change.verified_at = datetime.now(timezone.utc)
    
    # Decrement pending count
    contact.pending_changes_count = max(0, contact.pending_changes_count - 1)
    
    db.commit()
    db.refresh(change)
    return change


@router.post("/{contact_id}/image", response_model=ContactResponse)
def upload_contact_image(
    contact_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload an image for a contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    # Validate file type (extension)
    if not file.filename.lower().endswith(('.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos JPG")

    # Read file content for validation
    content = file.file.read()
    
    # Validate file size (max 5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="El archivo es demasiado grande (máximo 5MB)")
    
    # Validate JPEG magic bytes (S-05 fix)
    JPEG_MAGIC = b'\xFF\xD8\xFF'
    if not content.startswith(JPEG_MAGIC):
        raise HTTPException(status_code=400, detail="El archivo no es un JPEG válido")
    
    # Reset file pointer
    file.file.seek(0)

    # Create upload directory if it doesn't exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = f"contact_{contact_id}.jpg"
    filepath = UPLOAD_DIR / filename

    # Save and process image
    try:
        # Read image
        image = Image.open(file.file)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if necessary
        if image.width > MAX_IMAGE_SIZE[0] or image.height > MAX_IMAGE_SIZE[1]:
            image = resize_image(image, MAX_IMAGE_SIZE)
        
        # Save image
        image.save(filepath, 'JPEG', quality=85)
        
        # Update contact
        old_photo = contact.photo_path
        contact.photo_path = f"/uploads/images/{filename}"
        
        # Save history
        save_history(db, contact_id, user.id, "photo_path", old_photo, contact.photo_path)
        
        db.commit()
        db.refresh(contact)
        return contact
        
    except Exception as e:
        logging.error(f"Error uploading image for contact {contact_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al procesar la imagen")


@router.delete("/{contact_id}/image", response_model=ContactResponse)
def delete_contact_image(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete the image for a contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    if not contact.photo_path:
        raise HTTPException(status_code=404, detail="El contacto no tiene imagen")

    # Delete file
    filename = f"contact_{contact_id}.jpg"
    filepath = UPLOAD_DIR / filename
    if filepath.exists():
        os.remove(filepath)

    # Update contact
    old_photo = contact.photo_path
    contact.photo_path = None
    
    # Save history
    save_history(db, contact_id, user.id, "photo_path", old_photo, None)
    
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{contact_id}/verify", response_model=ContactResponse)
def verify_contact(
    contact_id: int,
    data: VerifyContactRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verify/unverify a contact (requires owner, moderator, or admin role)"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    # S-05: Check authorization
    if not can_verify_change(user, contact):
        raise HTTPException(status_code=403, detail="No tiene permisos para verificar este contacto")

    contact.is_verified = data.is_verified
    if data.is_verified:
        contact.verified_by = user.id
        contact.verified_at = datetime.now(timezone.utc)
        contact.verification_level = max(contact.verification_level, 1)  # Al menos nivel 1
    else:
        contact.verified_by = None
        contact.verified_at = None
        contact.verification_level = 0

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a contact. Owner can only delete if flagged for deletion. Admins can delete any contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    # Admin/moderator can delete any contact
    is_admin = user.role in ['admin', 'moderator']
    
    # Owner can only delete if flagged for deletion
    is_owner = contact.user_id == user.id
    
    if is_owner and not is_admin:
        # Owner trying to delete - only allowed if flagged
        if contact.status != 'flagged':
            raise HTTPException(
                status_code=403, 
                detail="Para eliminar un contacto, primero debe solicitar la eliminación desde la página del contacto"
            )
    
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="No tiene permisos para eliminar este contacto")

    # Delete image if exists
    if contact.photo_path:
        filename = f"contact_{contact_id}.jpg"
        filepath = UPLOAD_DIR / filename
        if filepath.exists():
            os.remove(filepath)

    # Delete pending changes
    db.query(ContactChange).filter(ContactChange.contact_id == contact_id).delete()

    # Delete history records (B-07 fix)
    db.query(ContactHistory).filter(ContactHistory.contact_id == contact_id).delete()

    db.delete(contact)
    db.commit()
    return None


@router.post("/{contact_id}/request-deletion", response_model=ContactResponse)
def request_deletion(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Request deletion of own contact. Marks it as flagged for admin review."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    if contact.user_id != user.id:
        raise HTTPException(status_code=403, detail="Solo puede solicitar eliminación de sus propios contactos")
    
    if contact.status == 'flagged':
        raise HTTPException(status_code=400, detail="Este contacto ya está marcado para eliminación")
    
    contact.status = 'flagged'
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{contact_id}/cancel-deletion", response_model=ContactResponse)
def cancel_deletion(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cancel deletion request. Owner or admin can cancel."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    is_admin = user.role in ['admin', 'moderator']
    
    if contact.user_id != user.id and not is_admin:
        raise HTTPException(status_code=403, detail="No tiene permisos para cancelar la eliminación")
    
    if contact.status != 'flagged':
        raise HTTPException(status_code=400, detail="Este contacto no está marcado para eliminación")
    
    contact.status = 'active'
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/{contact_id}/transfer-ownership", response_model=ContactResponse)
def transfer_ownership(
    contact_id: int,
    data: TransferOwnershipRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Transfer ownership of a contact to another user (admin only).
    
    Body: { "new_owner_id": 123 }
    """
    if user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Solo administradores pueden transferir propiedad")
    
    new_owner_id = data.new_owner_id
    
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    new_owner = db.query(User).filter(User.id == new_owner_id).first()
    if not new_owner:
        raise HTTPException(status_code=404, detail="Usuario nuevo propietario no encontrado")
    
    old_owner_id = contact.user_id
    contact.user_id = new_owner_id
    
    # If flagged for deletion, reset status when transferring
    if contact.status == 'flagged':
        contact.status = 'active'
    
    # Save history
    save_history(db, contact_id, user.id, "user_id", old_owner_id, new_owner_id)
    
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{contact_id}/leads", status_code=201)
def register_lead(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """Register a lead event (WhatsApp click, phone call, etc)."""
    from app.models.lead_event import LeadEvent

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    lead = LeadEvent(
        contact_id=contact_id,
        user_id=user.id if user else None,
        source="whatsapp",
    )
    db.add(lead)
    db.commit()
    return {"message": "Lead registrado"}


@router.get("/{contact_id}/leads")
def get_contact_leads(
    contact_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get leads for a contact (owner only)."""
    from app.models.lead_event import LeadEvent
    from datetime import timedelta

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    if contact.user_id != user.id and user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="No tiene permisos para ver los leads")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    leads = (
        db.query(LeadEvent)
        .filter(LeadEvent.contact_id == contact_id, LeadEvent.created_at >= since)
        .all()
    )

    return {
        "total": len(leads),
        "period_days": days,
        "by_source": {"whatsapp": sum(1 for l in leads if l.source == "whatsapp")},
    }


# ---------------------------------------------------------------------------
# V3: Search by phone, related businesses, photos, schedules, friendly URLs
# ---------------------------------------------------------------------------

@router.get("/search/phone")
def search_by_phone(
    phone: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
):
    """Search contacts by phone number (partial match)."""
    safe_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    # Escape LIKE wildcards to prevent wildcard injection
    safe_phone = safe_phone.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    contacts = db.query(Contact).filter(
        Contact.status != "suspended",
        Contact.phone.contains(safe_phone, escape='\\'),
    ).limit(20).all()
    return contacts


@router.get("/{contact_id}/related")
def get_related_businesses(
    contact_id: int,
    radius_km: float = Query(default=10, ge=1, le=50),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Get related businesses: same category, within radius, excluding self."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    if not contact.latitude or not contact.longitude or not contact.category_id:
        return []

    bbox = bounding_box(contact.latitude, contact.longitude, radius_km)
    candidates = db.query(Contact).filter(
        Contact.id != contact_id,
        Contact.status == "active",
        Contact.category_id == contact.category_id,
        Contact.latitude.isnot(None),
        Contact.longitude.isnot(None),
        Contact.latitude >= bbox.lat_min,
        Contact.latitude <= bbox.lat_max,
        Contact.longitude >= bbox.lon_min,
        Contact.longitude <= bbox.lon_max,
    ).limit(20).all()

    # Precise distance filter
    results = []
    for c in candidates:
        dist = haversine_km(contact.latitude, contact.longitude, c.latitude, c.longitude)
        if dist <= radius_km:
            c.distance_km = round(dist, 1)
            results.append(c)

    results.sort(key=lambda c: c.distance_km)
    return results[:limit]


@router.get("/{contact_id}/photos")
def list_photos(
    contact_id: int,
    db: Session = Depends(get_db),
):
    """List photos for a contact."""
    from app.models.contact_photo import ContactPhoto

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    photos = (
        db.query(ContactPhoto)
        .filter(ContactPhoto.contact_id == contact_id)
        .order_by(ContactPhoto.sort_order)
        .all()
    )
    return [{"id": p.id, "photo_path": p.photo_path, "caption": p.caption, "sort_order": p.sort_order} for p in photos]


@router.post("/{contact_id}/photos", status_code=201)
def upload_photo(
    contact_id: int,
    file: UploadFile = File(...),
    caption: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a photo for a contact (owner only, max 5)."""
    from app.models.contact_photo import ContactPhoto

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if contact.user_id != user.id and user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="No tiene permisos")

    # Check max photos
    count = db.query(ContactPhoto).filter(ContactPhoto.contact_id == contact_id).count()
    if count >= 5:
        raise HTTPException(status_code=400, detail="Máximo 5 fotos por contacto")

    # Validate JPEG
    if not file.filename.lower().endswith(('.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Solo JPG")
    content = file.file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Máximo 2MB")
    JPEG_MAGIC = b'\xFF\xD8\xFF'
    if not content.startswith(JPEG_MAGIC):
        raise HTTPException(status_code=400, detail="JPEG inválido")

    file.file.seek(0)
    UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "images"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"contact_{contact_id}_photo_{count + 1}.jpg"
    filepath = UPLOAD_DIR / filename
    try:
        image = Image.open(file.file)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        if image.width > 1200 or image.height > 1200:
            image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        image.save(filepath, 'JPEG', quality=85)
    except Exception as e:
        logging.error(f"Error uploading photo: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar imagen")

    photo = ContactPhoto(
        contact_id=contact_id,
        photo_path=f"/uploads/images/{filename}",
        caption=caption,
        sort_order=count + 1,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return {"id": photo.id, "photo_path": photo.photo_path, "caption": photo.caption}


@router.delete("/{contact_id}/photos/{photo_id}", status_code=204)
def delete_photo(
    contact_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a photo (owner only)."""
    from app.models.contact_photo import ContactPhoto

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404)
    if contact.user_id != user.id and user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403)

    photo = db.query(ContactPhoto).filter(
        ContactPhoto.id == photo_id,
        ContactPhoto.contact_id == contact_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    # Delete file
    try:
        full_path = Path(__file__).resolve().parent.parent.parent / photo.photo_path.lstrip("/")
        if full_path.exists():
            full_path.unlink()
    except:
        pass

    db.delete(photo)
    db.commit()
    return None


@router.get("/{contact_id}/schedules")
def list_schedules(
    contact_id: int,
    db: Session = Depends(get_db),
):
    """Get structured schedule for a contact."""
    from app.models.schedule import Schedule

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    schedules = (
        db.query(Schedule)
        .filter(Schedule.contact_id == contact_id)
        .order_by(Schedule.day_of_week)
        .all()
    )

    DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    result = []
    for s in schedules:
        result.append({
            "id": s.id,
            "day_of_week": s.day_of_week,
            "day_name": DAY_NAMES[s.day_of_week] if 0 <= s.day_of_week <= 6 else "?",
            "open_time": s.open_time,
            "close_time": s.close_time,
            "is_closed": s.open_time is None,
        })
    return result


@router.put("/{contact_id}/schedules")
def update_schedules(
    contact_id: int,
    schedules: list[ScheduleEntry],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update full week schedule for a contact (owner only).

    Body: [{"day_of_week": 0, "open_time": "08:00", "close_time": "18:00"}, ...]
    Use null open_time to mark a day as closed.
    """
    from app.models.schedule import Schedule

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404)
    if contact.user_id != user.id and user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403)

    # Delete existing
    db.query(Schedule).filter(Schedule.contact_id == contact_id).delete()

    # Insert new
    for s in schedules:
        schedule = Schedule(
            contact_id=contact_id,
            day_of_week=s.day_of_week,
            open_time=s.open_time,
            close_time=s.close_time,
        )
        db.add(schedule)

    db.commit()
    return {"message": "Horarios actualizados"}
