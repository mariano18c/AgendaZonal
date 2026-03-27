import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from app.database import get_db
from app.models.user import User


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_current_user(
    authorization: str = Header(None), db: Session = Depends(get_db)
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Esquema inválido")
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
