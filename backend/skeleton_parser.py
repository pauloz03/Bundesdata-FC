from __future__ import annotations

"""
skeleton_parser.py
──────────────────
Reads TRACAB GEN5 Parquet skeleton files from S3 using DuckDB.
Returns clean structured data for the fatigue curve and player baseline.

Main public functions:
    get_player_list(match_id)
    get_fatigue_curve(match_id, jersey, team_flag)
"""

import math
import statistics
from typing import Optional

import config
import db


def _frame_to_minute(frame: int, meta: dict) -> Optional[float]:
    """Convert absolute frame number to match minute."""
    if meta["phase_1_start"] <= frame <= meta["phase_1_end"]:
        return (frame - meta["phase_1_start"]) / meta["framerate"] / 60
    elif meta["phase_2_start"] <= frame <= meta["phase_2_end"]:
        return 45 + (frame - meta["phase_2_start"]) / meta["framerate"] / 60
    return None


def _trunk_lean_angle(joints: dict) -> Optional[float]:
    """
    Angle (degrees) of the neck→pelvis vector from vertical Z axis.
    0° = perfectly upright. Higher = more forward/sideways lean.
    """
    neck   = joints.get(5)   # neck
    pelvis = joints.get(12)  # pelvis
    if not neck or not pelvis:
        return None
    dx = neck[0] - pelvis[0]
    dy = neck[1] - pelvis[1]
    dz = neck[2] - pelvis[2]
    horizontal = math.sqrt(dx**2 + dy**2)
    vertical   = abs(dz) if abs(dz) > 0.001 else 0.001
    return round(math.degrees(math.atan2(horizontal, vertical)), 3)


def _stride_length(joints: dict) -> Optional[float]:
    """Euclidean XY distance between left and right ankle."""
    l = joints.get(16)  # l_ankle
    r = joints.get(17)  # r_ankle
    if not l or not r:
        return None
    return round(math.sqrt((l[0]-r[0])**2 + (l[1]-r[1])**2), 3)


def _shoulder_asymmetry(joints: dict) -> Optional[float]:
    """Z-axis height difference between left and right shoulder."""
    l = joints.get(4)   # l_shoulder
    r = joints.get(6)   # r_shoulder
    if not l or not r:
        return None
    return round(abs(l[2] - r[2]), 4)


def _knee_bend_angle(joints: dict, side: str = "right") -> Optional[float]:
    """
    Angle at the knee joint (hip → knee → ankle).
    180° = fully straight leg. Lower = more bent.
    side: "right" or "left"
    """
    if side == "right":
        hip, knee, ankle = joints.get(13), joints.get(15), joints.get(17)
    else:
        hip, knee, ankle = joints.get(11), joints.get(14), joints.get(16)

    if not hip or not knee or not ankle:
        return None

    # Vector knee→hip and knee→ankle
    v1 = (hip[0]-knee[0],   hip[1]-knee[1],   hip[2]-knee[2])
    v2 = (ankle[0]-knee[0], ankle[1]-knee[1], ankle[2]-knee[2])

    dot = sum(a*b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a**2 for a in v1))
    mag2 = math.sqrt(sum(a**2 for a in v2))

    if mag1 == 0 or mag2 == 0:
        return None

    cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return round(math.degrees(math.acos(cos_angle)), 2)


def _parse_parts(parts) -> dict:
    """Convert DuckDB parts array → {joint_id: (x, y, z)}."""
    joints = {}
    for part in parts:
        if isinstance(part, dict):
            jid = part.get("name")
            x, y, z = part.get("position_x"), part.get("position_y"), part.get("position_z")
        else:
            jid, x, y, z = part[0], part[1], part[2], part[3]
        if jid is not None and x is not None:
            joints[int(jid)] = (float(x), float(y), float(z))
    return joints


def _fatigue_signal(delta: float) -> str:
    if delta > config.FATIGUE_HIGH_THRESHOLD:     return "high"
    if delta > config.FATIGUE_MODERATE_THRESHOLD: return "moderate"
    if delta > config.FATIGUE_MILD_THRESHOLD:     return "mild"
    return "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Public functions
