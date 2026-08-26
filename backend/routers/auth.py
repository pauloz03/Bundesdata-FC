"""PostgreSQL auth routes — login, signup, logout, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

import auth

router = APIRouter(prefix="/auth", tags=["auth"])

class EmailPasswordBody(BaseModel):
    email: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


@router.post("/signup")
def signup(body: EmailPasswordBody):
    return auth.signup(body.email, body.password)


@router.post("/login")
def login(body: EmailPasswordBody, request: Request):
    return auth.login(body.email, body.password, request)


@router.post("/logout")
def logout(
    body: RefreshBody,
    credentials: HTTPAuthorizationCredentials = Depends(auth.security_scheme),
):
    return auth.logout(body.refresh_token, credentials)


@router.post("/refresh")
def refresh(body: RefreshBody):
    return auth.refresh_page(body.refresh_token)
