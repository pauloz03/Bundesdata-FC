from __future__ import annotations

"""
event_parser.py
───────────────
Parses Bundesliga XML event and KPI data files from S3.
Returns structured shot and pass events for a player in a match.

Main public functions:
    get_match_timeline(match_id)
    get_player_shots(match_id, player_id)
    get_player_passes(match_id, player_id)
    get_player_id_map(match_id)
"""

import boto3
import xmltodict
import config
import db as db_module

_player_id_map_cache: dict[str, dict[tuple[int, int], str]] = {}
_player_profile_map_cache: dict[str, dict[tuple[int, int], dict]] = {}


def _s3_client():
    return boto3.client(
        "s3",
        region_name=config.AWS_REGION,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        aws_session_token=config.AWS_SESSION_TOKEN or None,
    )


def _read_xml_from_s3(match_id: str, xml_type: str) -> dict:
    """Download and parse an XML file from S3 into a dict."""
    s3_path = db_module.get_s3_xml_path(match_id, xml_type)

    # Strip s3://bucket/ prefix to get the key
    key = s3_path.replace(f"s3://{config.S3_BUCKET}/", "")

    s3 = _s3_client()
    obj = s3.get_object(Bucket=config.S3_BUCKET, Key=key)
    return xmltodict.parse(obj["Body"].read())


def _unwrap_put_data_request(raw: dict) -> dict:
    """DFL XML files are wrapped in PutDataRequest."""
    if not isinstance(raw, dict):
        return {}
    return raw.get("PutDataRequest", raw)


def _as_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _get_events(raw: dict) -> list[dict]:
    """Return match events from Events XML (PutDataRequest.Event)."""
    pdr = _unwrap_put_data_request(raw)
    events = pdr.get("Event", [])
    if isinstance(events, dict):
        events = [events]
    return events


def _event_payload(event: dict) -> tuple[str | None, dict]:
    """First non-attribute child of an Event → (type_name, payload dict)."""
    for key, val in event.items():
        if key.startswith("@"):
            continue
        return key, val if isinstance(val, dict) else {}
    return None, {}


def _get_kpi_rows(raw: dict) -> list[dict]:
    """Return KPI rows from kpi_data XML (PutDataRequest.AdvancedEvents.Event)."""
    pdr = _unwrap_put_data_request(raw)
    adv = pdr.get("AdvancedEvents", {})
    if not isinstance(adv, dict):
        return []
    rows = adv.get("Event", [])
    return _as_list(rows)


def _kpi_payload(row: dict) -> tuple[str | None, dict]:
    """Each KPI row wraps one event type (Play, ShotAtGoal, …)."""
    for key, val in row.items():
        if key.startswith("@"):
            continue
        return key, val if isinstance(val, dict) else {}
    return None, {}


def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _safe_str(val) -> str | None:
    return str(val).strip() if val is not None else None


def _truthy(val) -> bool:
    return str(val).lower() in {"true", "1", "yes"}


def _team_side_to_flag(match_id: str, side: str | None, index: int) -> int | None:
    """Map home/away (or list order) → TRACAB team_flag from config."""
    meta = config.MATCH_METADATA.get(match_id, {})
    home_flag = meta.get("home_team_flag", 1)
    away_flag = meta.get("away_team_flag", 0)

    if side:
        s = side.lower()
        if s in {"home", "h", "1"}:
            return home_flag
        if s in {"away", "a", "guest", "0", "2"}:
            return away_flag

    # Fallback: first team in XML = home
    return home_flag if index == 0 else away_flag


def _player_jersey(player: dict) -> int | None:
    for key in ("@ShirtNumber", "@JerseyNumber", "@Number", "ShirtNumber"):
        val = player.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                continue
    return None


def _player_dfl_id(player: dict) -> str | None:
    for key in ("@PersonId", "@PlayerId", "@Id", "PersonId", "PlayerId"):
        val = _safe_str(player.get(key))
        if val:
            return val
    return None


def _player_name_parts(player: dict) -> tuple[str | None, str | None, str | None]:
    """Return (first_name, last_name, display_name) from XML player attributes."""
    first = _safe_str(
        player.get("@FirstName")
        or player.get("@First")
        or player.get("@GivenName")
        or player.get("FirstName")
    )
    last = _safe_str(
        player.get("@LastName")
        or player.get("@Last")
        or player.get("@FamilyName")
        or player.get("LastName")
    )
    display = _safe_str(
        player.get("@DisplayName")
        or player.get("@KnownName")
        or player.get("@NickName")
        or player.get("@Name")
        or player.get("DisplayName")
    )
    return first, last, display


