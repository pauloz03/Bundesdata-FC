"""
precompute.py
─────────────
Run once per match to precompute all player biomechanics and save
results as JSON back to S3.

The API then serves these precomputed files directly — no heavy
computation at request time.

Usage:
    python precompute.py --match union_bayern
    python precompute.py --all
"""

import argparse
import json
import logging
import boto3
import config
import skeleton_parser
import event_parser
import biomechanics_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# S3 helpers
# ─────────────────────────────────────────────────────────────────────────────

def _s3_client():
    return boto3.client(
        "s3",
        region_name=config.AWS_REGION,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        aws_session_token=config.AWS_SESSION_TOKEN or None,
    )


def _save_json_to_s3(data: dict, s3_key: str):
    """Upload a dict as a JSON file to S3."""
    s3 = _s3_client()
    s3.put_object(
        Bucket=config.S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(data, ensure_ascii=False, default=str),
        ContentType="application/json",
    )
    log.info(f"  Saved → s3://{config.S3_BUCKET}/{s3_key}")


def _precomputed_key(match_id: str, jersey: int, team_flag: int) -> str:
    """S3 key for a precomputed player file."""
    return (
        f"precomputed/{match_id}/"
        f"player_{jersey}_team{team_flag}.json"
    )


def _precomputed_timeline_key(match_id: str) -> str:
    return f"precomputed/{match_id}/timeline.json"


def _precomputed_players_key(match_id: str) -> str:
    return f"precomputed/{match_id}/players.json"


# ─────────────────────────────────────────────────────────────────────────────
# Precompute one match
# ─────────────────────────────────────────────────────────────────────────────

def precompute_match(match_id: str):
    log.info(f"Starting precompute for match: {match_id}")

    meta = config.MATCH_METADATA.get(match_id)
    if not meta:
        log.error(f"No metadata found for {match_id}. Add it to config.MATCH_METADATA.")
        return

    # ── Step 1: Player list + DFL id mapping ──────────────────────────────────
    log.info("  Fetching player list from skeleton data...")
    players = skeleton_parser.get_player_list(match_id)
    player_profiles = event_parser.get_player_profile_map(match_id)
    player_id_map = event_parser.get_player_id_map(match_id)
    log.info(
        f"  Found {len(players)} players, "
        f"{len(player_id_map)} DFL id mappings from match_info"
    )

    for player in players:
        key = (player["jersey"], player["team_flag"])
        profile = player_profiles.get(key, {})
        dfl_id = profile.get("dfl_player_id") or player_id_map.get(key)
        player["dfl_player_id"] = dfl_id
        player["player_name"] = profile.get("player_name")
        if profile.get("first_name"):
            player["first_name"] = profile.get("first_name")
        if profile.get("last_name"):
            player["last_name"] = profile.get("last_name")

    _save_json_to_s3(
        {"match_id": match_id, "players": players},
        _precomputed_players_key(match_id),
    )

    # ── Step 2: Match timeline ────────────────────────────────────────────────
    log.info("  Parsing match event timeline...")
    timeline = event_parser.get_match_timeline(match_id)
    log.info(f"  Found {len(timeline)} timeline events")

    _save_json_to_s3(
        {"match_id": match_id, "timeline": timeline},
        _precomputed_timeline_key(match_id),
    )

    # ── Step 3: Per-player biomechanics ───────────────────────────────────────
    log.info("  Computing biomechanics per player...")
    success_count = 0
    error_count   = 0

    for player in players:
        jersey    = player["jersey"]
        team_flag = player["team_flag"]
        profile = event_parser.resolve_player_profile(match_id, jersey, team_flag) or {}
        player_id = player.get("dfl_player_id") or event_parser.resolve_player_id(
            match_id, jersey, team_flag
        )

        if not player_id:
            log.warning(
                f"    ⚠ jersey #{jersey} team {team_flag}: "
                "no DFL player id in match_info — skipping events"
            )
            player_id = f"jersey_{jersey}_team{team_flag}"

        log.info(
            f"    Processing jersey #{jersey} ({player['side']}) "
            f"[{player_id}]..."
        )

        try:
            result = biomechanics_sync.get_player_event_biomechanics(
                match_id  = match_id,
                player_id = player_id,
                jersey    = jersey,
                team_flag = team_flag,
            )

            if "error" in result:
                log.warning(f"    ⚠ jersey #{jersey}: {result['error']}")
                error_count += 1
                continue

            # Add XML identity fields so frontend can display names directly.
            player_meta = result.get("player", {})
            player_meta["dfl_player_id"] = player_id
            if profile.get("player_name"):
                player_meta["player_name"] = profile.get("player_name")
            if profile.get("first_name"):
                player_meta["first_name"] = profile.get("first_name")
            if profile.get("last_name"):
                player_meta["last_name"] = profile.get("last_name")
            result["player"] = player_meta

            shots_count   = len(result.get("shots", []))
            passes_count  = len(result.get("passes", []))
            curve_count   = len(result.get("fatigue", {}).get("curve", []))
            episode_count = len(result.get("degradation_episodes", []))
            pass_summary  = result.get("passes_summary", {})
            log.info(
                f"    ✅ jersey #{jersey}: "
                f"{curve_count} curve points, "
                f"{episode_count} degradation episodes, "
                f"{shots_count} shots, "
                f"{passes_count} notable passes "
                f"(of {pass_summary.get('total_passes', '?')} total)"
            )

            _save_json_to_s3(
                result,
                _precomputed_key(match_id, jersey, team_flag),
            )
            success_count += 1

        except Exception as e:
            log.error(f"    ❌ jersey #{jersey}: {e}")
            error_count += 1

    log.info(
        f"Precompute complete for {match_id}: "
        f"{success_count} players OK, {error_count} errors"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Precompute match biomechanics")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--match", type=str, help="Match ID to precompute")
    group.add_argument("--all",   action="store_true", help="Precompute all matches")
    args = parser.parse_args()

    config.validate()

    if args.all:
        for match_id in config.MATCHES:
            precompute_match(match_id)
    else:
        if args.match not in config.MATCHES:
            log.error(
                f"Unknown match '{args.match}'. "
                f"Available: {list(config.MATCHES.keys())}"
            )
            return
        precompute_match(args.match)


if __name__ == "__main__":
    main()