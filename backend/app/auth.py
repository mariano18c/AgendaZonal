import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Header, Request, Response
from sqlalchemy.orm import Session
from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_ISSUER, JWT_AUDIENCE, HTTPS
from app.database import get_db
from app.models.user import User


# Cookie configuration
AUTH_COOKIE_NAME = "auth_token"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={
            "verify_issuer": True,
            "verify_audience": True,
            "require": ["iss", "aud", "exp", "sub"]
        },
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE
    )


def get_token_from_cookie(request: Request) -> Optional[str]:
    """Extract JWT from HttpOnly cookie."""
    return request.cookies.get(AUTH_COOKIE_NAME)


def get_current_user(
    authorization: Optional[str] = Header(None),
    request: Request = None,
    db: Session = Depends(get_db)
) -> User:
    """Get current user from either Authorization header or cookie."""
    token = None
    
    # First try Authorization header (for API clients)
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                pass  # Use token from header
            else:
                raise HTTPException(status_code=401, detail="Esquema inválido")
        except ValueError:
            raise HTTPException(status_code=401, detail="Formato de token inválido")
    # Fall back to cookie (for browser clients)
    elif request:
        token = get_token_from_cookie(request)
    
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")

    try:
        payload = verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Token inválido")
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Formato de token inválido")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inactivo")

    return user


def set_auth_cookie(response: Response, token: str) -> Response:
    """Set the auth token in an HttpOnly cookie."""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=AUTH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",  # lax allows cross-origin navigation
        secure=HTTPS,  # Condicional según переменная окружения HTTPS
        path="/",
    )
    return response


def clear_auth_cookie(response: Response) -> Response:
    """Clear the auth cookie."""
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
    )
    return response
