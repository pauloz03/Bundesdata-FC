"""User access and invitations — PostgreSQL implementation pending."""

from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException, Depends
from auth_guard import get_current_user


router = APIRouter(prefix="/users", tags=["users"])


_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="User routes not implemented yet (PostgreSQL).",
)

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    user_id= current_user["user_id"]
    response = {"user_id": user_id}

    return response


@router.get("/access")
def get_access_state():
    raise _NOT_IMPLEMENTED


@router.post("/invitations")
def send_invitation(body: dict = Body(...)):
    raise _NOT_IMPLEMENTED


@router.post("/invitations/accept")
def accept_invitation():
    raise _NOT_IMPLEMENTED
