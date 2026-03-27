from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import bcrypt
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from app.auth import create_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """Get current user info"""
    return user


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
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

    # Check if this is the first user (make them admin)
    user_count = db.query(User).count()
    role = 'admin' if user_count == 0 else 'user'

    # Create user
    user = User(
        username=data.username,
        email=data.email,
        phone_area_code=data.phone_area_code,
        phone_number=data.phone_number,
        password_hash=password_hash,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    token = create_token(user.id)

    return AuthResponse(
        token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Find user by email or username
    user = (
        db.query(User)
        .filter(
            (User.email == data.username_or_email)
            | (User.username == data.username_or_email)
        )
        .first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # B-01: Check if user is active BEFORE expensive bcrypt
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inactivo. Contacte al administrador.")

    # Verify password
    if not bcrypt.checkpw(
        data.password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Generate token
    token = create_token(user.id)

    return AuthResponse(
        token=token,
        user=UserResponse.model_validate(user),
    )