def _player_display_name(player: dict, player_id: str | None) -> str | None:
    first, last, display = _player_name_parts(player)
    if display:
        return display
    if first and last:
        return f"{first} {last}"
    if last:
        return last
    if first:
        return first
    return player_id


def get_player_profile_map(match_id: str) -> dict[tuple[int, int], dict]:
    """
    Map (jersey, team_flag) → profile dict from MatchInformations XML.

    Profile keys:
      dfl_player_id, player_name, first_name, last_name, jersey, team_flag
    """
    if match_id in _player_profile_map_cache:
        return _player_profile_map_cache[match_id]

    profiles: dict[tuple[int, int], dict] = {}

    try:
        raw = _read_xml_from_s3(match_id, "match_info")
        pdr = _unwrap_put_data_request(raw)
        mi = pdr.get("MatchInformation", {})
        teams = mi.get("Teams", {}).get("Team", [])

        for idx, team in enumerate(_as_list(teams)):
            side = _safe_str(
                team.get("@Role")
                or team.get("@TeamRole")
                or team.get("@TeamPosition")
                or team.get("@Type")
            )
            team_flag = _team_side_to_flag(match_id, side, idx)
            if team_flag is None:
                continue

            players = team.get("Players", {}).get("Player", [])
            for player in _as_list(players):
                jersey = _player_jersey(player)
                player_id = _player_dfl_id(player)
                if jersey is None:
                    continue

                first, last, _display = _player_name_parts(player)
                profiles[(jersey, team_flag)] = {
                    "dfl_player_id": player_id,
                    "player_name": _player_display_name(player, player_id),
                    "first_name": first,
                    "last_name": last,
                    "jersey": jersey,
                    "team_flag": team_flag,
                }
    except Exception:
        pass

    _player_profile_map_cache[match_id] = profiles
    return profiles


def get_player_id_map(match_id: str) -> dict[tuple[int, int], str]:
    """
    Map (jersey, team_flag) → DFL player id (e.g. DFL-OBJ-J01R3R).

    Parsed from MatchInformations XML (PutDataRequest.MatchInformation.Teams).
    """
    if match_id in _player_id_map_cache:
        return _player_id_map_cache[match_id]

    mapping: dict[tuple[int, int], str] = {}
    for key, profile in get_player_profile_map(match_id).items():
        player_id = _safe_str(profile.get("dfl_player_id"))
        if player_id:
            mapping[key] = player_id

    _player_id_map_cache[match_id] = mapping
    return mapping


def resolve_player_id(match_id: str, jersey: int, team_flag: int) -> str | None:
    """Look up DFL player id for a skeleton jersey + team flag."""
    return get_player_id_map(match_id).get((jersey, team_flag))


def resolve_player_profile(match_id: str, jersey: int, team_flag: int) -> dict | None:
    """Look up profile for a skeleton jersey + team flag."""
    return get_player_profile_map(match_id).get((jersey, team_flag))


def resolve_player_name(match_id: str, jersey: int, team_flag: int) -> str | None:
    """Look up display name for a skeleton jersey + team flag."""
    profile = resolve_player_profile(match_id, jersey, team_flag)
    return _safe_str(profile.get("player_name")) if profile else None


def get_kickoff_time_str(match_id: str) -> str | None:
    """Kickoff ISO timestamp from KPI AdvancedEvents (preferred) or match_info."""
    try:
        raw = _read_xml_from_s3(match_id, "kpi")
        adv = _unwrap_put_data_request(raw).get("AdvancedEvents", {})
        if isinstance(adv, dict):
            kickoff = _safe_str(adv.get("@KickoffTime"))
            if kickoff:
                return kickoff
    except Exception:
        pass

    try:
        raw = _read_xml_from_s3(match_id, "match_info")
        return _find_kickoff_string(_unwrap_put_data_request(raw))
    except Exception:
        return None


def _find_kickoff_string(node) -> str | None:
    if isinstance(node, dict):
        for key, val in node.items():
            if key in ("MatchKickoffTime", "KickoffTime", "@MatchKickoffTime", "@KickoffTime"):
                if isinstance(val, str):
                    return val
            found = _find_kickoff_string(val)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_kickoff_string(item)
            if found:
                return found
    return None


