from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import bcrypt
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserRoleUpdate, PasswordReset
from app.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role"""
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol de administrador.")
    return user


@router.get("/active")
def list_active_users_simple(
    db: Session = Depends(get_db),
):
    """List active users (public, for dropdowns). Returns only id and username."""
    users = db.query(User.id, User.username).filter(User.is_active == True).order_by(User.username).all()
    return [{"id": u.id, "username": u.username} for u in users]


@router.get("", response_model=list[UserResponse])
def list_users(
    filter: str = Query("all", description="Filter: all, active, inactive"),
    role: str | None = Query(None, description="Filter by role: user, moderator, admin"),
    username: str | None = Query(None, description="Filter by username (partial match)"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all users (admin only)"""
    query = db.query(User)
    if filter == "active":
        query = query.filter(User.is_active == True)
    elif filter == "inactive":
        query = query.filter(User.is_active == False)
    if role:
        query = query.filter(User.role == role)
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))
    return query.order_by(User.created_at.desc()).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get a specific user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update user data (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Validate role if provided
    if 'role' in update_data and update_data['role']:
        valid_roles = ['user', 'moderator', 'admin']
        if update_data['role'] not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Rol inválido. Valores permitidos: {', '.join(valid_roles)}")
        
        # Cannot change role of admin users
        if user.role == 'admin' and update_data['role'] != 'admin':
            raise HTTPException(status_code=400, detail="No se puede cambiar el rol de un administrador")
    
    # Check if email exists (if changing)
    if 'email' in update_data and update_data['email']:
        existing = db.query(User).filter(User.email == update_data['email'], User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email ya registrado")
    
    # Check if username exists (if changing)
    if 'username' in update_data and update_data['username']:
        existing = db.query(User).filter(User.username == update_data['username'], User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username ya registrado")
    
    # Hash password if provided
    if 'password' in update_data and update_data['password']:
        password_hash = bcrypt.hashpw(
            update_data['password'].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        user.password_hash = password_hash
        del update_data['password']
    
    # Update other fields
    for key, value in update_data.items():
        if key != 'password':
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new user (admin only)"""
    # Validate role
    valid_roles = ['user', 'moderator', 'admin']
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Valores permitidos: {', '.join(valid_roles)}")
    
    # Check if email exists
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    # Check if username exists
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username ya registrado")
    
    # Hash password
    password_hash = bcrypt.hashpw(
        data.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    
    # Create user
    user = User(
        username=data.username,
        email=data.email,
        phone_area_code=data.phone_area_code,
        phone_number=data.phone_number,
        password_hash=password_hash,
        role=data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.put("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update user role (admin only)"""
    # Validate role
    valid_roles = ['user', 'moderator', 'admin']
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Valores permitidos: {', '.join(valid_roles)}")
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # S-10: Prevent self-role-change
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol")
    
    # Update role
    user.role = data.role
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Deactivate a user (soft delete - admin only)"""
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Cannot deactivate self
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")
    
    # Deactivate user
    user.is_active = False
    user.deactivated_at = datetime.now(timezone.utc)
    user.deactivated_by = admin.id
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Activate a user (admin only)"""
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Activate user
    user.is_active = True
    user.deactivated_at = None
    user.deactivated_by = None
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/reset-password", response_model=UserResponse)
def reset_password(
    user_id: int,
    data: PasswordReset,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Reset user password (admin only)"""
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Hash new password
    password_hash = bcrypt.hashpw(
        data.new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    
    # Update password
    user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    
    return user
