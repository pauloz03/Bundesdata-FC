import math
import os
from pathlib import Path

import pyarrow.parquet as pq
import s3fs
from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")

BUCKET_NAME = "hackathon-data-127393434859"
PREFFIX = "Challenge 2 – Unlock the Power of 3D Football Data/Match_Data/Union_Bayern/"
PARQUET_KEY = PREFFIX + "FCU-FCB.parquet"

FRAMERATE     = 50
PHASE_1_START = 2_790_583
PHASE_1_END   = 2_940_975
PHASE_2_START = 2_989_542
PHASE_2_END   = 3_143_459

HOME_FLAG = 1
AWAY_FLAG = 0
REF_FLAG  = 3

# ── Target player (hardcoded for this test) ───────────────────────────────────
TARGET_JERSEY   = 14
TARGET_TEAM     = HOME_FLAG

JOINT_MAP = {
    1: "l_ear",    2: "nose",      3: "r_ear",
    4: "l_shoulder", 5: "neck",   6: "r_shoulder",
    7: "l_elbow",  8: "r_elbow",  9: "l_wrist",   10: "r_wrist",
    11: "l_hip",   12: "pelvis",  13: "r_hip",
    14: "l_knee",  15: "r_knee",
    16: "l_ankle", 17: "r_ankle",
    18: "l_heel",  19: "l_toe",   20: "r_heel",   21: "r_toe",
}


def connect_s3():
    key_id        = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key    = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = os.environ.get("AWS_SESSION_TOKEN")
    if not key_id or not secret_key:
        raise EnvironmentError(f"Missing AWS credentials in {_BACKEND_DIR / '.env'}")
    return s3fs.S3FileSystem(
        anon=False, key=key_id, secret=secret_key, token=session_token or None
    )


def extract_posture(skeletons, target_jersey, target_team):
    for entity in skeletons:
        if int(entity.get("jersey_number", -99)) != int(target_jersey):
            continue
        if int(entity.get("team", -99)) != int(target_team):
            continue
        parts = entity.get("parts")
        if parts is None or len(parts) == 0:
            continue
        posture = {}
        for joint in parts:
            jd = dict(joint) if not isinstance(joint, dict) else joint
            jid = jd.get("name")
            x, y, z = jd.get("position_x"), jd.get("position_y"), jd.get("position_z")
            if jid is not None and x is not None:
                posture[int(jid)] = (float(x), float(y), float(z))
        return posture
    return None


def trunk_lean_angle(posture):
    neck   = posture.get(5)
    pelvis = posture.get(12)
    if not neck or not pelvis:
        return None
    dx = neck[0] - pelvis[0]
    dy = neck[1] - pelvis[1]
    dz = neck[2] - pelvis[2]
    horizontal = math.sqrt(dx**2 + dy**2)
    vertical   = abs(dz) if abs(dz) > 0.001 else 0.001
    return round(math.degrees(math.atan2(horizontal, vertical)), 3)


def stride_length(posture):
    """Euclidean distance between left and right ankle — proxy for stride length."""
    l_ankle = posture.get(16)
    r_ankle = posture.get(17)
    if not l_ankle or not r_ankle:
        return None
    dx = l_ankle[0] - r_ankle[0]
    dy = l_ankle[1] - r_ankle[1]
    return round(math.sqrt(dx**2 + dy**2), 3)


def shoulder_asymmetry(posture):
    """Height difference between left and right shoulder — body imbalance indicator."""
    l_shoulder = posture.get(4)
    r_shoulder = posture.get(6)
    if not l_shoulder or not r_shoulder:
        return None
    return round(abs(l_shoulder[2] - r_shoulder[2]), 3)


def frame_to_minute(frame):
    if PHASE_1_START <= frame <= PHASE_1_END:
        return (frame - PHASE_1_START) / FRAMERATE / 60
    elif PHASE_2_START <= frame <= PHASE_2_END:
        return 45 + (frame - PHASE_2_START) / FRAMERATE / 60
    return None


def fatigue_signal(delta):
    if delta > 5:   return "🔴 HIGH"
    if delta > 2:   return "🟡 Moderate"
    if delta > 0.5: return "🟢 Mild"
    return "   OK"


def find_match_row_groups(parquet_file):
    num_groups      = parquet_file.metadata.num_row_groups
    first_half_rgs  = []
    second_half_rgs = []
    for rg in range(num_groups):
        df = parquet_file.read_row_group(rg, columns=["frame_number"]).to_pandas()
        mn = int(df["frame_number"].min())
        mx = int(df["frame_number"].max())
        if mn <= PHASE_1_END   and mx >= PHASE_1_START:
            first_half_rgs.append(rg)
        if mn <= PHASE_2_END   and mx >= PHASE_2_START:
            second_half_rgs.append(rg)
        if rg % 30 == 0:
            print(f"  Scanning rg {rg:>4}/{num_groups} | {mn:,}–{mx:,}")
        if mn > PHASE_2_END:
            break
    print(f"  ✅ First half:  rg {first_half_rgs[0]}–{first_half_rgs[-1]}  ({len(first_half_rgs)} groups)")
    print(f"  ✅ Second half: rg {second_half_rgs[0]}–{second_half_rgs[-1]}  ({len(second_half_rgs)} groups)")
    return first_half_rgs, second_half_rgs


