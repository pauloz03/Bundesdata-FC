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

#This object's whole job is: look at the incoming request, find the Authorization header, check it
#  starts with Bearer , and if so, pull out everything after it, the token part
security_scheme = HTTPBearer()


#so credentials is equal to a HTTPAuthorizationCredentials object,  which gets a value  when we call 
# security_schema to get the token, using Depends. Before get_current_user runs even one line, FastAPI sees 
# Depends(security_scheme) and calls security_scheme itself, this is HTTPBearer() doing its extraction work 
# on the incoming request right now
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


