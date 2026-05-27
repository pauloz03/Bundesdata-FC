"""User snapshots and sharing — placeholder for Cognito-backed features."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

import access_control
from auth_guard import get_current_user_payload, get_user_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me():
    return {"message": "not implemented yet"}


def _requester_email(user_payload: dict) -> str:
    return access_control.normalize_email(get_user_email(user_payload))


@router.get("/access")
def get_access_state(user_payload: dict = Depends(get_current_user_payload)):
    email = _requester_email(user_payload)
    state = access_control.list_access()
    is_owner = access_control.is_owner(email)
    can_access = access_control.can_access_s3(email)
    out = {
        "requester_email": email,
        "is_owner": is_owner,
        "can_access_s3": can_access,
        "invitation_status": (
            "owner"
            if is_owner
            else ("accepted" if email in set(state["accepted_invites"]) else ("pending" if email in set(state["pending_invites"]) else "none"))
        ),
    }
    if is_owner:
        out.update(state)
    return out


@router.post("/invitations")
def send_invitation(
    body: dict = Body(...),
    user_payload: dict = Depends(get_current_user_payload),
):
    requester = _requester_email(user_payload)
    if not access_control.is_owner(requester):
        raise HTTPException(status_code=403, detail="Only owner can send invitations")
    try:
        return access_control.send_invite(body.get("email"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/invitations/accept")
def accept_invitation(user_payload: dict = Depends(get_current_user_payload)):
    email = _requester_email(user_payload)
    return access_control.accept_invite(email)