def build_fatigue_curve(parquet_file, all_match_rgs, jersey, team_flag,
                        sample_every_n_frames=250):
    """
    Sample every 250 frames (~5s at 50Hz).
    Returns list of dicts with minute, lean_angle, stride_length, shoulder_asymmetry.
    Also prints a 5-minute bucketed summary table.
    """
    print("\n" + "=" * 60)
    side = "Home" if team_flag == HOME_FLAG else "Away"
    print(f"Fatigue curve — jersey #{jersey}  ({side})")
    print(f"Sampling every {sample_every_n_frames} frames (~{sample_every_n_frames/FRAMERATE:.0f}s)")
    print("=" * 60)

    raw = []  # list of {minute, lean, stride, asym}

    for rg in all_match_rgs:
        df = parquet_file.read_row_group(rg).to_pandas()
        for idx, (_, row) in enumerate(df.iterrows()):
            if idx % sample_every_n_frames != 0:
                continue
            frame  = int(row["frame_number"])
            minute = frame_to_minute(frame)
            if minute is None:
                continue
            posture = extract_posture(row["skeletons"],
                                      target_jersey=jersey,
                                      target_team=team_flag)
            if not posture:
                continue
            lean  = trunk_lean_angle(posture)
            stride = stride_length(posture)
            asym   = shoulder_asymmetry(posture)
            if lean is not None:
                raw.append({
                    "minute":   round(minute, 2),
                    "lean":     lean,
                    "stride":   stride,
                    "asym":     asym,
                    "frame":    frame,
                })

    if not raw:
        print("  ❌ No data found. Check jersey and team flag.")
        return []

    # ── Compute baselines from first 10 samples (kickoff) ────────────────────
    n_base        = min(10, len(raw))
    baseline_lean = sum(r["lean"]   for r in raw[:n_base]) / n_base
    baseline_str  = sum(r["stride"] for r in raw[:n_base] if r["stride"]) / n_base
    baseline_asym = sum(r["asym"]   for r in raw[:n_base] if r["asym"])   / n_base

    print(f"\n  Baselines from first {n_base} samples:")
    print(f"    Trunk lean:           {baseline_lean:.3f}°")
    print(f"    Stride length:        {baseline_str:.3f} m")
    print(f"    Shoulder asymmetry:   {baseline_asym:.4f} m")
    print(f"  Total raw samples: {len(raw)}\n")

    # ── 5-minute bucket summary ───────────────────────────────────────────────
    print(f"  {'Min':>5}  {'Lean°':>7}  {'ΔLean':>7}  {'Stride':>7}  {'ΔStride':>8}  {'Asym':>6}  Signal")
    print("  " + "─" * 68)

    last_bucket = -1
    for r in raw:
        bucket = int(r["minute"] // 5)
        if bucket == last_bucket:
            continue
        last_bucket = bucket
    
        delta_lean   = r["lean"]   - baseline_lean
        delta_stride = (r["stride"] - baseline_str) if r["stride"] else 0
        signal       = fatigue_signal(delta_lean)
        ht           = " ◀ HT" if 44.5 <= r["minute"] <= 45.5 else ""

        lean_str   = f"{r['lean']:>7.2f}°"
        delta_str  = f"{delta_lean:>+7.2f}°"
        stride_str = f"{r['stride']:>7.3f}" if r["stride"] else "     —"
        ds_str     = f"{delta_stride:>+8.3f}" if r["stride"] else "       —"
        asym_str   = f"{r['asym']:>6.4f}" if r["asym"] else "     —"

        print(f"  {r['minute']:>4.1f}'  {lean_str}  {delta_str}  {stride_str}  {ds_str}  {asym_str}  {signal}{ht}")

    # ── End of match summary ──────────────────────────────────────────────────
    final_lean   = raw[-1]["lean"]
    final_stride = raw[-1]["stride"] or 0
    drift_lean   = final_lean   - baseline_lean
    drift_stride = final_stride - baseline_str

    print(f"\n  ── End of match summary ──────────────────────────────")
    print(f"  Trunk lean drift:    {drift_lean:+.3f}°  →  {fatigue_signal(drift_lean)}")
    print(f"  Stride length drift: {drift_stride:+.3f} m  ({drift_stride/baseline_str*100:+.1f}%)")
    print(f"  Shoulder asym final: {raw[-1]['asym']:.4f} m  (baseline {baseline_asym:.4f} m)")

    return raw


def run():
    print("Connecting to S3...\n")
    fs      = connect_s3()
    s3_path = f"s3://{BUCKET_NAME}/{PARQUET_KEY}"

    with fs.open(s3_path, mode="rb") as f:
        pf = pq.ParquetFile(f)

        print(f"Rows: {pf.metadata.num_rows:,}  |  Row groups: {pf.metadata.num_row_groups}  |  {FRAMERATE}Hz")
        print(f"Phase 1: {PHASE_1_START:,} → {PHASE_1_END:,}")
        print(f"Phase 2: {PHASE_2_START:,} → {PHASE_2_END:,}\n")

        print("=" * 60)
        print("Mapping match row groups...")
        print("=" * 60)
        first_half_rgs, second_half_rgs = find_match_row_groups(pf)
        all_match_rgs = sorted(set(first_half_rgs + second_half_rgs))

        build_fatigue_curve(
            pf,
            all_match_rgs,
            jersey    = TARGET_JERSEY,
            team_flag = TARGET_TEAM,
            sample_every_n_frames = 250,
        )


if __name__ == "__main__":
    run()