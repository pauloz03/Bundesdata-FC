import os
from pathlib import Path
from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")

# Local Parquet cache — drop match files here to avoid repeated S3 scans.
# e.g. backend/data/parquet/FCU-FCB.parquet for union_bayern
LOCAL_PARQUET_DIR = Path(
    os.environ.get("LOCAL_PARQUET_DIR", str(_BACKEND_DIR / "data" / "parquet"))
).expanduser()

# ── AWS ──
AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_SESSION_TOKEN     = os.environ.get("AWS_SESSION_TOKEN", "")
AWS_REGION            = os.environ.get("AWS_REGION", "eu-central-1")

# ── S3 ──
S3_BUCKET    = os.environ.get("S3_BUCKET", "hackathon-data-127393434859")
S3_CHALLENGE = "Challenge 2 \u2013 Unlock the Power of 3D Football Data"

# ── Match registry ────────────────────────────────────────────────────────────
# Each match needs:

MATCHES = {
    "union_bayern": f"{S3_CHALLENGE}/Match_Data/Union_Bayern/",
    "frankfurt_union": f"{S3_CHALLENGE}/Match_Data/Frankfurt_Union/",
    "frankfurt_bayern": f"{S3_CHALLENGE}/Match_Data/Frankfurt_Bayern/",
    "dortmund_stuttgart": f"{S3_CHALLENGE}/Match_Data/Dortmund_Stuttgart/",
    "bayern_hamburg": f"{S3_CHALLENGE}/Match_Data/Bayern_Hamburg/",
}

MATCH_PARQUET_FILES = {
    "union_bayern": "FCU-FCB.parquet",
    "frankfurt_union": "SGE-FCU.parquet" ,
    "frankfurt_bayern": "SGE-FCB.parquet" ,
    "dortmund_stuttgart": "BVB-VFB.parquet" ,
    "bayern_hamburg": "FCB-HSV.parquet",
}

MATCH_XML_FILES = {
    "union_bayern": {
        "events":     "Events_Union_Bayern.xml",
        "kpi":        "kpi_data_Union_Bayern.xml",
        "match_info": "MatchInformations_Union_Bayern.xml",
        "positions":  "Positions_Union_Bayern.xml",
    },
    "frankfurt_union": {
        "events":     "Events_Frankfurt_Union.xml",
        "kpi":        "kpi_data_Frankfurt_Union.xml",
        "match_info": "MatchInformations_Frankfurt_Union.xml",
        "positions":  "Positions_Frankfurt_Union.xml",
    },
    "frankfurt_bayern": {
        "events":     "Events_Frankfurt_Bayern.xml",
        "kpi":        "kpi_data_Frankfurt_Bayern.xml",
        "match_info": "MatchInformations_Frankfurt_Bayern.xml",
        "positions":  "Positions_Frankfurt_Bayern.xml",
    },
    "dortmund_stuttgart": {
        "events":     "Events_Dortmund_Stuttgart.xml",
        "kpi":        "kpi_data_Dortmund_Stuttgart.xml",
        "match_info": "MatchInformations_Dortmund_Stuttgart.xml",
        "positions":  "Positions_Dortmund_Stuttgart.xml",
    },
    "bayern_hamburg": {
        "events":     "Events_Bayern_Hamburg.xml",
        "kpi":        "kpi_data_Bayern_Hamburg.xml",
        "match_info": "MatchInformations_Bayern_Hamburg.xml",
        "positions":  "Positions_Bayern_Hamburg.xml",
    },
}

