"""
s3_storage.py
───────────────
Read precomputed JSON artifacts written by precompute.py.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

import config


def _s3_client():
    return boto3.client(
        "s3",
        region_name=config.AWS_REGION,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        aws_session_token=config.AWS_SESSION_TOKEN or None,
    )


def _get_json(key: str) -> Optional[dict[str, Any]]:
    s3 = _s3_client()
    try:
        obj = s3.get_object(Bucket=config.S3_BUCKET, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def precomputed_player_key(match_id: str, jersey: int, team_flag: int) -> str:
    return f"precomputed/{match_id}/player_{jersey}_team{team_flag}.json"


def precomputed_players_key(match_id: str) -> str:
    return f"precomputed/{match_id}/players.json"


def precomputed_timeline_key(match_id: str) -> str:
    return f"precomputed/{match_id}/timeline.json"


def load_player(match_id: str, jersey: int, team_flag: int) -> Optional[dict[str, Any]]:
    return _get_json(precomputed_player_key(match_id, jersey, team_flag))


def load_players(match_id: str) -> Optional[dict[str, Any]]:
    return _get_json(precomputed_players_key(match_id))


def load_timeline(match_id: str) -> Optional[dict[str, Any]]:
    return _get_json(precomputed_timeline_key(match_id))
