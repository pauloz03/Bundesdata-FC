"""User snapshots and sharing — placeholder for Cognito-backed features."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me():
    return {"message": "not implemented yet"}