# ─────────────────────────────────────────────────────────────────────────────
# KPI lookup — index keyed by EventId
# ─────────────────────────────────────────────────────────────────────────────

def _build_kpi_index(match_id: str) -> dict:
    """
    Parse KPI XML (AdvancedEvents) and index rows by @EventId.
    Each nested Play/ShotAtGoal carries pressure, speed, xG, etc.
    """
    raw = _read_xml_from_s3(match_id, "kpi")
    rows = _get_kpi_rows(raw)

    index = {}
    for row in rows:
        _kind, payload = _kpi_payload(row)
        if not payload:
            continue

        event_id = _safe_str(payload.get("@EventId"))
        if not event_id:
            continue

        index[event_id] = {
            "pressure": _safe_float(
                payload.get("@PressureOnReceiver")
                or payload.get("@Pressure")
                or payload.get("PRESSURE")
            ),
            "player_speed": _safe_float(
                payload.get("@X-PlayerSpeed")
                or payload.get("@PlayerSpeed")
                or payload.get("PLAYER_SPEED")
            ),
            "xg": _safe_float(payload.get("@xG") or payload.get("xG")),
            "xpass": _safe_float(payload.get("@xPass") or payload.get("xPass")),
            "distance": _safe_float(payload.get("@Distance") or payload.get("DISTANCE")),
            "angle": _safe_float(payload.get("@Angle") or payload.get("ANGLE")),
            "distance_to_goal": _safe_float(
                payload.get("@DistanceToGoal") or payload.get("DistanceToGoal")
            ),
            "angle_to_goal": _safe_float(
                payload.get("@AngleToGoal") or payload.get("AngleToGoal")
            ),
            "amount_of_defenders": _safe_float(
                payload.get("@AmountOfDefenders") or payload.get("AmountOfDefenders")
            ),
            "shot_condition": _safe_str(
                payload.get("@ShotCondition") or payload.get("ShotCondition")
            ),
            "synced_event_time": _safe_str(payload.get("@SyncedEventTime")),
            "synced_frame_id": _safe_str(payload.get("@SyncedFrameId")),
        }
    return index


# ─────────────────────────────────────────────────────────────────────────────
# Public functions
# ─────────────────────────────────────────────────────────────────────────────

def get_match_timeline(match_id: str) -> list[dict]:
    """
    Return all key match events for the timeline view.
    Includes: goals, yellow/red cards, substitutions, fouls.
    """
    raw = _read_xml_from_s3(match_id, "events")
    events = _get_events(raw)

    timeline = []
    for event in events:
        event_type, event_data = _event_payload(event)

        if event_type not in {
            "SuccessfulShot", "Caution", "Substitution",
            "Foul", "OwnGoal", "FinalWhistle",
        }:
            continue

        entry = {
            "event_id":   event.get("@EventId"),
            "match_id":   event.get("@MatchId"),
            "event_time": event.get("@EventTime"),
            "type":       event_type,
        }

        if event_type == "SuccessfulShot":
            entry["player"] = event_data.get("@Assist") or event_data.get("@Player")
            entry["result"] = event_data.get("@CurrentResult")
            entry["goal_zone"] = event_data.get("@GoalZone")

        elif event_type == "Caution":
            entry["player"] = event_data.get("@Player")
            entry["team"] = event_data.get("@Team")
            entry["card_color"] = event_data.get("@CardColor")

        elif event_type == "Substitution":
            entry["player_out"] = event_data.get("@PlayerOut")
            entry["player_in"] = event_data.get("@PlayerIn")
            entry["team"] = event_data.get("@Team")

        elif event_type == "Foul":
            entry["fouler"] = event_data.get("@Fouler")
            entry["fouled"] = event_data.get("@Fouled")
            entry["team"] = event_data.get("@TeamFouler")

        timeline.append(entry)

    return timeline


