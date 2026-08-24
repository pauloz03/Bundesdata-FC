"""
auth_guard.py
─────────────
"""
from __future__ import annotations
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import config
import secrets
from datetime import datetime, timedelta, timezone


security_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    token = credentials.credentials
    payload = verify_access_token(token)
    return payload


_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="Auth not implemented yet (PostgreSQL).",
)


def verify_access_token(token: str) -> dict:
    try:
        payload= jwt.decode(token, config.SECRET_JWT_KEY, algorithms=[config.TOKEN_ALGORITHM])
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_payload(
    authorization: str | None = Header(default=None),
) -> dict:
    raise _NOT_IMPLEMENTED


def get_user_email(user_payload: dict) -> str:
    return (user_payload.get("email") or "").strip().lower()


def require_s3_access(
    user_payload: dict = Depends(get_current_user_payload),
) -> dict:
    raise _NOT_IMPLEMENTED
