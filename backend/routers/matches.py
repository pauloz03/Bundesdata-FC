"""
Match and player analytics routes.
Computes from local parquet / XML (S3 cache is disabled).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

import biomechanics_sync
import config
import db
import event_parser
import football_media
import possession
import skeleton_parser
from auth_guard import get_current_user

_match_deps = [] if config.SKIP_AUTH else [Depends(get_current_user)]

router = APIRouter(
    prefix="/matches",
    tags=["matches"],
    dependencies=_match_deps,
)


def _listed_match_ids() -> list[str]:
    return [
        mid
        for mid in config.MATCHES
        if mid in config.MATCH_METADATA and db.has_local_parquet(mid)
    ]


def _ensure_match(match_id: str) -> dict:
    meta = config.MATCH_METADATA.get(match_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown match '{match_id}'. Available: {list(config.MATCHES.keys())}",
        )
    if not db.has_local_parquet(match_id):
        raise HTTPException(
            status_code=404,
            detail=f"No local parquet for '{match_id}'. Drop the file in {config.LOCAL_PARQUET_DIR}.",
        )
    return meta


@router.get("")
def list_matches():
    return {
        "matches": [
            {
                "id":        mid,
                "label":     config.MATCH_METADATA.get(mid, {}).get("label", mid),
                "date":      config.MATCH_METADATA.get(mid, {}).get("date"),
                "home_team": config.MATCH_METADATA.get(mid, {}).get("home_team"),
                "away_team": config.MATCH_METADATA.get(mid, {}).get("away_team"),
            }
            for mid in _listed_match_ids()
        ]
    }


@router.get("/{match_id}/timeline")
def get_timeline(match_id: str):
    _ensure_match(match_id)
    return {"match_id": match_id, "timeline": event_parser.get_match_timeline(match_id)}


@router.get("/{match_id}/possession")
def get_possession(
    match_id: str,
    recompute: bool = Query(False, description="Bypass the local JSON cache"),
):
    """
    Possession share and derived events (passes / turnovers / restarts).

    Derived from tracking data, not vendor event labels — see possession.py.
    A cold run scans the full parquet and takes ~25s; results are cached.
    """
    meta = config.MATCH_METADATA.get(match_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown match '{match_id}'")

    # The cached JSON is committed to the repo, so this endpoint still works on
    # a clone that has no parquet. Only a cold run needs the tracking file.
    data = None if recompute else possession.load(match_id)
    if data is None:
        _ensure_match(match_id)
        data = possession.load_or_compute(match_id, recompute=True)

    return {
        **data,
        "home_team": meta.get("home_team"),
        "away_team": meta.get("away_team"),
        "label": meta.get("label", match_id),
    }


@router.get("/{match_id}/players")
def get_players(match_id: str):
    meta = _ensure_match(match_id)
    players = skeleton_parser.get_player_list(match_id)
    players = football_media.enrich_players_media(
        players,
        home_team_name=meta.get("home_team"),
        away_team_name=meta.get("away_team"),
    )
    return {"match_id": match_id, "players": players}


@router.get("/{match_id}/players/{jersey}")
def get_player(
    match_id: str,
    jersey: int,
    team: int = Query(1, description="TRACAB team flag: 1=home, 0=away"),
    player_id: str | None = Query(
        None,
        description="DFL player id from XML; defaults to jersey_team placeholder",
    ),
    recompute: bool = Query(False, description="Unused (live compute only)"),
):
    _ensure_match(match_id)
    pid = (
        player_id
        or event_parser.resolve_player_id(match_id, jersey, team)
        or f"jersey_{jersey}_team{team}"
    )
    result = biomechanics_sync.get_player_event_biomechanics(
        match_id, pid, jersey, team
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{match_id}/players/{jersey}/fatigue")
def get_fatigue(
    match_id: str,
    jersey: int,
    team: int = Query(1),
    recompute: bool = Query(False),
):
    _ensure_match(match_id)
    fatigue = skeleton_parser.get_fatigue_curve(match_id, jersey, team)
    if "error" in fatigue:
        raise HTTPException(status_code=404, detail=fatigue["error"])

    from fatigue_episodes import detect_degradation_episodes

    return {
        "match_id": match_id,
        "player":   fatigue.get("player"),
        "fatigue":  {
            "baseline": fatigue.get("baseline"),
            "curve":    fatigue.get("curve"),
            "summary":  fatigue.get("summary"),
        },
        "degradation_episodes": detect_degradation_episodes(fatigue.get("curve", [])),
    }


@router.get("/{match_id}/players/{jersey}/events")
def get_events(
    match_id: str,
    jersey: int,
    team: int = Query(1),
    player_id: str | None = Query(None),
    recompute: bool = Query(False),
):
    """Shots (all) + notable passes with biomechanics."""
    _ensure_match(match_id)
    pid = (
        player_id
        or event_parser.resolve_player_id(match_id, jersey, team)
        or f"jersey_{jersey}_team{team}"
    )
    result = biomechanics_sync.get_player_event_biomechanics(
        match_id, pid, jersey, team
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {
        "match_id":       match_id,
        "player":         result.get("player"),
        "shots":          result.get("shots", []),
        "passes":         result.get("passes", []),
        "passes_summary": result.get("passes_summary", {}),
    }
