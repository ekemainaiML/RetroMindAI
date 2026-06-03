import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.models import User, Workshop

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
JWT_BEARER = HTTPBearer(auto_error=False)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def prefix_from_key(key: str) -> str:
    return key[:7] if len(key) >= 7 else key


def generate_api_key() -> tuple[str, str, str]:
    raw = "rm_" + secrets.token_hex(20)
    return raw, hash_api_key(raw), prefix_from_key(raw)


def _lookup_workshop(api_key: str, db: Session) -> Workshop | None:
    key_hash = hash_api_key(api_key)
    workshop = (
        db.query(Workshop)
        .filter(Workshop.api_key_hash == key_hash, Workshop.is_active.is_(True))
        .first()
    )
    if workshop:
        return workshop
    if api_key == settings.admin_api_key:
        return (
            db.query(Workshop)
            .filter(Workshop.is_active.is_(True))
            .order_by(Workshop.created_at)
            .first()
        )
    return None


def get_current_workshop(
    api_key: str | None = Depends(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> str:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    workshop = _lookup_workshop(api_key, db)
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    return str(workshop.id)


def get_current_workshop_obj(
    api_key: str | None = Depends(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> Workshop:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    workshop = _lookup_workshop(api_key, db)
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    return workshop


def get_optional_workshop(
    api_key: str | None = Depends(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> str | None:
    if not api_key:
        return None
    workshop = _lookup_workshop(api_key, db)
    if not workshop:
        return None
    return str(workshop.id)


def get_admin_user(
    api_key: str | None = Depends(API_KEY_HEADER),
) -> str:
    from core.config import settings
    if not api_key or not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin access requires a valid admin API key",
        )
    if api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )
    return "admin"


# ── Password hashing ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ── JWT ──────────────────────────────────────────────────────────

def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict | None:
    try:
        return pyjwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None


def get_current_user(
    bearer=Depends(JWT_BEARER),
    db: Session = Depends(get_db),
) -> User:
    if bearer is None or not bearer.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    payload = decode_jwt(bearer.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = db.query(User).filter(
        User.id == payload["sub"], User.is_active.is_(True)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def seed_demo_workshop(db: Session) -> str:
    demo = db.query(Workshop).filter(Workshop.name == "Demo Workshop").first()
    if demo:

        if demo.demo_raw_key:
            expected_hash = hashlib.sha256(demo.demo_raw_key.encode()).hexdigest()
            if expected_hash == demo.api_key_hash:
                return demo.api_key_prefix
        logger.warning("Demo workshop key mismatch — regenerating")
        raw, key_hash, prefix = generate_api_key()
        demo.api_key_hash = key_hash
        demo.api_key_prefix = prefix
        demo.demo_raw_key = raw
        db.commit()
        logger.info("Demo Workshop key regenerated: %s", raw)
        return prefix

    raw, key_hash, prefix = generate_api_key()
    workshop = Workshop(
        id=uuid.uuid4(),
        name="Demo Workshop",
        email="demo@retromind.ai",
        tier="guest",
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        demo_raw_key=raw,
        is_active=True,
    )
    db.add(workshop)
    db.commit()
    logger.info("Demo Workshop created with full API key: %s", raw)
    logger.info("Set NEXT_PUBLIC_API_KEY=%s in frontend/.env.local", raw)
    return prefix
