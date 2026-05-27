"""
fatigue_episodes.py
───────────────────
Detect sustained posture degradation windows on the fatigue curve
(~5s samples). Used for timeline bands in the UI and to gate
lean-based pass flags (ignore one-off lean spikes).
"""

from __future__ import annotations

import statistics
from typing import Any, Optional

import config


def _smooth_lean_deltas(curve: list[dict]) -> list[Optional[float]]:
    """3-point median smoothing on lean_delta to reduce single-sample spikes."""
    deltas = [s.get("lean_delta") for s in curve]
    out: list[Optional[float]] = []
    for i, val in enumerate(deltas):
        if val is None:
            out.append(None)
            continue
        window = []
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(deltas) and deltas[j] is not None:
                window.append(deltas[j])
        out.append(statistics.median(window) if window else val)
    return out


def _sample_is_bad(
    sample: dict,
    smoothed_lean_delta: Optional[float],
) -> bool:
    lean_bad = (
        smoothed_lean_delta is not None
        and smoothed_lean_delta >= config.EPISODE_LEAN_DELTA_DEG
    )
    stride_delta = sample.get("stride_delta")
    stride_bad = (
        stride_delta is not None
        and stride_delta <= -config.EPISODE_STRIDE_DELTA_M
    )
    if config.EPISODE_REQUIRE_BOTH_METRICS:
        return lean_bad and stride_bad
    return lean_bad or stride_bad


def _episode_severity(peak_lean: float, peak_stride_drop: float) -> str:
    if peak_lean >= config.FATIGUE_HIGH_THRESHOLD:
        return "high"
    if peak_lean >= config.FATIGUE_MODERATE_THRESHOLD:
        return "moderate"
    if peak_lean >= config.FATIGUE_MILD_THRESHOLD:
        return "mild"
    if abs(peak_stride_drop) >= config.EPISODE_STRIDE_DELTA_M * 2:
        return "moderate"
    return "mild"


def detect_degradation_episodes(curve: list[dict]) -> list[dict[str, Any]]:
    """
    Find runs of consecutive bad samples (sustained degradation).

    Returns list of:
        start_minute, end_minute, start_frame, end_frame,
        peak_lean_delta, peak_stride_delta, severity, sample_count
    """
    if not curve:
        return []

    smoothed = _smooth_lean_deltas(curve)
    min_run = config.EPISODE_MIN_CONSECUTIVE_SAMPLES
    max_gap = config.EPISODE_MAX_GAP_SAMPLES

    episodes: list[dict[str, Any]] = []
    run_start: Optional[int] = None
    run_indices: list[int] = []
    last_bad_idx: Optional[int] = None

    def flush_run():
        nonlocal run_start, run_indices, last_bad_idx
        if len(run_indices) < min_run:
            run_start = None
            run_indices = []
            last_bad_idx = None
            return

        start_s = curve[run_indices[0]]
        end_s = curve[run_indices[-1]]
        peak_lean = max(
            (smoothed[i] or 0.0 for i in run_indices if smoothed[i] is not None),
            default=0.0,
        )
        stride_drops = [
            curve[i].get("stride_delta")
            for i in run_indices
            if curve[i].get("stride_delta") is not None
        ]
        peak_stride_drop = min(stride_drops) if stride_drops else 0.0

        episodes.append({
            "start_minute":      start_s.get("minute"),
            "end_minute":        end_s.get("minute"),
            "start_frame":       start_s.get("frame"),
            "end_frame":         end_s.get("frame"),
            "peak_lean_delta":   round(peak_lean, 3),
            "peak_stride_delta": round(peak_stride_drop, 3),
            "severity":          _episode_severity(peak_lean, peak_stride_drop),
            "sample_count":      len(run_indices),
        })
        run_start = None
        run_indices = []
        last_bad_idx = None

    for i, sample in enumerate(curve):
        if _sample_is_bad(sample, smoothed[i]):
            if run_start is None:
                run_start = i
                run_indices = [i]
            elif last_bad_idx is not None and (i - last_bad_idx) <= max_gap + 1:
                run_indices.append(i)
            else:
                flush_run()
                run_start = i
                run_indices = [i]
            last_bad_idx = i
        elif run_start is not None and last_bad_idx is not None:
            if (i - last_bad_idx) <= max_gap:
                run_indices.append(i)
            else:
                flush_run()

    flush_run()
    return episodes


def minute_in_episode(minute: Optional[float], episodes: list[dict]) -> bool:
    """True if match minute falls inside any degradation episode window."""
    if minute is None:
        return False
    for ep in episodes:
        start_m = ep.get("start_minute")
        end_m = ep.get("end_minute")
        if start_m is None or end_m is None:
            continue
        if start_m <= minute <= end_m:
            return True
    return False
