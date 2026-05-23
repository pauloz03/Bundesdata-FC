import os
from pathlib import Path
from dotenv import load_dotenv

#load .env 
_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")


#  AWS 
AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_SESSION_TOKEN     = os.environ.get("AWS_SESSION_TOKEN", "")
AWS_REGION            = os.environ.get("AWS_REGION", "eu-central-1")

#  S3 
S3_BUCKET     = os.environ.get("S3_BUCKET", "hackathon-data-127393434859")
S3_CHALLENGE  = "Challenge 2 – Unlock the Power of 3D Football Data"

# Match prefixes — one entry per match
# Key = short match ID used in API, Value = S3 prefix inside the bucket
MATCHES = {
    "union_bayern": f"{S3_CHALLENGE}/Match_Data/Union_Bayern/",
    "bayern_hamburg": f"{S3_CHALLENGE}/Match_Data/Bayern_Hamburg/",
    "dortmund_stuttgart": f"{S3_CHALLENGE}/Match_Data/Dortmund_Stuttgart/",
    "frankfurt_bayern": f"{S3_CHALLENGE}/Match_Data/Frankfurt_Bayern/",
    "frankfurt_union": f"{S3_CHALLENGE}/Match_Data/Frankfurt_Union/",
}

# TRACAB skeleton constants 
HOME_TEAM_FLAG = 1   # team=1 in skeleton data means home
AWAY_TEAM_FLAG = 0   # team=0 in skeleton data means away
REF_FLAG       = 3   # team=3 = referee

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

#  Biomechanics thresholds 
FATIGUE_MILD_THRESHOLD     = 0.5   # degrees above baseline
FATIGUE_MODERATE_THRESHOLD = 2.0
FATIGUE_HIGH_THRESHOLD     = 5.0

#  Sampling 
FATIGUE_SAMPLE_EVERY_N_FRAMES = 250   # ~5 seconds at 50Hz

#  FastAPI 
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", 8000))

#  Cognito (fill these in once you create the user pool) 
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID    = os.environ.get("COGNITO_APP_CLIENT_ID", "")
COGNITO_REGION       = os.environ.get("COGNITO_REGION", "eu-central-1")


def validate():
    """Call this at startup to catch missing config early."""
    missing = []
    if not AWS_ACCESS_KEY_ID:
        missing.append("AWS_ACCESS_KEY_ID")
    if not AWS_SECRET_ACCESS_KEY:
        missing.append("AWS_SECRET_ACCESS_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Add them to {_BACKEND_DIR / '.env'}"
        )