# ── Match metadata ─────────────────────────────────────────────────────────────
# Phase frame numbers come from each Parquet file's metadata header.
# Add the other matches once you inspect their Parquet metadata.
MATCH_METADATA = {
    "union_bayern": {
        "label":          "Union Berlin vs Bayern Munich",
        "date":           "2025-09-13",
        "home_team":      "FC Union Berlin",
        "away_team":      "FC Bayern Munich",
        "home_team_flag": 1,   # TRACAB skeleton team flag
        "away_team_flag": 0,
        "framerate":      50,
        "phase_1_start":  2_790_583,
        "phase_1_end":    2_940_975,
        "phase_2_start":  2_989_542,
        "phase_2_end":    3_143_459,
        # From Parquet metadata
        "home_team_id":   297,
        "away_team_id":   10,
    },
    "bayern_hamburg": {
        "label":          "Bayern Munich vs Hamburg",
        "home_team":      "FC Bayern Munich",
        "away_team":      "Hamburger SV",
        "home_team_flag": 1,
        "away_team_flag": 0,
        "framerate":      50,
        "phase_1_start":  3_330_943,
        "phase_1_end":    3_484_329,
        "phase_2_start":  3_536_417,
        "phase_2_end":    3_678_119,
        # From Parquet metadata
        "home_team_id":   10,
        "away_team_id":   13,
    },
    "dortmund_stuttgart": {
        "label":          "Dortmund vs Stuttgart",
        "home_team":      "Borussia Dortmund",
        "away_team":      "VfB Stuttgart",
        "home_team_flag": 1,
        "away_team_flag": 0,
        "framerate":      50,
        "phase_1_start":  2_790_134,
        "phase_1_end":    2_935_531,
        "phase_2_start":  2_984_098,
        "phase_2_end":    3_141_386,
        # From Parquet metadata
        "home_team_id":   18,
        "away_team_id":   14,
    },
    "frankfurt_bayern": {
        "label":          "Frankfurt vs Bayern Munich",
        "home_team":      "Eintracht Frankfurt",
        "away_team":      "FC Bayern Munich",
        "home_team_flag": 1,
        "away_team_flag": 0,
        "framerate":      50,
        "phase_1_start":  3_331_222,
        "phase_1_end":    3_476_767,
        "phase_2_start":  3_526_374,
        "phase_2_end":    3_674_654,
        # From Parquet metadata
        "home_team_id":   12,
        "away_team_id":   10,
    },
    "frankfurt_union": {
        "label":          "Frankfurt vs Union Berlin",
        "home_team":      "Eintracht Frankfurt",
        "away_team":      "FC Union Berlin",
        "home_team_flag": 1,
        "away_team_flag": 0,
        "framerate":      50,
        "phase_1_start":  2_790_176,
        "phase_1_end":    2_943_018,
        "phase_2_start":  2_988_828,
        "phase_2_end":    3_156_116,
        # From Parquet metadata
        "home_team_id":   12,
        "away_team_id":   297,
    },
}

# ── TRACAB skeleton team flags ────────────────────────────────────────────────
HOME_TEAM_FLAG = 1
AWAY_TEAM_FLAG = 0
REF_FLAG       = 3

# ── Joint ID → name mapping (TRACAB spec) ─────────────────────────────────────
JOINT_MAP = {
    1:  "l_ear",
    2:  "nose",
    3:  "r_ear",
    4:  "l_shoulder",
    5:  "neck",
    6:  "r_shoulder",
    7:  "l_elbow",
    8:  "r_elbow",
    9:  "l_wrist",
    10: "r_wrist",
    11: "l_hip",
    12: "pelvis",
    13: "r_hip",
    14: "l_knee",
    15: "r_knee",
    16: "l_ankle",
    17: "r_ankle",
    18: "l_heel",
    19: "l_toe",
    20: "r_heel",
    21: "r_toe",
}

# ── Biomechanical thresholds ──────────────────────────────────────────────────
FATIGUE_MILD_THRESHOLD     = 0.5   # degrees above baseline → mild
FATIGUE_MODERATE_THRESHOLD = 2.0   # degrees above baseline → moderate
FATIGUE_HIGH_THRESHOLD     = 5.0   # degrees above baseline → high / sub signal

# ── Sampling ──────────────────────────────────────────────────────────────────
FATIGUE_SAMPLE_EVERY_N_FRAMES = 250   # ~5 seconds at 50Hz
BASELINE_SAMPLE_COUNT         = 10    # first N samples used to compute baseline

# ── Sustained degradation episodes (fatigue timeline bands) ───────────────────
EPISODE_LEAN_DELTA_DEG         = 3.0    # ° above kickoff baseline per ~5s sample
EPISODE_STRIDE_DELTA_M           = 0.08  # stride shorter than baseline (metres)
EPISODE_MIN_CONSECUTIVE_SAMPLES  = 6     # ~30s at 5s sampling
EPISODE_MAX_GAP_SAMPLES          = 1     # allow 1 non-bad sample inside a run
EPISODE_REQUIRE_BOTH_METRICS     = False # True = lean AND stride; False = lean OR stride

# ── Notable pass filtering (event-time vs kickoff baseline) ───────────────────
PASS_STRIDE_DELTA_THRESHOLD      = 0.05  # |Δstride| at pass vs kickoff baseline (m)
PASS_LEAN_DELTA_THRESHOLD          = 2.0    # Δlean at pass vs kickoff baseline (°)
PASS_REQUIRE_EPISODE_FOR_LEAN_ONLY = True  # lean alone counts only inside an episode

# ── FastAPI ───────────────────────────────────────────────────────────────────
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))

# ── PostgreSQL auth (to be implemented) ──────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ── Optional Football media API (team logos / player photos) ─────────────────
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
FOOTBALL_API_BASE = os.environ.get("FOOTBALL_API_BASE", "https://v3.football.api-sports.io")

# Local demo: skip JWT checks and allow fatigue from local parquet only.
SKIP_AUTH = os.environ.get("SKIP_AUTH", "").lower() in ("1", "true", "yes")


def validate():
    """Call at app startup — raises if critical env vars are missing."""
    if SKIP_AUTH:
        return
    missing = []
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if not JWT_SECRET:
        missing.append("JWT_SECRET")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Add them to {_BACKEND_DIR / '.env'}"
        )