def get_player_shots(match_id: str, player_id: str) -> list[dict]:
    """
    Return all shot events for a player with full metadata.
    Enriched with KPI data (xG, pressure, player speed).
    """
    raw = _read_xml_from_s3(match_id, "events")
    kpi = _build_kpi_index(match_id)
    events = _get_events(raw)

    shots = []
    for event in events:
        shot_data = event.get("ShotAtGoal")
        if not shot_data:
            continue
        if _safe_str(shot_data.get("@Player")) != player_id:
            continue

        event_id = event.get("@EventId")
        kpi_row = kpi.get(event_id, {})

        outcome = "other"
        if "SuccessfulShot" in shot_data:
            outcome = "goal"
        elif "SavedShot" in shot_data:
            outcome = "saved"
        elif "BlockedShot" in shot_data:
            outcome = "blocked"
        elif "ShotWide" in shot_data:
            outcome = "wide"
        elif "ShotWoodWork" in shot_data:
            outcome = "woodwork"

        shots.append({
            "event_id":       event_id,
            "event_time":     event.get("@EventTime"),
            "player_id":      player_id,
            "team":           shot_data.get("@Team"),
            "type_of_shot":   shot_data.get("@TypeOfShot"),
            "taker_setup":    shot_data.get("@TakerSetup"),
            "shot_origin":    shot_data.get("@ShotOrigin"),
            "inside_box":     shot_data.get("@InsideBox"),
            "after_freekick": shot_data.get("@AfterFreeKick"),
            "outcome":        outcome,
            "xg":             _safe_float(shot_data.get("@xG")) or kpi_row.get("xg"),
            "distance_to_goal": _safe_float(shot_data.get("@DistanceToGoal"))
            or kpi_row.get("distance_to_goal")
            or kpi_row.get("distance"),
            "angle_to_goal": _safe_float(shot_data.get("@AngleToGoal"))
            or kpi_row.get("angle_to_goal")
            or kpi_row.get("angle"),
            "pressure":       _safe_float(shot_data.get("@Pressure")) or kpi_row.get("pressure"),
            "player_speed":   _safe_float(shot_data.get("@PlayerSpeed")) or kpi_row.get("player_speed"),
            "amount_of_defenders": _safe_float(shot_data.get("@AmountOfDefenders"))
            or kpi_row.get("amount_of_defenders"),
            "shot_condition": _safe_str(shot_data.get("@ShotCondition")) or kpi_row.get("shot_condition"),
            # Backward-compatible aliases used in some frontend components
            "distance":       _safe_float(shot_data.get("@DistanceToGoal"))
            or kpi_row.get("distance_to_goal")
            or kpi_row.get("distance"),
            "angle":          _safe_float(shot_data.get("@AngleToGoal"))
            or kpi_row.get("angle_to_goal")
            or kpi_row.get("angle"),
            "frame_number":   None,
            "biomechanics":   None,
        })

    return shots


def _is_pass_play(play_data: dict) -> bool:
    """Events feed: Play is a pass when @IsPass is set or a Pass child exists."""
    if play_data.get("Pass"):
        return True
    if "@IsPass" in play_data:
        return _truthy(play_data.get("@IsPass"))
    # Events XML: Play entries without explicit flag are still pass actions
    return bool(play_data.get("@Player"))


def get_player_passes(match_id: str, player_id: str) -> list[dict]:
    """
    Return all pass events for a player.
    Enriched with xPass and pressure from KPI data.
    """
    raw = _read_xml_from_s3(match_id, "events")
    kpi = _build_kpi_index(match_id)
    events = _get_events(raw)

    passes = []
    for event in events:
        play_data = event.get("Play")
        if not play_data or not _is_pass_play(play_data):
            continue
        pass_data = play_data.get("Pass") if isinstance(play_data.get("Pass"), dict) else {}

        actor = _safe_str(
            play_data.get("@Player")
            or play_data.get("@PlayerId")
        )
        if actor != player_id:
            continue

        event_id = event.get("@EventId")
        kpi_row = kpi.get(event_id, {})

        passes.append({
            "event_id":     event_id,
            "event_time":   event.get("@EventTime"),
            "player_id":    player_id,
            "team":         play_data.get("@Team"),
            "recipient":    play_data.get("@Recipient") or play_data.get("@ReceiverId"),
            "evaluation":   play_data.get("@Evaluation"),
            "height":       play_data.get("@Height"),
            "distance":     play_data.get("@Distance") or kpi_row.get("distance"),
            "xpass":        kpi_row.get("xpass"),
            "pressure":     kpi_row.get("pressure"),
            "player_speed": kpi_row.get("player_speed"),
            "rotation":     play_data.get("@Rotation") or pass_data.get("@Rotation"),
            "frame_number": None,
            "biomechanics": None,
            "notable":      False,
        })

    return passes
