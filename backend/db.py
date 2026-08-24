import os

import duckdb
import config
from pathlib import Path


def get_connection(*, use_s3: bool = False) -> duckdb.DuckDBPyConnection:
    """
    DuckDB in-memory connection.
    Loads httpfs + S3 credentials only when reading remote Parquet (use_s3=True).
    """
    con = duckdb.connect()
    if use_s3:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_region='{config.AWS_REGION}';")
        con.execute(f"SET s3_access_key_id='{config.AWS_ACCESS_KEY_ID}';")
        con.execute(f"SET s3_secret_access_key='{config.AWS_SECRET_ACCESS_KEY}';")
        if config.AWS_SESSION_TOKEN:
            con.execute(f"SET s3_session_token='{config.AWS_SESSION_TOKEN}';")
    return con


def _sql_string_literal(value: str) -> str:
    """Escape a path for embedding in SQL single-quoted strings."""
    return value.replace("'", "''")


def get_s3_parquet_path(match_id: str) -> str:
    """
    Return the full S3 path to the Parquet skeleton file for a given match ID.
    Raises ValueError if the match ID is not registered in config.
    """
    prefix = config.MATCHES.get(match_id)
    if not prefix:
        raise ValueError(
            f"Unknown match_id '{match_id}'. "
            f"Available: {list(config.MATCHES.keys())}"
        )

    parquet_filename = config.MATCH_PARQUET_FILES.get(match_id)
    if not parquet_filename:
        raise ValueError(f"No Parquet filename registered for match '{match_id}'")

    return f"s3://{config.S3_BUCKET}/{prefix}{parquet_filename}"


def has_local_parquet(match_id: str) -> bool:
    """True when a parquet file exists on disk for this match (no S3 fallback)."""
    _, use_s3 = get_parquet_path(match_id)
    return not use_s3


def get_parquet_path(match_id: str) -> tuple[str, bool]:
    """
    Resolve Parquet path for DuckDB read_parquet().

    Returns (path, use_s3):
      - Local file in LOCAL_PARQUET_DIR if present (use_s3=False)
      - Per-match env override LOCAL_PARQUET_{MATCH_ID} if set and file exists
      - Otherwise S3 path (use_s3=True)

    Local filenames match MATCH_PARQUET_FILES, e.g. FCU-FCB.parquet.
    """
    parquet_filename = config.MATCH_PARQUET_FILES.get(match_id)
    if not parquet_filename:
        raise ValueError(f"No Parquet filename registered for match '{match_id}'")

    env_key = f"LOCAL_PARQUET_{match_id.upper()}"
    env_path = os.environ.get(env_key)
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file():
            return str(p.resolve()), False

    local_path = config.LOCAL_PARQUET_DIR / parquet_filename
    if local_path.is_file():
        return str(local_path.resolve()), False

    return get_s3_parquet_path(match_id), True


def read_parquet_sql(match_id: str) -> tuple[str, bool]:
    """
    Return (escaped_path, use_s3) for: read_parquet('{path}')
    """
    path, use_s3 = get_parquet_path(match_id)
    return _sql_string_literal(path), use_s3


def get_s3_xml_path(match_id: str, xml_type: str) -> str:
    """
    Return the full S3 path to an XML file for a given match.

    xml_type options:
        "events"       → Events_[Match].xml
        "kpi"          → kpi_data_[Match].xml
        "match_info"   → MatchInformations_[Match].xml
        "positions"    → Positions_[Match].xml
    """
    prefix = config.MATCHES.get(match_id)
    if not prefix:
        raise ValueError(f"Unknown match_id '{match_id}'")

    xml_files = config.MATCH_XML_FILES.get(match_id, {})
    filename = xml_files.get(xml_type)
    if not filename:
        raise ValueError(
            f"No XML file registered for match '{match_id}' type '{xml_type}'. "
            f"Available types: {list(xml_files.keys())}"
        )

    return f"s3://{config.S3_BUCKET}/{prefix}{filename}"
