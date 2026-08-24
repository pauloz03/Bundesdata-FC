"""
access_control.py
─────────────────
PostgreSQL invitation + user scan sharing — to be implemented.
"""

from __future__ import annotations


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def owner_email() -> str:
    raise NotImplementedError("PostgreSQL auth not implemented yet.")


def is_owner(email: str | None) -> bool:
    raise NotImplementedError("PostgreSQL auth not implemented yet.")


def can_access_s3(email: str | None) -> bool:
    raise NotImplementedError("PostgreSQL auth not implemented yet.")


def list_access() -> dict:
    raise NotImplementedError("PostgreSQL auth not implemented yet.")


def send_invite(email: str) -> dict:
    raise NotImplementedError("PostgreSQL auth not implemented yet.")


def accept_invite(email: str) -> dict:
    raise NotImplementedError("PostgreSQL auth not implemented yet.")
