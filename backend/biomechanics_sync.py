"""
biomechanics_sync.py
────────────────────
Connects skeleton data to match events.

- Maps event timestamps → Parquet frame numbers (accounts for halftime gap in recording).
- Enriches all shots with per-event biomechanics.
- Enriches passes, returns only notable ones (stride + lean rules, episode-gated lean).
- Builds degradation episodes on the fatigue curve for the timeline UI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import config
import event_parser
import fatigue_episodes
import skeleton_parser


_kickoff_cache: dict[str, datetime] = {}


def _get_kickoff_time(match_id: str) -> Optional[datetime]:
    """Match kickoff from KPI AdvancedEvents or match_info (cached)."""
    if match_id in _kickoff_cache:
        return _kickoff_cache[match_id]

    kickoff_str = event_parser.get_kickoff_time_str(match_id)
    if kickoff_str:
        try:
            dt = datetime.fromisoformat(kickoff_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            _kickoff_cache[match_id] = dt
            return dt
        except (ValueError, TypeError):
            pass
    return None


def _wall_offset_to_playing_seconds(offset_seconds: float, meta: dict) -> Optional[float]:
    """
    Map wall-clock seconds since kickoff to match playing-time seconds,
    using phase frame boundaries (halftime gap in the recording).
    """
    framerate = meta["framerate"]
    first_half_play_sec = (meta["phase_1_end"] - meta["phase_1_start"]) / framerate
    recording_ht_gap_sec = (meta["phase_2_start"] - meta["phase_1_end"]) / framerate
    second_half_play_sec = (meta["phase_2_end"] - meta["phase_2_start"]) / framerate

    if offset_seconds < 0:
        return None
    if offset_seconds <= first_half_play_sec:
        return offset_seconds
    if offset_seconds < first_half_play_sec + recording_ht_gap_sec:
        return None  # halftime in recording
    second_half_elapsed = offset_seconds - first_half_play_sec - recording_ht_gap_sec
    if second_half_elapsed > second_half_play_sec:
        return None
    return first_half_play_sec + second_half_elapsed


def _playing_seconds_to_frame(playing_seconds: float, meta: dict) -> int:
    framerate = meta["framerate"]
    first_half_play_sec = (meta["phase_1_end"] - meta["phase_1_start"]) / framerate
    if playing_seconds <= first_half_play_sec:
        return meta["phase_1_start"] + int(playing_seconds * framerate)
    second_half_play = playing_seconds - first_half_play_sec
    return meta["phase_2_start"] + int(second_half_play * framerate)


def _playing_seconds_to_minute(playing_seconds: float) -> float:
    if playing_seconds <= 45 * 60:
        return playing_seconds / 60.0
    return 45.0 + (playing_seconds - 45 * 60) / 60.0


def event_time_to_frame(event_time_str: str, match_id: str) -> Optional[int]:
    """ISO8601 event time → nearest skeleton frame number."""
    meta = config.MATCH_METADATA.get(match_id)
    if not meta or not event_time_str:
        return None

    kickoff_dt = _get_kickoff_time(match_id)
    if not kickoff_dt:
        return None

    try:
        event_dt = datetime.fromisoformat(event_time_str)
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        offset_seconds = (event_dt - kickoff_dt).total_seconds()
        playing_seconds = _wall_offset_to_playing_seconds(offset_seconds, meta)
        if playing_seconds is None:
            return None
        return _playing_seconds_to_frame(playing_seconds, meta)
    except (ValueError, TypeError):
        return None


def event_time_to_minute(event_time_str: str, match_id: str) -> Optional[float]:
    """ISO8601 event time → match minute (0–90+)."""
    meta = config.MATCH_METADATA.get(match_id)
    if not meta or not event_time_str:
        return None

    kickoff_dt = _get_kickoff_time(match_id)
    if not kickoff_dt:
        return None

    try:
        event_dt = datetime.fromisoformat(event_time_str)
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        offset_seconds = (event_dt - kickoff_dt).total_seconds()
        playing_seconds = _wall_offset_to_playing_seconds(offset_seconds, meta)
        if playing_seconds is None:
            return None
        return round(_playing_seconds_to_minute(playing_seconds), 2)
    except (ValueError, TypeError):
        return None


def _evaluate_notable_pass(
    lean_delta: Optional[float],
    stride_delta: Optional[float],
    minute: Optional[float],
    episodes: list[dict],
) -> tuple[bool, list[str]]:
    """
    Notable when stride differs materially from kickoff baseline AND
    (lean is elevated OR the pass falls in a sustained degradation episode).

    Lean-only spikes outside episodes are ignored (quick movements).
    """
    reasons: list[str] = []
    stride_notable = (
        stride_delta is not None
        and abs(stride_delta) >= config.PASS_STRIDE_DELTA_THRESHOLD
    )
    lean_notable = (
        lean_delta is not None
        and lean_delta >= config.PASS_LEAN_DELTA_THRESHOLD
    )
    in_episode = fatigue_episodes.minute_in_episode(minute, episodes)

    if stride_notable:
        reasons.append("stride_delta")
    if lean_notable and in_episode:
        reasons.append("lean_delta_in_episode")
    elif lean_notable and not config.PASS_REQUIRE_EPISODE_FOR_LEAN_ONLY:
        reasons.append("lean_delta")
    if in_episode and stride_notable:
        reasons.append("in_degradation_episode")

    if stride_notable and (lean_notable or in_episode):
        return True, reasons
    if stride_notable and lean_notable:
        return True, reasons
    return False, reasons


def enrich_shots(
    match_id: str,
    jersey: int,
    team_flag: int,
    shots: list[dict],
) -> list[dict]:
    """All shots with frame_number, minute, and biomechanics."""
    enriched = []
    for shot in shots:
        event_time = shot.get("event_time", "")
        frame = event_time_to_frame(event_time, match_id)
        shot["frame_number"] = frame
        shot["minute"] = event_time_to_minute(event_time, match_id)

        if frame is not None:
            shot["biomechanics"] = skeleton_parser.get_frame_biomechanics(
                match_id, jersey, team_flag, frame
            )
        else:
            shot["biomechanics"] = None

        enriched.append(shot)
    return enriched


def enrich_passes(
    match_id: str,
    jersey: int,
    team_flag: int,
    passes: list[dict],
    fatigue_baseline: dict,
    episodes: list[dict],
) -> tuple[list[dict], dict]:
    """
    Compute biomechanics for every pass; return only notable passes plus summary.
    """
    baseline_lean = fatigue_baseline.get("lean", 0.0)
    baseline_stride = fatigue_baseline.get("stride", 0.0)

    notable_passes: list[dict] = []
    total = 0

    for pass_event in passes:
        total += 1
        event_time = pass_event.get("event_time", "")
        frame = event_time_to_frame(event_time, match_id)
        minute = event_time_to_minute(event_time, match_id)
        pass_event["frame_number"] = frame
        pass_event["minute"] = minute

        lean_delta = None
        stride_delta = None

        if frame is not None:
            bio = skeleton_parser.get_frame_biomechanics(
                match_id, jersey, team_flag, frame
            )
            pass_event["biomechanics"] = bio
            if bio:
                if bio.get("trunk_lean") is not None:
                    lean_delta = round(bio["trunk_lean"] - baseline_lean, 3)
                if bio.get("stride_length") is not None and baseline_stride:
                    stride_delta = round(bio["stride_length"] - baseline_stride, 3)
        else:
            pass_event["biomechanics"] = None

        pass_event["deltas"] = {
            "lean":   lean_delta,
            "stride": stride_delta,
        }

        is_notable, reasons = _evaluate_notable_pass(
            lean_delta, stride_delta, minute, episodes
        )
        pass_event["notable"] = is_notable
        pass_event["notable_reasons"] = reasons
        pass_event["in_episode"] = fatigue_episodes.minute_in_episode(minute, episodes)

        if is_notable:
            notable_passes.append(pass_event)

    summary = {
        "total_passes":   total,
        "notable_count":  len(notable_passes),
    }
    return notable_passes, summary


def get_player_event_biomechanics(
    match_id: str,
    player_id: str,
    jersey: int,
    team_flag: int,
) -> dict:
    """
    Full pipeline for one player.

    Returns fatigue curve, degradation episodes (timeline bands),
    all shots with biomechanics, and notable passes only.
    """
    fatigue = skeleton_parser.get_fatigue_curve(match_id, jersey, team_flag)
    if "error" in fatigue:
        return {"error": fatigue["error"]}

    curve = fatigue.get("curve", [])
    baseline = fatigue.get("baseline", {})
    episodes = fatigue_episodes.detect_degradation_episodes(curve)

    shots = event_parser.get_player_shots(match_id, player_id)
    passes = event_parser.get_player_passes(match_id, player_id)

    # Compute event → frame/minute once, then batch-fetch biomechanics.
    frames_needed: set[int] = set()

    for shot in shots:
        event_time = shot.get("event_time", "")
        frame = event_time_to_frame(event_time, match_id)
        minute = event_time_to_minute(event_time, match_id)
        shot["frame_number"] = frame
        shot["minute"] = minute
        shot["biomechanics"] = None
        if frame is not None:
            frames_needed.add(frame)

    for pass_event in passes:
        event_time = pass_event.get("event_time", "")
        frame = event_time_to_frame(event_time, match_id)
        minute = event_time_to_minute(event_time, match_id)
        pass_event["frame_number"] = frame
        pass_event["minute"] = minute
        pass_event["biomechanics"] = None
        if frame is not None:
            frames_needed.add(frame)

    bio_by_frame = skeleton_parser.get_frames_biomechanics(
        match_id=match_id,
        jersey=jersey,
        team_flag=team_flag,
        frame_numbers=list(frames_needed),
    )

    # Attach biomechanics to shots
    for shot in shots:
        frame = shot.get("frame_number")
        if frame is not None:
            shot["biomechanics"] = bio_by_frame.get(frame)

    # Attach biomechanics + deltas to passes, then filter notable.
    baseline_lean = baseline.get("lean", 0.0)
    baseline_stride = baseline.get("stride", 0.0)

    notable_passes: list[dict] = []
    total = 0

    for pass_event in passes:
        total += 1
        frame = pass_event.get("frame_number")
        minute = pass_event.get("minute")

        lean_delta = None
        stride_delta = None

        if frame is not None:
            bio = bio_by_frame.get(frame)
            pass_event["biomechanics"] = bio
            if bio:
                if bio.get("trunk_lean") is not None:
                    lean_delta = round(bio["trunk_lean"] - baseline_lean, 3)
                if bio.get("stride_length") is not None and baseline_stride:
                    stride_delta = round(
                        bio["stride_length"] - baseline_stride, 3
                    )
        else:
            pass_event["biomechanics"] = None

        pass_event["deltas"] = {
            "lean": lean_delta,
            "stride": stride_delta,
        }

        is_notable, reasons = _evaluate_notable_pass(
            lean_delta, stride_delta, minute, episodes
        )
        pass_event["notable"] = is_notable
        pass_event["notable_reasons"] = reasons
        pass_event["in_episode"] = fatigue_episodes.minute_in_episode(
            minute, episodes
        )

        if is_notable:
            notable_passes.append(pass_event)

    passes_summary = {"total_passes": total, "notable_count": len(notable_passes)}

    return {
        "player": fatigue.get("player"),
        "fatigue": {
            "baseline": baseline,
            "curve":    curve,
            "summary":  fatigue.get("summary"),
        },
        "degradation_episodes": episodes,
        "shots":                shots,
        "passes":               notable_passes,
        "passes_summary":       passes_summary,
    }
