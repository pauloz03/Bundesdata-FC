"""
access_control.py
─────────────────
Dashboard sharing.

Every user owns exactly one dashboard — their own. An accepted invitation grants
one other registered user read access to it. There is no global owner role: the
relationship is peer to peer and always directional, so A inviting B says nothing
about whether B has invited A.

Invitations are only ever issued to addresses that already have an account. That
keeps `invitee_user_id` non-null for every row, so access checks join on the user
id rather than falling back to matching raw email text.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import text

from postgres import SessionLocal

# Rows in these states are live; 'revoked' and 'expired' are history. Inlined
# into the SQL rather than bound, since a tuple parameter would need an
# expanding bindparam and these are fixed enum labels either way.
_LIVE_SQL = "('pending', 'accepted')"


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _as_uuid(value: str, label: str) -> str:
    """Reject malformed ids here so Postgres never sees a bad cast."""
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


def _require_user(db, user_id: str) -> dict:
    row = (
        db.execute(
            text("SELECT id, email FROM users WHERE id = :uid"),
            {"uid": _as_uuid(user_id, "user id")},
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    return row


def list_access(user_id: str) -> dict:
    """Both directions of sharing, plus the dashboards this user may open."""
    db = SessionLocal()
    try:
        me = _require_user(db, user_id)

        sent = (
            db.execute(
                text(
                    f"""
                    SELECT id, invitee_email AS email, status
                      FROM invitations
                     WHERE owner_user_id = :uid
                       AND status IN {_LIVE_SQL}
                     ORDER BY created_at DESC
                    """
                ),
                {"uid": me["id"]},
            )
            .mappings()
            .all()
        )

        received = (
            db.execute(
                text(
                    f"""
                    SELECT i.id, i.status, i.owner_user_id, u.email AS owner_email
                      FROM invitations i
                      JOIN users u ON u.id = i.owner_user_id
                     WHERE i.invitee_user_id = :uid
                       AND i.status IN {_LIVE_SQL}
                     ORDER BY i.created_at DESC
                    """
                ),
                {"uid": me["id"]},
            )
            .mappings()
            .all()
        )

        # Your own dashboard always leads; shared ones follow in invite order.
        viewable = [
            {"user_id": str(me["id"]), "email": me["email"], "is_self": True}
        ] + [
            {
                "user_id": str(r["owner_user_id"]),
                "email": r["owner_email"],
                "is_self": False,
            }
            for r in received
            if r["status"] == "accepted"
        ]

        return {
            "user_id": str(me["id"]),
            "email": me["email"],
            "sent": [
                {"id": str(r["id"]), "email": r["email"], "status": r["status"]}
                for r in sent
            ],
            "received": [
                {
                    "id": str(r["id"]),
                    "owner_email": r["owner_email"],
                    "status": r["status"],
                }
                for r in received
            ],
            "viewable_dashboards": viewable,
        }
    finally:
        db.close()


def send_invite(owner_user_id: str, email: str) -> dict:
    """Invite a registered user to view the caller's dashboard. Idempotent."""
    address = normalize_email(email)
    if not address:
        raise HTTPException(status_code=400, detail="Email is required")

    db = SessionLocal()
    try:
        me = _require_user(db, owner_user_id)

        if normalize_email(me["email"]) == address:
            raise HTTPException(
                status_code=400, detail="You already have access to your own dashboard"
            )

        invitee = (
            db.execute(
                text("SELECT id, email FROM users WHERE email = :email"),
                {"email": address},
            )
            .mappings()
            .first()
        )
        if not invitee:
            raise HTTPException(
                status_code=404, detail=f"{address} is not registered"
            )

        # Re-inviting someone who is already pending or accepted is a no-op that
        # reports the existing state, so the button is safe to press twice. The
        # partial unique index only covers 'pending', so this check is what stops
        # a second row being stacked on top of an accepted one.
        existing = (
            db.execute(
                text(
                    f"""
                    SELECT id, status FROM invitations
                     WHERE owner_user_id = :owner
                       AND invitee_user_id = :invitee
                       AND status IN {_LIVE_SQL}
                     LIMIT 1
                    """
                ),
                {"owner": me["id"], "invitee": invitee["id"]},
            )
            .mappings()
            .first()
        )
        if existing:
            return {
                "id": str(existing["id"]),
                "email": address,
                "status": existing["status"],
                "already_existed": True,
            }

        row = (
            db.execute(
                text(
                    """
                    INSERT INTO invitations
                        (owner_user_id, invitee_email, invitee_user_id, status)
                    VALUES (:owner, :email, :invitee, 'pending')
                    ON CONFLICT (owner_user_id, invitee_email)
                        WHERE status = 'pending'
                        DO NOTHING
                    RETURNING id, status
                    """
                ),
                {"owner": me["id"], "email": address, "invitee": invitee["id"]},
            )
            .mappings()
            .first()
        )
        db.commit()

        if not row:
            # Lost a race against a concurrent identical invite; report theirs.
            row = (
                db.execute(
                    text(
                        """
                        SELECT id, status FROM invitations
                         WHERE owner_user_id = :owner
                           AND invitee_email = :email
                           AND status = 'pending'
                         LIMIT 1
                        """
                    ),
                    {"owner": me["id"], "email": address},
                )
                .mappings()
                .first()
            )
            if not row:
                raise HTTPException(
                    status_code=500, detail="Could not create invitation"
                )
            return {
                "id": str(row["id"]),
                "email": address,
                "status": row["status"],
                "already_existed": True,
            }

        return {
            "id": str(row["id"]),
            "email": address,
            "status": row["status"],
            "already_existed": False,
        }
    finally:
        db.close()


