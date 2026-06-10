import hashlib
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt as pyjwt
import redis as redis_lib
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal, get_db
from core.models import User, Workshop

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
JWT_BEARER = HTTPBearer(auto_error=False)

API_KEY_EXPIRY_DAYS = 90


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def prefix_from_key(key: str) -> str:
    return key[:7] if len(key) >= 7 else key


def generate_api_key(expiry_days: int = API_KEY_EXPIRY_DAYS) -> tuple[str, str, str]:
    raw = "rm_" + secrets.token_hex(20)
    return raw, hash_api_key(raw), prefix_from_key(raw)


def _get_redis() -> redis_lib.Redis | None:
    try:
        return redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
    except Exception:
        return None


def _check_key_expiry(workshop: Workshop) -> Workshop | None:
    if workshop.api_key_expires_at and workshop.api_key_expires_at < datetime.now(timezone.utc):
        logger.warning("Expired API key attempt for workshop %s", workshop.id)
        return None
    if workshop.api_key_revoked_at:
        logger.warning("Revoked API key attempt for workshop %s", workshop.id)
        return None
    return workshop


def _check_breach(api_key: str, workshop_id: str, ip_address: str | None) -> None:
    if not ip_address:
        return
    redis_client = _get_redis()
    if not redis_client:
        return

    prefix = prefix_from_key(api_key)
    bucket = int(time.time() / 300)
    key = f"apikey_breach:{prefix}:{bucket}"
    redis_client.sadd(key, ip_address)
    redis_client.expire(key, 600)

    count = redis_client.scard(key)
    if count > 3:
        allowed = redis_client.get(f"apikey_allowlist:{prefix}")
        if allowed and ip_address in allowed.decode():
            return

        logger.warning(
            "Breach detected for API key %s: %d distinct IPs in 5min window",
            prefix, count,
        )
        db = SessionLocal()
        try:
            workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
            if workshop and not workshop.api_key_revoked_at:
                workshop.api_key_revoked_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("Auto-revoked API key %s due to breach detection", prefix)
        finally:
            db.close()


def _lookup_workshop(api_key: str, db: Session, ip_address: str | None = None) -> Workshop | None:
    key_hash = hash_api_key(api_key)
    workshop = (
        db.query(Workshop)
        .filter(Workshop.api_key_hash == key_hash, Workshop.is_active.is_(True))
        .first()
    )
    if workshop:
        workshop = _check_key_expiry(workshop)
        if workshop:
            _check_breach(api_key, str(workshop.id), ip_address)
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
            detail="Invalid or inactive API key. Key may be expired or revoked.",
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

def create_jwt(user_id: str, email: str = "", name: str = "") -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
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
        demo.api_key_expires_at = datetime.now(timezone.utc) + timedelta(days=90)
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
        api_key_expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db.add(workshop)
    db.commit()
    logger.info("Demo Workshop created with full API key: %s", raw)
    logger.info("Set NEXT_PUBLIC_API_KEY=%s in frontend/.env.local", raw)
    return prefix
