"""
Match and player analytics routes.
Serves precomputed JSON from S3 when available; falls back to live compute.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import biomechanics_sync
import config
import event_parser
import s3_storage
import skeleton_parser

router = APIRouter(prefix="/matches", tags=["matches"])


def _ensure_match(match_id: str) -> dict:
    meta = config.MATCH_METADATA.get(match_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown match '{match_id}'. Available: {list(config.MATCHES.keys())}",
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
            for mid in config.MATCHES
            if mid in config.MATCH_METADATA
        ]
    }


@router.get("/{match_id}/timeline")
def get_timeline(match_id: str):
    _ensure_match(match_id)
    data = s3_storage.load_timeline(match_id)
    if data:
        return data
    from event_parser import get_match_timeline

    return {"match_id": match_id, "timeline": get_match_timeline(match_id)}


@router.get("/{match_id}/players")
def get_players(match_id: str):
    _ensure_match(match_id)
    data = s3_storage.load_players(match_id)
    if data:
        return data
    players = skeleton_parser.get_player_list(match_id)
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
    recompute: bool = Query(False, description="Force live S3 compute instead of cache"),
):
    _ensure_match(match_id)
    if not recompute:
        cached = s3_storage.load_player(match_id, jersey, team)
        if cached:
            return cached

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
    if not recompute:
        cached = s3_storage.load_player(match_id, jersey, team)
        if cached and "fatigue" in cached:
            return {
                "match_id": match_id,
                "player":   cached.get("player"),
                "fatigue":  cached["fatigue"],
                "degradation_episodes": cached.get("degradation_episodes", []),
            }

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
    if not recompute:
        cached = s3_storage.load_player(match_id, jersey, team)
        if cached:
            return {
                "match_id":       match_id,
                "player":         cached.get("player"),
                "shots":          cached.get("shots", []),
                "passes":         cached.get("passes", []),
                "passes_summary": cached.get("passes_summary", {}),
            }

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
