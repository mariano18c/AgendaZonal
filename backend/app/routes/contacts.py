import os
import logging
import jwt
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Header
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
)
from app.config import JWT_SECRET, JWT_ALGORITHM
from app.auth import get_current_user

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

# Fields to track in history
TRACKED_FIELDS = [
    "name", "phone", "email", "address", "city", "neighborhood",
    "category_id", "description", "schedule", "website", "photo_path",
    "latitude", "longitude", "maps_url",
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
    """Get current user or None if not authenticated"""
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = int(user_id_str)
    except Exception:
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


@router.get("", response_model=list[ContactResponse])
def list_contacts(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Contact)
    if category_id is not None:
        query = query.filter(Contact.category_id == category_id)
    return query.offset(skip).limit(limit).all()


@router.get("/search", response_model=list[ContactResponse])
def search_contacts(
    q: str | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Contact)

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
            )
        )

    if category_id is not None:
        query = query.filter(Contact.category_id == category_id)

    if not q and category_id is None:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'q' o 'category_id'")

    return query.all()


@router.get("/pending", response_model=list[ContactResponse])
def list_pending_contacts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List contacts with pending changes (only for users with permission)"""
    # Get contacts owned by user or if user is moderator/admin
    if user.role in ['moderator', 'admin']:
        contacts = db.query(Contact).filter(Contact.pending_changes_count > 0).all()
    else:
        contacts = db.query(Contact).filter(
            Contact.user_id == user.id,
            Contact.pending_changes_count > 0
        ).all()
    
    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contact


@router.get("/{contact_id}/history", response_model=list[ContactHistoryResponse])
def get_contact_history(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the change history for a contact (requires authentication)"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    return (
        db.query(ContactHistory)
        .filter(ContactHistory.contact_id == contact_id)
        .order_by(ContactHistory.changed_at.desc())
        .all()
    )


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
def create_contact(
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
    else:
        contact.verified_by = None
        contact.verified_at = None

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    if contact.user_id != user.id and user.role not in ['admin', 'moderator']:
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