# ─────────────────────────────────────────────────────────────────────────────

def get_player_list(match_id: str) -> list[dict]:
    """
    Return all real players (non-referee) found in the first half of the match.
    Each entry: {jersey, team_flag, side, frames_seen}
    """
    meta       = config.MATCH_METADATA[match_id]
    parquet, use_s3 = db.read_parquet_sql(match_id)
    con        = db.get_connection(use_s3=use_s3)

    query = f"""
        SELECT
            sk.jersey_number AS jersey,
            sk.team          AS team_flag,
            COUNT(*)         AS frames_seen
        FROM read_parquet('{parquet}') AS p,
        UNNEST(p.skeletons) AS t(sk)
        WHERE
            p.frame_number BETWEEN {meta['phase_1_start']} AND {meta['phase_1_end']}
            AND sk.jersey_number != -1
            AND sk.team != {config.REF_FLAG}
        GROUP BY sk.jersey_number, sk.team
        ORDER BY sk.team, sk.jersey_number
    """

    rows = con.execute(query).fetchall()
    con.close()

    return [
        {
            "jersey":      int(r[0]),
            "team_flag":   int(r[1]),
            "side":        "home" if int(r[1]) == config.HOME_TEAM_FLAG else "away",
            "frames_seen": int(r[2]),
        }
        for r in rows
    ]


def get_fatigue_curve(match_id: str, jersey: int, team_flag: int) -> dict:
    """
    Build the full 90-minute fatigue curve for a player.

    Returns:
    {
        "player":   {jersey, team_flag, side},
        "baseline": {lean, stride, shoulder_asymmetry},
        "curve":    [{minute, frame, lean, stride, asym, lean_delta, stride_delta, signal}],
        "summary":  {drift_lean, drift_stride_pct, final_signal}
    }
    """
    meta    = config.MATCH_METADATA[match_id]
    parquet, use_s3 = db.read_parquet_sql(match_id)
    con     = db.get_connection(use_s3=use_s3)

    query = f"""
        SELECT
            p.frame_number,
            sk.parts
        FROM read_parquet('{parquet}') AS p,
        UNNEST(p.skeletons) AS t(sk)
        WHERE
            (
                p.frame_number BETWEEN {meta['phase_1_start']} AND {meta['phase_1_end']}
                OR
                p.frame_number BETWEEN {meta['phase_2_start']} AND {meta['phase_2_end']}
            )
            AND sk.jersey_number = {jersey}
            AND sk.team = {team_flag}
        ORDER BY p.frame_number
    """

    rows = con.execute(query).fetchall()
    con.close()

    if not rows:
        return {"error": f"No data found for jersey #{jersey} team {team_flag}"}

    # Sample every N frames
    sampled = rows[::config.FATIGUE_SAMPLE_EVERY_N_FRAMES]

    # Compute metrics for each sampled frame
    samples = []
    for frame_num, parts in sampled:
        minute = _frame_to_minute(frame_num, meta)
        if minute is None:
            continue
        joints = _parse_parts(parts)
        lean   = _trunk_lean_angle(joints)
        stride = _stride_length(joints)
        asym   = _shoulder_asymmetry(joints)
        if lean is not None:
            samples.append({
                "frame":  int(frame_num),
                "minute": round(minute, 2),
                "lean":   lean,
                "stride": stride,
                "asym":   asym,
            })

    if not samples:
        return {"error": "Could not compute metrics from frames"}

    # Baseline from first N samples at kickoff
    n = min(config.BASELINE_SAMPLE_COUNT, len(samples))
    baseline_lean   = statistics.mean(s["lean"]   for s in samples[:n])
    stride_vals     = [s["stride"] for s in samples[:n] if s["stride"]]
    baseline_stride = statistics.mean(stride_vals) if stride_vals else 0.0
    asym_vals       = [s["asym"] for s in samples[:n] if s["asym"]]
    baseline_asym   = statistics.mean(asym_vals) if asym_vals else 0.0

    # Build curve with deltas and signals
    curve = []
    for s in samples:
        delta_lean = s["lean"] - baseline_lean
        stride_delta = (
            round(s["stride"] - baseline_stride, 3)
            if s["stride"] and baseline_stride
            else None
        )
        curve.append({
            **s,
            "lean_delta":   round(delta_lean, 3),
            "stride_delta": stride_delta,
            "signal":       _fatigue_signal(delta_lean),
        })

    # Summary
    final        = samples[-1]
    drift_lean   = final["lean"] - baseline_lean
    drift_stride = ((final["stride"] - baseline_stride) / baseline_stride * 100
                    if final["stride"] else None)

    return {
        "player": {
            "jersey":    jersey,
            "team_flag": team_flag,
            "side":      "home" if team_flag == config.HOME_TEAM_FLAG else "away",
        },
        "baseline": {
            "lean":               round(baseline_lean, 3),
            "stride":             round(baseline_stride, 3),
            "shoulder_asymmetry": round(baseline_asym, 4),
        },
        "curve":   curve,
        "summary": {
            "drift_lean":        round(drift_lean, 3),
            "drift_stride_pct":  round(drift_stride, 1) if drift_stride else None,
            "final_signal":      _fatigue_signal(drift_lean),
            "total_samples":     len(curve),
        },
    }