def accept_invite(user_id: str, invitation_id: str) -> dict:
    """
    Claim one pending invitation addressed to the caller.

    Guarded in a single statement: the WHERE clause carries the authorization, so
    an invitation belonging to somebody else can never be accepted, and a double
    click cannot accept twice.
    """
    invite_id = _as_uuid(invitation_id, "invitation id")

    db = SessionLocal()
    try:
        me = _require_user(db, user_id)
        row = (
            db.execute(
                text(
                    """
                    UPDATE invitations
                       SET status = 'accepted',
                           accepted_at = now(),
                           updated_at = now()
                     WHERE id = :invite
                       AND status = 'pending'
                       AND invitee_user_id = :uid
                    RETURNING id
                    """
                ),
                {"invite": invite_id, "uid": me["id"]},
            )
            .mappings()
            .first()
        )
        if not row:
            db.rollback()
            # Not yours, not pending, or not there — all the same to the caller.
            raise HTTPException(status_code=404, detail="Invitation not found")

        db.commit()
        return {"id": str(row["id"]), "status": "accepted"}
    finally:
        db.close()


def can_view(viewer_user_id: str, owner_user_id: str) -> bool:
    """True if the viewer owns the dashboard or holds an accepted invitation."""
    viewer = _as_uuid(viewer_user_id, "user id")
    owner = _as_uuid(owner_user_id, "owner id")
    if viewer == owner:
        return True

    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT 1 FROM invitations
                 WHERE owner_user_id = :owner
                   AND invitee_user_id = :viewer
                   AND status = 'accepted'
                 LIMIT 1
                """
            ),
            {"owner": owner, "viewer": viewer},
        ).first()
        return row is not None
    finally:
        db.close()


def get_dashboard(viewer_user_id: str, owner_user_id: str) -> dict:
    """Resolve a dashboard the viewer is allowed to open, or refuse."""
    owner = _as_uuid(owner_user_id, "owner id")

    if not can_view(viewer_user_id, owner):
        raise HTTPException(
            status_code=403, detail="You do not have access to this dashboard"
        )

    db = SessionLocal()
    try:
        row = (
            db.execute(
                text("SELECT id, email FROM users WHERE id = :uid"), {"uid": owner}
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        return {
            "owner_user_id": str(row["id"]),
            "owner_email": row["email"],
            "is_self": str(row["id"]) == _as_uuid(viewer_user_id, "user id"),
        }
    finally:
        db.close()
