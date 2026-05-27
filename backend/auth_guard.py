"""
auth_guard.py
─────────────
Cognito JWT verification + owner/invite access guard for S3-backed analytics.
"""

from __future__ import annotations

import json
import time
from urllib.request import Request, urlopen

import jwt
from fastapi import Depends, Header, HTTPException
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWTError

import access_control
import config

_jwks_cache: dict[str, object] = {"exp": 0.0, "keys": {}}
_JWKS_TTL_SECONDS = 60 * 60


def _issuer() -> str:
    if not config.COGNITO_REGION or not config.COGNITO_USER_POOL_ID:
        raise HTTPException(
            status_code=500,
            detail="Server auth is not configured (missing Cognito env vars).",
        )
    return f"https://cognito-idp.{config.COGNITO_REGION}.amazonaws.com/{config.COGNITO_USER_POOL_ID}"


def _load_jwks() -> dict:
    now = time.time()
    if _jwks_cache["keys"] and now < float(_jwks_cache["exp"]):
        return _jwks_cache["keys"]  # type: ignore[return-value]

    issuer = _issuer()
    req = Request(f"{issuer}/.well-known/jwks.json", headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=8) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to fetch Cognito JWKS: {exc}") from exc

    keys = {k.get("kid"): k for k in payload.get("keys", []) if k.get("kid")}
    _jwks_cache["keys"] = keys
    _jwks_cache["exp"] = now + _JWKS_TTL_SECONDS
    return keys


def _verify_token(token: str) -> dict:
    try:
        unverified = jwt.get_unverified_header(token)
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token header") from exc

    kid = unverified.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing key id")

    keys = _load_jwks()
    jwk = keys.get(kid)
    if not jwk:
        # Key rotation fallback: force refresh once.
        _jwks_cache["exp"] = 0.0
        keys = _load_jwks()
        jwk = keys.get(kid)
    if not jwk:
        raise HTTPException(status_code=401, detail="Unknown signing key")

    signing_key = RSAAlgorithm.from_jwk(json.dumps(jwk))
    decode_kwargs = {
        "key": signing_key,
        "algorithms": ["RS256"],
        "issuer": _issuer(),
    }
    if config.COGNITO_CLIENT_ID:
        decode_kwargs["audience"] = config.COGNITO_CLIENT_ID
    else:
        decode_kwargs["options"] = {"verify_aud": False}

    try:
        payload = jwt.decode(token, **decode_kwargs)
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return payload


def get_current_user_payload(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return _verify_token(token)


def get_user_email(user_payload: dict) -> str:
    """Best-effort email/username extraction from Cognito token claims."""
    return (
        (user_payload.get("email") or "")
        or (user_payload.get("cognito:username") or "")
        or (user_payload.get("username") or "")
    ).strip().lower()


def require_s3_access(user_payload: dict = Depends(get_current_user_payload)) -> dict:
    email = get_user_email(user_payload)
    if not email:
        raise HTTPException(status_code=403, detail="Token does not include usable user identifier")

    if not access_control.can_access_s3(email):
        raise HTTPException(
            status_code=403,
            detail="Access denied. You are not invited to view S3 analytics data.",
        )
    return user_payload

