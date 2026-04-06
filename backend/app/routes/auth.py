from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import bcrypt
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, AuthResponse, UserResponse,
    CaptchaChallengeResponse, CaptchaVerifyRequest, PendingRegistrationResponse
)
from app.auth import create_token, get_current_user, set_auth_cookie, clear_auth_cookie
from app.rate_limit import limiter
from app.captcha import CaptchaManager

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/captcha", response_model=CaptchaChallengeResponse)
def get_captcha():
    """Get a new CAPTCHA challenge for registration."""
    challenge = CaptchaManager.generate()
    return CaptchaChallengeResponse(
        challenge_id=challenge.id,
        question=challenge.question
    )


@router.post("/captcha/verify")
def verify_captcha(data: CaptchaVerifyRequest):
    """Verify a CAPTCHA answer. Returns success status."""
    is_valid = CaptchaManager.verify(data.challenge_id, data.answer)
    return {"valid": is_valid}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get current user info"""
    return user


@router.post("/register", response_model=PendingRegistrationResponse, status_code=201)
@limiter.limit("3/minute")
def register(request: Request, response: Response, data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Always assigns role 'user'.

    For first-time admin setup, use /api/auth/bootstrap-admin instead.
    New registrations are created in pending state (is_active=False)
    and require administrator approval before login.
    """
    # CAP-01: Verify CAPTCHA before processing registration (if provided)
    if data.captcha_challenge_id and data.captcha_answer:
        if not CaptchaManager.verify(data.captcha_challenge_id, data.captcha_answer):
            raise HTTPException(
                status_code=400,
                detail="CAPTCHA incorrecto. Por favor, resolvé el problema matemático."
            )
    
    # Hash password
    password_hash = bcrypt.hashpw(
        data.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Create user with role 'user' and pending state (no race condition on admin role)
    user = User(
        username=data.username,
        email=data.email,
        phone_area_code=data.phone_area_code,
        phone_number=data.phone_number,
        password_hash=password_hash,
        role='user',
        is_active=False,  # Pending administrator approval
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # pragma: no cover (race condition safety net)
        db.rollback()
        raise HTTPException(status_code=400, detail="Email o username ya registrado")
    db.refresh(user)

    # NO token generated — user must wait for admin approval
    return PendingRegistrationResponse(
        message="Tu cuenta está pendiente de aprobación por un administrador. Podrás iniciar sesión cuando sea activada.",
        username=user.username,
    )


@router.post("/bootstrap-admin", response_model=AuthResponse, status_code=201)
@limiter.limit("3/minute")
def bootstrap_admin(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    """Create the first admin user. Only works if the database is empty."""
    # CAP-01: Verify CAPTCHA before processing (if provided)
    if data.captcha_challenge_id and data.captcha_answer:
        if not CaptchaManager.verify(data.captcha_challenge_id, data.captcha_answer):
            raise HTTPException(
                status_code=400,
                detail="CAPTCHA incorrecto. Por favor, resolvé el problema matemático."
            )
    
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=403,
            detail="Ya existen usuarios. Use /register para crear cuentas normales.",
        )

    # Hash password
    password_hash = bcrypt.hashpw(
        data.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    user = User(
        username=data.username,
        email=data.email,
        phone_area_code=data.phone_area_code,
        phone_number=data.phone_number,
        password_hash=password_hash,
        role='admin',
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # pragma: no cover (race condition safety net)
        db.rollback()
        raise HTTPException(status_code=400, detail="Email o username ya registrado")
    db.refresh(user)

    token = create_token(user.id)

    return AuthResponse(
        token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, data: LoginRequest, db: Session = Depends(get_db)):
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
        if user.deactivated_at is None:
            raise HTTPException(status_code=401, detail="Cuenta pendiente de aprobación. Un administrador debe activarla.")
        raise HTTPException(status_code=401, detail="Usuario desactivado. Contacte al administrador.")

    # Verify password
    if not bcrypt.checkpw(
        data.password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Generate token
    token = create_token(user.id)
    
    # Set HttpOnly cookie
    set_auth_cookie(response, token)

    return AuthResponse(
        token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout(response: Response):
    """Log out the current user by clearing the auth cookie."""
    clear_auth_cookie(response)
    return {"message": "Sesión cerrada correctamente"}
