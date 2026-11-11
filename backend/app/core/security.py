from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("Password exceeds maximum bcrypt length of 72 bytes.")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")
        if len(pwd_bytes) > 72:
            return False
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "role", "exp", "type"]},
        )
        if payload.get("type") != "access":
            raise credentials_exc
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise credentials_exc from exc