def get_frame_biomechanics(match_id: str, jersey: int,
                           team_flag: int, frame_number: int) -> dict:
    """
    Return full biomechanical snapshot for a player at a specific frame.
    Used by biomechanics_sync.py to enrich shot and pass events.
    """
    parquet, use_s3 = db.read_parquet_sql(match_id)
    con     = db.get_connection(use_s3=use_s3)

    query = f"""
        SELECT sk.parts
        FROM read_parquet('{parquet}') AS p,
        UNNEST(p.skeletons) AS t(sk)
        WHERE
            p.frame_number = {frame_number}
            AND sk.jersey_number = {jersey}
            AND sk.team = {team_flag}
        LIMIT 1
    """

    rows = con.execute(query).fetchall()
    con.close()

    if not rows:
        return {}

    joints = _parse_parts(rows[0][0])

    return {
        "trunk_lean":          _trunk_lean_angle(joints),
        "stride_length":       _stride_length(joints),
        "shoulder_asymmetry":  _shoulder_asymmetry(joints),
        "knee_bend_right":     _knee_bend_angle(joints, "right"),
        "knee_bend_left":      _knee_bend_angle(joints, "left"),
    }


def get_frames_biomechanics(
    match_id: str,
    jersey: int,
    team_flag: int,
    frame_numbers: list[int],
) -> dict[int, dict]:
    """
    Batch biomechanical lookup.

    Returns a mapping:
      { frame_number: {trunk_lean, stride_length, shoulder_asymmetry, ...} }

    This reuses a single DuckDB connection, avoiding one Parquet query per event.
    """
    unique_frames = sorted({int(f) for f in frame_numbers if f is not None})
    if not unique_frames:
        return {}

    parquet, use_s3 = db.read_parquet_sql(match_id)
    con = db.get_connection(use_s3=use_s3)

    frames_csv = ", ".join(str(f) for f in unique_frames)

    query = f"""
        SELECT
            p.frame_number AS frame_number,
            sk.parts AS parts
        FROM read_parquet('{parquet}') AS p,
        UNNEST(p.skeletons) AS t(sk)
        WHERE
            p.frame_number IN ({frames_csv})
            AND sk.jersey_number = {jersey}
            AND sk.team = {team_flag}
        ORDER BY p.frame_number
    """

    rows = con.execute(query).fetchall()
    con.close()

    out: dict[int, dict] = {}
    for frame_number, parts in rows:
        # Keep first occurrence per frame to mimic the old LIMIT 1 behaviour.
        if frame_number in out:
            continue
        joints = _parse_parts(parts)
        out[int(frame_number)] = {
            "trunk_lean": _trunk_lean_angle(joints),
            "stride_length": _stride_length(joints),
            "shoulder_asymmetry": _shoulder_asymmetry(joints),
            "knee_bend_right": _knee_bend_angle(joints, "right"),
            "knee_bend_left": _knee_bend_angle(joints, "left"),
        }

    return out