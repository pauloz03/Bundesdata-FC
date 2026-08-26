"""User identity, dashboard sharing and invitations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

import access_control
from auth_guard import get_current_user
from postgres import SessionLocal

router = APIRouter(prefix="/users", tags=["users"])


class InviteBody(BaseModel):
    email: str


class AcceptBody(BaseModel):
    invitation_id: str


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    db_session = SessionLocal()
    try:
        row = db_session.execute(
            text("SELECT id, email FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": str(row["id"]), "email": row["email"]}
    finally:
        db_session.close()


@router.get("/access")
def get_access_state(current_user: dict = Depends(get_current_user)):
    return access_control.list_access(current_user["user_id"])


@router.post("/invitations")
def send_invitation(body: InviteBody, current_user: dict = Depends(get_current_user)):
    return access_control.send_invite(current_user["user_id"], body.email)


@router.post("/invitations/accept")
def accept_invitation(body: AcceptBody, current_user: dict = Depends(get_current_user)):
    return access_control.accept_invite(current_user["user_id"], body.invitation_id)


# Declared last so its two-segment path never shadows the literal routes above.
@router.get("/{owner_id}/dashboard")
def get_dashboard(owner_id: str, current_user: dict = Depends(get_current_user)):
    """
    Open a dashboard by owner. Refuses with 403 unless the caller owns it or
    holds an accepted invitation to it.
    """
    return access_control.get_dashboard(current_user["user_id"], owner_id)
