"""
access_control.py
─────────────────
In-memory owner/invitation state for S3 analytics access.

Initial invited users come from config.INVITED_EMAILS.
This is process-memory only; restart resets runtime changes.
"""

from __future__ import annotations

import config

_pending_invites: set[str] = set()
_accepted_invites: set[str] = set(config.INVITED_EMAILS)


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def owner_email() -> str:
    return config.OWNER_EMAIL


def is_owner(email: str | None) -> bool:
    return normalize_email(email) == config.OWNER_EMAIL


def can_access_s3(email: str | None) -> bool:
    e = normalize_email(email)
    return e == config.OWNER_EMAIL or e in _accepted_invites


def list_access() -> dict:
    return {
        "owner_email": config.OWNER_EMAIL,
        "accepted_invites": sorted(_accepted_invites),
        "pending_invites": sorted(_pending_invites),
    }


def send_invite(email: str) -> dict:
    e = normalize_email(email)
    if not e:
        raise ValueError("Email is required")
    if e == config.OWNER_EMAIL:
        raise ValueError("Owner already has access")
    if e in _accepted_invites:
        return {"email": e, "status": "already_accepted"}
    _pending_invites.add(e)
    return {"email": e, "status": "pending"}


def accept_invite(email: str) -> dict:
    e = normalize_email(email)
    if not e:
        raise ValueError("Email is required")
    if e == config.OWNER_EMAIL:
        return {"email": e, "status": "owner"}
    if e not in _pending_invites and e not in _accepted_invites:
        return {"email": e, "status": "not_invited"}
    _pending_invites.discard(e)
    _accepted_invites.add(e)
    return {"email": e, "status": "accepted"}

