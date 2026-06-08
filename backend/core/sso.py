import logging
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from core.config import settings

logger = logging.getLogger(__name__)


class SSOUserInfo(BaseModel):
    sub: str
    email: str
    name: str
    provider: str


class OAuthProvider:
    def __init__(self, name: str, client_id: str, client_secret: str, authorize_url: str, token_url: str, userinfo_url: str, scopes: list[str] | None = None):
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url
        self.scopes = scopes or ["openid", "email", "profile"]

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
        }
        return f"{self.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                logger.error("Token exchange failed: %s %s", resp.status_code, resp.text)
                raise HTTPException(status_code=401, detail="Failed to exchange authorization code")
            return resp.json()

    async def get_userinfo(self, access_token: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                logger.error("Userinfo fetch failed: %s %s", resp.status_code, resp.text)
                raise HTTPException(status_code=401, detail="Failed to fetch user info")
            return resp.json()

    def parse_userinfo(self, raw: dict) -> SSOUserInfo:
        return SSOUserInfo(
            sub=str(raw.get("sub", "")),
            email=raw.get("email", ""),
            name=raw.get("name", raw.get("given_name", "")),
            provider=self.name,
        )


PROVIDERS: dict[str, OAuthProvider] = {}


def init_providers():
    if settings.google_client_id and settings.google_client_secret:
        PROVIDERS["google"] = OAuthProvider(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scopes=["openid", "email", "profile"],
        )
        logger.info("Google OAuth provider configured")

    if settings.azure_client_id and settings.azure_client_secret and settings.azure_tenant_id:
        tenant = settings.azure_tenant_id
        PROVIDERS["azure"] = OAuthProvider(
            name="azure",
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
            authorize_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/oidc/userinfo",
            scopes=["openid", "email", "profile"],
        )
        logger.info("Azure AD OAuth provider configured")

    logger.info("SSO providers initialized: %s", list(PROVIDERS.keys()))


def get_provider(name: str) -> OAuthProvider:
    provider = PROVIDERS.get(name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"SSO provider '{name}' not configured")
    return provider
