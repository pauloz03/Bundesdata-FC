"""
possession.py
─────────────
Ball possession and event detection from TRACAB tracking parquet.

Replaces the vendor event XML, which is no longer available. Passes,
turnovers and restarts are derived from ball kinematics plus player
pelvis positions rather than read from vendor annotations.

Main public functions:
    analyze_match(match_id)     → full result dict (events + possession share)
    load_or_compute(match_id)   → cached variant, writes JSON to disk
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Optional

import config
import db

log = logging.getLogger(__name__)


# ── Pitch geometry (from parquet file metadata: pitch_long/short minus padding) ──
PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M  = 67.9
_HALF_LENGTH   = PITCH_LENGTH_M / 2
_HALF_WIDTH    = PITCH_WIDTH_M / 2

# ── Tracking artifact rejection ──
# 0.24m between consecutive 50Hz frames = 12 m/s. Elite sprint peaks ~10 m/s,
# so this clips artifacts without touching real movement (0.008% of steps).
TELEPORT_MAX_STEP_M = 0.24

# ── Ball state thresholds ──
TRANSIT_SPEED_MS   = 6.0
TRANSIT_HEIGHT_M   = 1.5
CONTROL_SPEED_MS   = 3.0
CONTROL_DISTANCE_M = 1.5

# ── Possession assignment ──
POSSESSION_HOLD_FRAMES = 10    # 0.2s before committing a possessor
HYSTERESIS_MARGIN_M    = 0.3   # challenger must be this much closer to steal

# ── Release detection ──
TOUCH_DELTA_V_MS      = 4.0    # starting threshold, uncalibrated
RELEASE_LOOKBACK_FRAMES = 5
RELEASE_LOOKAHEAD_FRAMES = 10

STATE_DEAD       = "DEAD"
STATE_IN_TRANSIT = "IN_TRANSIT"
STATE_CONTROLLED = "CONTROLLED"


# ─────────────────────────────────────────────────────────────────────────────
# Frame loading
# ─────────────────────────────────────────────────────────────────────────────

def _phases(meta: dict) -> list[tuple[int, int]]:
    """Valid (start, end) frame ranges for the match, ignoring unused phases."""
    out = []
    for n in (1, 2, 3, 4, 5):
        start = meta.get(f"phase_{n}_start") or 0
        end   = meta.get(f"phase_{n}_end") or 0
        if start and end and end > start:
            out.append((int(start), int(end)))
    return out


def _phase_sql(phases: list[tuple[int, int]], column: str = "frame_number") -> str:
    clauses = [f"{column} BETWEEN {s} AND {e}" for s, e in phases]
    return "(" + " OR ".join(clauses) + ")" if clauses else "TRUE"


def _load_frames(match_id: str, meta: dict) -> list[tuple]:
    """
    One row per frame inside a match phase:
        (frame, bx, by, bz, vx, vy, vz, team_1, jersey_1, dist_1, dist_2)

    Teleport artifacts are rejected inside the query, before any distance is
    computed, so a corrupted position can never win the nearest-player rank.
    """
    parquet, _ = db.read_parquet_sql(match_id)
    phases = _phases(meta)
    where_frames = _phase_sql(phases, "p.frame_number")
    where_ball   = _phase_sql(phases, "frame_number")

    query = f"""
    WITH pelvis AS (
        SELECT
            p.frame_number AS fn,
            s.team         AS tm,
            s.jersey_number AS jn,
            j.position_x   AS px,
            j.position_y   AS py
        FROM read_parquet('{parquet}') AS p,
             UNNEST(p.skeletons) AS a(s),
             UNNEST(s.parts)     AS b(j)
        WHERE j.name = 12
          AND s.jersey_number <> -1
          AND s.team <> 3
          AND {where_frames}
    ),
    stepped AS (
        SELECT fn, tm, jn, px, py,
               sqrt(pow(px - lag(px) OVER w, 2) + pow(py - lag(py) OVER w, 2)) AS step,
               fn - lag(fn) OVER w AS gap
        FROM pelvis
        WINDOW w AS (PARTITION BY tm, jn ORDER BY fn)
    ),
    valid AS (
        SELECT fn, tm, jn, px, py
        FROM stepped
        WHERE step IS NULL OR gap <> 1 OR step <= {TELEPORT_MAX_STEP_M}
    ),
    ballpos AS (
        SELECT frame_number AS fn,
               ball.position_x AS bx, ball.position_y AS byy, ball.position_z AS bz,
               ball.velocity_x AS vx, ball.velocity_y AS vy, ball.velocity_z AS vz
        FROM read_parquet('{parquet}')
        WHERE {where_ball}
    ),
    ranked AS (
        SELECT v.fn, v.tm, v.jn,
               sqrt(pow(v.px - b.bx, 2) + pow(v.py - b.byy, 2)) AS dist,
               row_number() OVER (
                   PARTITION BY v.fn
                   ORDER BY sqrt(pow(v.px - b.bx, 2) + pow(v.py - b.byy, 2))
               ) AS rk
        FROM valid v
        JOIN ballpos b USING (fn)
    )
    SELECT b.fn, b.bx, b.byy, b.bz, b.vx, b.vy, b.vz,
           max(CASE WHEN r.rk = 1 THEN r.tm END)   AS t1,
           max(CASE WHEN r.rk = 1 THEN r.jn END)   AS j1,
           max(CASE WHEN r.rk = 1 THEN r.dist END) AS d1,
           max(CASE WHEN r.rk = 2 THEN r.dist END) AS d2
    FROM ballpos b
    LEFT JOIN ranked r ON r.fn = b.fn AND r.rk <= 2
    GROUP BY b.fn, b.bx, b.byy, b.bz, b.vx, b.vy, b.vz
    ORDER BY b.fn
    """

    con = db.get_connection()
    try:
        return con.execute(query).fetchall()
    finally:
        con.close()


# ─────────────────────────────────────────────────────────────────────────────
# Ball state
# ─────────────────────────────────────────────────────────────────────────────

def _in_bounds(x: float, y: float) -> bool:
    return abs(x) <= _HALF_LENGTH and abs(y) <= _HALF_WIDTH


def _ball_state(speed: float, height: float, nearest: Optional[float],
                previous: str) -> str:
    """
    Three-state classifier. The thresholds leave a deliberate gap
    (3–6 m/s) where neither rule fires; there we hold the previous state,
    which doubles as hysteresis on the ball phase itself.
    """
    if speed > TRANSIT_SPEED_MS or height > TRANSIT_HEIGHT_M:
        return STATE_IN_TRANSIT
    if speed < CONTROL_SPEED_MS and nearest is not None and nearest < CONTROL_DISTANCE_M:
        return STATE_CONTROLLED
    return previous


def _frame_to_minute(frame: int, meta: dict) -> Optional[float]:
    fr = meta.get("framerate", 50) or 50
    if meta["phase_1_start"] <= frame <= meta["phase_1_end"]:
        return round((frame - meta["phase_1_start"]) / fr / 60, 2)
    if meta["phase_2_start"] <= frame <= meta["phase_2_end"]:
        return round(45 + (frame - meta["phase_2_start"]) / fr / 60, 2)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Core analysis
# ─────────────────────────────────────────────────────────────────────────────

def _confidence(margin: Optional[float], hold_frames: int,
                delta_v: Optional[float]) -> float:
    """
    Blend of how uncontested the assignment was, how long the player held
    the ball, and how clean the release spike was. Each term is clamped to
    [0, 1] before weighting.
    """
    margin_score = min(max((margin or 0.0) / 1.0, 0.0), 1.0)
    hold_score   = min(max(hold_frames / 25.0, 0.0), 1.0)
    release_score = min(max((delta_v or 0.0) / 8.0, 0.0), 1.0)
    return round(0.4 * margin_score + 0.3 * hold_score + 0.3 * release_score, 3)


def analyze_match(match_id: str) -> dict[str, Any]:
    meta = config.MATCH_METADATA.get(match_id)
    if not meta:
        raise ValueError(f"No metadata registered for match '{match_id}'")

    framerate = meta.get("framerate", 50) or 50
    rows = _load_frames(match_id, meta)
    if not rows:
        return {
            "match_id": match_id,
            "events": [],
            "possession": _empty_possession(),
            "unverified": True,
        }

    state = STATE_DEAD
    holder: Optional[tuple[int, int]] = None
    holder_since = 0
    holder_margin: Optional[float] = None

    candidate: Optional[tuple[int, int]] = None
    candidate_count = 0

    # Completed possession spells: (team, jersey, start_frame, end_frame, margin)
    segments: list[tuple[int, int, int, int, Optional[float]]] = []
    # Whether the ball went dead before each segment — splits restarts from passes.
    dead_before_segment: list[bool] = []
    saw_dead_since_segment = False

    delta_v_by_frame: dict[int, float] = {}
    state_counts = {STATE_DEAD: 0, STATE_IN_TRANSIT: 0, STATE_CONTROLLED: 0}
    controlled_frames_by_team: dict[int, int] = {}

    prev_frame = None
    prev_vel: Optional[tuple[float, float, float]] = None

    def close_segment(end_frame: int) -> None:
        nonlocal holder, holder_since, holder_margin, saw_dead_since_segment
        if holder is not None and end_frame >= holder_since:
            segments.append(
                (holder[0], holder[1], holder_since, end_frame, holder_margin)
            )
            dead_before_segment.append(saw_dead_since_segment)
            saw_dead_since_segment = False
        holder = None
        holder_margin = None

    for fn, bx, byy, bz, vx, vy, vz, t1, j1, d1, d2 in rows:
        speed = math.sqrt(vx * vx + vy * vy + vz * vz)

        if prev_vel is not None and prev_frame is not None and fn - prev_frame == 1:
            dv = math.sqrt(
                (vx - prev_vel[0]) ** 2
                + (vy - prev_vel[1]) ** 2
                + (vz - prev_vel[2]) ** 2
            )
            delta_v_by_frame[fn] = dv
        prev_vel = (vx, vy, vz)
        prev_frame = fn

        if not _in_bounds(bx, byy):
            new_state = STATE_DEAD
        else:
            new_state = _ball_state(speed, bz, d1, state)
            if new_state == STATE_DEAD:
                # Ball is back inside the pitch; wait for a real classification.
                new_state = STATE_IN_TRANSIT

        if new_state != STATE_CONTROLLED and state == STATE_CONTROLLED:
            close_segment(fn - 1)
            candidate = None
            candidate_count = 0

        if new_state == STATE_DEAD:
            saw_dead_since_segment = True

        state = new_state
        state_counts[state] += 1

        if state != STATE_CONTROLLED:
            continue

        if t1 is None or d1 is None:
            continue

        nearest = (int(t1), int(j1))
        margin = (d2 - d1) if d2 is not None else None

        if holder is None:
            if nearest == candidate:
                candidate_count += 1
            else:
                candidate = nearest
                candidate_count = 1
            if candidate_count >= POSSESSION_HOLD_FRAMES:
                holder = candidate
                holder_since = fn - candidate_count + 1
                holder_margin = margin
                candidate = None
                candidate_count = 0
        else:
            if nearest == holder:
                candidate = None
                candidate_count = 0
            else:
                # Challenger must be clearly closer, for a sustained window.
                # If the holder has slipped past second place the margin
                # understates the gap, which only makes stealing harder.
                challenger_closer = margin is not None and margin >= HYSTERESIS_MARGIN_M
                if challenger_closer and nearest == candidate:
                    candidate_count += 1
                elif challenger_closer:
                    candidate = nearest
                    candidate_count = 1
                else:
                    candidate = None
                    candidate_count = 0

                if candidate_count >= POSSESSION_HOLD_FRAMES:
                    close_segment(fn - candidate_count)
                    holder = candidate
                    holder_since = fn - candidate_count + 1
                    holder_margin = margin
                    candidate = None
                    candidate_count = 0

        if holder is not None:
            controlled_frames_by_team[holder[0]] = (
                controlled_frames_by_team.get(holder[0], 0) + 1
            )

    close_segment(rows[-1][0])

    events = _build_events(segments, dead_before_segment, delta_v_by_frame, meta)
    possession = _possession_share(controlled_frames_by_team, state_counts, framerate, meta)

    return {
        "match_id": match_id,
        "framerate": framerate,
        "events": events,
        "possession": possession,
        # No vendor XML or video exists to validate against, so per-event
        # correctness is unverified. Confidence scores are relative only.
        "unverified": True,
    }


def _refine_release(boundary: int, delta_v_by_frame: dict[int, float]) -> tuple[int, Optional[float]]:
    """
    Sharpen the release frame using the ball's velocity-change spike near the
    CONTROLLED→IN_TRANSIT boundary. Falls back to the boundary itself when no
    spike clears the touch threshold.
    """
    best_frame = boundary
    best_dv = None
    for f in range(boundary - RELEASE_LOOKBACK_FRAMES, boundary + RELEASE_LOOKAHEAD_FRAMES + 1):
        dv = delta_v_by_frame.get(f)
        if dv is None:
            continue
        if best_dv is None or dv > best_dv:
            best_dv = dv
            best_frame = f
    if best_dv is not None and best_dv >= TOUCH_DELTA_V_MS:
        return best_frame, best_dv
    return boundary, best_dv


def _build_events(segments, dead_flags, delta_v_by_frame, meta) -> list[dict]:
    events: list[dict] = []
    for i in range(len(segments)):
        team, jersey, start, end, margin = segments[i]
        had_dead = dead_flags[i] if i < len(dead_flags) else False

        if had_dead:
            events.append({
                "frame_number": start,
                "minute": _frame_to_minute(start, meta),
                "event_type": "restart",
                "team_from": None,
                "team_to": team,
                "jersey_from": None,
                "jersey_to": jersey,
                "release_frame": start,
                "confidence_score": _confidence(margin, end - start + 1, None),
            })
            continue

        if i == 0:
            continue

        prev_team, prev_jersey, prev_start, prev_end, prev_margin = segments[i - 1]
        release_frame, delta_v = _refine_release(prev_end, delta_v_by_frame)
        hold_frames = prev_end - prev_start + 1

        if prev_team == team and prev_jersey == jersey:
            # Same player regained control without anyone else intervening.
            continue

        event_type = "pass" if prev_team == team else "turnover"
        events.append({
            "frame_number": prev_end,
            "minute": _frame_to_minute(prev_end, meta),
            "event_type": event_type,
            "team_from": prev_team,
            "team_to": team,
            "jersey_from": prev_jersey,
            "jersey_to": jersey,
            "release_frame": release_frame,
            "release_delta_v": round(delta_v, 2) if delta_v is not None else None,
            "confidence_score": _confidence(prev_margin, hold_frames, delta_v),
        })
    return events


def _empty_possession() -> dict:
    return {
        "home_frames": 0, "away_frames": 0,
        "home_pct": 0.0, "away_pct": 0.0,
        "home_seconds": 0.0, "away_seconds": 0.0,
        "controlled_frames": 0, "in_transit_frames": 0, "dead_frames": 0,
    }


def _possession_share(by_team: dict[int, int], state_counts: dict[str, int],
                      framerate: float, meta: dict) -> dict:
    """
    Share of time each team spent in direct control of the ball.

    DEAD and IN_TRANSIT frames are excluded from the denominator, so this is
    time-in-control rather than broadcast-style possession (which credits
    ball-flight time to the passing team). The two will not match.
    """
    home_flag = meta.get("home_team_flag", 1)
    away_flag = meta.get("away_team_flag", 0)

    home = by_team.get(home_flag, 0)
    away = by_team.get(away_flag, 0)
    total = home + away

    return {
        "home_frames": home,
        "away_frames": away,
        "home_pct": round(100.0 * home / total, 1) if total else 0.0,
        "away_pct": round(100.0 * away / total, 1) if total else 0.0,
        "home_seconds": round(home / framerate, 1),
        "away_seconds": round(away / framerate, 1),
        "controlled_frames": state_counts.get(STATE_CONTROLLED, 0),
        "in_transit_frames": state_counts.get(STATE_IN_TRANSIT, 0),
        "dead_frames": state_counts.get(STATE_DEAD, 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Local JSON cache
# ─────────────────────────────────────────────────────────────────────────────

def cache_path(match_id: str) -> Path:
    return config.LOCAL_PRECOMPUTED_DIR / match_id / "possession.json"


def save(match_id: str, data: dict) -> Path:
    path = cache_path(match_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def load(match_id: str) -> Optional[dict]:
    path = cache_path(match_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Ignoring unreadable possession cache %s: %s", path, exc)
        return None


def load_or_compute(match_id: str, *, recompute: bool = False) -> dict:
    if not recompute:
        cached = load(match_id)
        if cached:
            return cached
    data = analyze_match(match_id)
    save(match_id, data)
    return data
