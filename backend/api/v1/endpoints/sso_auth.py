import logging
import uuid
from datetime import datetime, timezone

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.auth import create_jwt, generate_api_key, get_current_user, hash_password
from core.config import settings
from core.database import get_db
from core.models import User, WorkspaceRole, Workshop
from core.sso import PROVIDERS, SSOUserInfo, get_provider, init_providers

logger = logging.getLogger(__name__)

router = APIRouter()

SSO_STATE_TTL = 600


def _get_redis() -> redis_lib.Redis | None:
    try:
        return redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
    except Exception:
        return None


def _store_state(state: str, provider: str) -> None:
    redis_client = _get_redis()
    if redis_client:
        redis_client.setex(f"sso_state:{state}", SSO_STATE_TTL, provider)


def _get_state(state: str) -> str | None:
    redis_client = _get_redis()
    if redis_client:
        val = redis_client.get(f"sso_state:{state}")
        if val:
            redis_client.delete(f"sso_state:{state}")
            return val.decode()
    return None


init_providers()


@router.get("/auth/sso/providers")
def list_sso_providers():
    return {
        "providers": [
            {"id": name, "name": name.capitalize()}
            for name in PROVIDERS
        ]
    }


@router.get("/auth/sso/{provider}/authorize")
async def sso_authorize(
    provider: str,
    redirect: str = Query("/", description="Frontend redirect after login"),
):
    sso = get_provider(provider)
    state = str(uuid.uuid4())
    _store_state(state, provider)

    redirect_uri = f"{settings.backend_url}/api/v1/auth/sso/{provider}/callback"

    authorize_url = sso.get_authorize_url(state, redirect_uri)
    return RedirectResponse(url=authorize_url)


@router.get("/auth/sso/{provider}/callback")
async def sso_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    stored_provider = _get_state(state)
    if not stored_provider or stored_provider != provider:
        raise HTTPException(status_code=401, detail="Invalid or expired state parameter")

    sso = get_provider(provider)
    redirect_uri = f"{settings.backend_url}/api/v1/auth/sso/{provider}/callback"

    token_data = await sso.exchange_code(code, redirect_uri)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token received")

    raw_userinfo = await sso.get_userinfo(access_token)
    userinfo = sso.parse_userinfo(raw_userinfo)

    user = _find_or_create_user(userinfo, db)
    workshop = _get_or_create_workshop(user, db)

    jwt = create_jwt(str(user.id))

    frontend_url = settings.frontend_url.rstrip("/")
    redirect_url = f"{frontend_url}/auth/callback?token={jwt}&workshop_id={workshop.id}"

    return RedirectResponse(url=redirect_url)


@router.post("/auth/sso/link")
def link_sso_account(
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = body.get("provider")
    authorization_code = body.get("authorization_code")

    if not provider or not authorization_code:
        raise HTTPException(status_code=400, detail="provider and authorization_code required")

    user.sso_provider = provider
    user.sso_subject = authorization_code
    db.commit()

    return {"status": "linked", "provider": provider}


def _find_or_create_user(userinfo: SSOUserInfo, db: Session) -> User:
    user = db.query(User).filter(
        User.sso_provider == userinfo.provider,
        User.sso_subject == userinfo.sub,
    ).first()

    if user:
        return user

    existing = db.query(User).filter(User.email == userinfo.email).first()
    if existing:
        existing.sso_provider = userinfo.provider
        existing.sso_subject = userinfo.sub
        db.commit()
        return existing

    user = User(
        id=uuid.uuid4(),
        email=userinfo.email,
        name=userinfo.name,
        password_hash=hash_password(str(uuid.uuid4())),
        sso_provider=userinfo.provider,
        sso_subject=userinfo.sub,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _get_or_create_workshop(user: User, db: Session) -> Workshop:
    workshops = db.query(Workshop).filter(Workshop.user_id == user.id).all()
    if workshops:
        return workshops[0]

    raw, key_hash, prefix = generate_api_key()
    workshop = Workshop(
        id=uuid.uuid4(),
        user_id=user.id,
        name=user.name,
        email=user.email,
        tier="free",
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        is_active=True,
        api_key_expires_at=datetime.now(timezone.utc),
    )
    db.add(workshop)
    db.flush()

    user.current_workshop_id = workshop.id

    role = WorkspaceRole(
        id=uuid.uuid4(),
        user_id=user.id,
        workshop_id=workshop.id,
        role="admin",
        accepted_at=datetime.now(timezone.utc),
    )
    db.add(role)
    db.commit()

    return workshop
