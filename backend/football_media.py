"""
football_media.py
─────────────────
Media enrichment via API-Football (api-sports.io v3).

Auth header (required):
  x-apisports-key: <FOOTBALL_API_KEY>

Endpoints used:
  GET /teams?id={team_id}           → team.logo
  GET /players/squads?team={team_id} → player.number + player.photo

We resolve Bundesliga clubs by name → API team id, then match players
by jersey number (fallback: last-name match). Results are cached in-memory.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import config

log = logging.getLogger(__name__)

# API-Football team ids for clubs in our match registry (Bundesliga).
TEAM_API_IDS: dict[str, int] = {
    "bayern": 157,
    "bayern munich": 157,
    "fc bayern munich": 157,
    "fc bayern münchen": 157,
    "dortmund": 165,
    "borussia dortmund": 165,
    "frankfurt": 169,
    "eintracht frankfurt": 169,
    "stuttgart": 172,
    "vfb stuttgart": 172,
    "hamburg": 175,
    "hamburger sv": 175,
    "union berlin": 182,
    "fc union berlin": 182,
}

_team_bundle_cache: dict[int, dict] = {}


def _api_key() -> str:
    return (config.FOOTBALL_API_KEY or "").strip().strip('"')


def _api_get(path: str, params: dict[str, str | int]) -> dict | None:
    key = _api_key()
    if not key:
        return None

    query = urlencode({k: v for k, v in params.items() if v is not None and v != ""})
    base = config.FOOTBALL_API_BASE.rstrip("/")
    url = f"{base}{path}"
    if query:
        url = f"{url}?{query}"

    req = Request(
        url,
        headers={
            "x-apisports-key": key,
            "Accept": "application/json",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=12, context=ctx) as res:
            body = json.loads(res.read().decode("utf-8"))
    except HTTPError as exc:
        log.warning("Football API %s %s: HTTP %s", path, params, exc.code)
        return None
    except Exception as exc:
        log.warning("Football API %s %s failed: %s", path, params, exc)
        return None

    errors = body.get("errors")
    if errors:
        log.warning("Football API %s %s errors: %s", path, params, errors)
        return None
    return body


def _normalize_team_name(name: str | None) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"^fc\s+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def resolve_team_api_id(team_name: str | None) -> int | None:
    """Map our match metadata team label to API-Football team id."""
    norm = _normalize_team_name(team_name)
    if not norm:
        return None
    if norm in TEAM_API_IDS:
        return TEAM_API_IDS[norm]

    # Partial match (e.g. "fc union berlin" contains "union berlin").
    for key, tid in TEAM_API_IDS.items():
        if key in norm or norm in key:
            return tid
    return None


def _last_name_tokens(name: str) -> set[str]:
    parts = [p.lower() for p in re.split(r"[\s,.\-]+", name) if len(p) > 2]
    if not parts:
        return set()
    return {parts[-1], *parts[-2:]}


def _fetch_team_bundle(team_id: int) -> dict:
    """
    Returns:
      logo: str | None
      by_number: dict[int, dict]  # jersey -> {name, photo}
      roster: list[dict]
    """
    if team_id in _team_bundle_cache:
        return _team_bundle_cache[team_id]

    bundle: dict = {"logo": None, "by_number": {}, "roster": []}

    team_payload = _api_get("/teams", {"id": team_id})
    if team_payload:
        rows = team_payload.get("response") or []
        if rows:
            bundle["logo"] = (rows[0].get("team") or {}).get("logo")

    squad_payload = _api_get("/players/squads", {"team": team_id})
    if squad_payload:
        rows = squad_payload.get("response") or []
        if rows:
            team = rows[0].get("team") or {}
            if not bundle["logo"]:
                bundle["logo"] = team.get("logo")
            players = rows[0].get("players") or []
            bundle["roster"] = players
            for p in players:
                num = p.get("number")
                if num is not None:
                    try:
                        bundle["by_number"][int(num)] = p
                    except (TypeError, ValueError):
                        pass

    _team_bundle_cache[team_id] = bundle
    return bundle


def get_team_logo(team_name: str | None) -> str | None:
    team_id = resolve_team_api_id(team_name)
    if not team_id:
        return None
    return _fetch_team_bundle(team_id).get("logo")


def get_player_headshot(
    player_name: str | None,
    team_name: str | None = None,
    *,
    jersey: int | None = None,
) -> str | None:
    team_id = resolve_team_api_id(team_name)
    if not team_id:
        return None

    bundle = _fetch_team_bundle(team_id)
    by_number: dict[int, dict] = bundle.get("by_number") or {}

    if jersey is not None and int(jersey) in by_number:
        return by_number[int(jersey)].get("photo")

    name = (player_name or "").strip()
    if not name:
        return None

    tokens = _last_name_tokens(name)
    if not tokens:
        return None

    for p in bundle.get("roster") or []:
        api_name = (p.get("name") or "").lower()
        api_tokens = _last_name_tokens(api_name)
        if tokens & api_tokens:
            return p.get("photo")
    return None


def enrich_players_media(
    players: list[dict],
    *,
    home_team_name: str | None,
    away_team_name: str | None,
) -> list[dict]:
    """Return players enriched with headshot_url and team_logo_url."""
    home_id = resolve_team_api_id(home_team_name)
    away_id = resolve_team_api_id(away_team_name)

    home_bundle = _fetch_team_bundle(home_id) if home_id else {}
    away_bundle = _fetch_team_bundle(away_id) if away_id else {}

    out: list[dict] = []
    for p in players:
        row = dict(p)
        team_flag = int(row.get("team_flag", 1))
        team_name = home_team_name if team_flag == 1 else away_team_name
        bundle = home_bundle if team_flag == 1 else away_bundle

        player_name = row.get("player_name") or " ".join(
            x for x in [row.get("first_name"), row.get("last_name")] if x
        )
        jersey = row.get("jersey")
        try:
            jersey_int = int(jersey) if jersey is not None else None
        except (TypeError, ValueError):
            jersey_int = None

        row["team_name"] = team_name
        row["team_logo_url"] = bundle.get("logo")
        row["headshot_url"] = get_player_headshot(
            player_name,
            team_name,
            jersey=jersey_int,
        )
        out.append(row)
    return out
