import os

import duckdb
import config
from pathlib import Path


def get_connection(*, use_s3: bool = False) -> duckdb.DuckDBPyConnection:
    """
    DuckDB in-memory connection.
    S3/httpfs is disabled — only local parquet is used.
    """
    # if use_s3:
    #     con.execute("INSTALL httpfs; LOAD httpfs;")
    #     con.execute(f"SET s3_region='{config.AWS_REGION}';")
    #     con.execute(f"SET s3_access_key_id='{config.AWS_ACCESS_KEY_ID}';")
    #     con.execute(f"SET s3_secret_access_key='{config.AWS_SECRET_ACCESS_KEY}';")
    #     if config.AWS_SESSION_TOKEN:
    #         con.execute(f"SET s3_session_token='{config.AWS_SESSION_TOKEN}';")
    if use_s3:
        raise FileNotFoundError(
            "S3 parquet is disabled. Put the match parquet in LOCAL_PARQUET_DIR."
        )
    return duckdb.connect()


def _sql_string_literal(value: str) -> str:
    """Escape a path for embedding in SQL single-quoted strings."""
    return value.replace("'", "''")


# def get_s3_parquet_path(match_id: str) -> str:
#     """Return the full S3 path to the Parquet skeleton file for a match."""
#     prefix = config.MATCHES.get(match_id)
#     if not prefix:
#         raise ValueError(
#             f"Unknown match_id '{match_id}'. "
#             f"Available: {list(config.MATCHES.keys())}"
#         )
#     parquet_filename = config.MATCH_PARQUET_FILES.get(match_id)
#     if not parquet_filename:
#         raise ValueError(f"No Parquet filename registered for match '{match_id}'")
#     return f"s3://{config.S3_BUCKET}/{prefix}{parquet_filename}"


def _local_parquet_file(match_id: str) -> Path | None:
    parquet_filename = config.MATCH_PARQUET_FILES.get(match_id)
    if not parquet_filename:
        return None
    env_key = f"LOCAL_PARQUET_{match_id.upper()}"
    env_path = os.environ.get(env_key)
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file():
            return p
    local_path = config.LOCAL_PARQUET_DIR / parquet_filename
    if local_path.is_file():
        return local_path
    return None


def has_local_parquet(match_id: str) -> bool:
    """True when a parquet file exists on disk for this match."""
    return _local_parquet_file(match_id) is not None


def get_parquet_path(match_id: str) -> tuple[str, bool]:
    """
    Resolve Parquet path for DuckDB read_parquet().
    Returns (path, use_s3=False). Raises if the local file is missing.
    """
    parquet_filename = config.MATCH_PARQUET_FILES.get(match_id)
    if not parquet_filename:
        raise ValueError(f"No Parquet filename registered for match '{match_id}'")

    local_path = _local_parquet_file(match_id)
    if local_path is not None:
        return str(local_path.resolve()), False

    expected = config.LOCAL_PARQUET_DIR / parquet_filename
    raise FileNotFoundError(
        f"Local parquet not found for '{match_id}'. Expected {expected}"
    )


def read_parquet_sql(match_id: str) -> tuple[str, bool]:
    """
    Return (escaped_path, use_s3) for: read_parquet('{path}')
    """
    path, use_s3 = get_parquet_path(match_id)
    return _sql_string_literal(path), use_s3


def get_local_xml_path(match_id: str, xml_type: str) -> Path:
    """Local path for a match XML file (events / kpi / match_info / positions)."""
    xml_files = config.MATCH_XML_FILES.get(match_id, {})
    filename = xml_files.get(xml_type)
    if not filename:
        raise ValueError(
            f"No XML file registered for match '{match_id}' type '{xml_type}'. "
            f"Available types: {list(xml_files.keys())}"
        )
    return config.LOCAL_XML_DIR / filename


# Aliases used by skeleton_parser / event_parser
get_connection = get_connection
read_parquet_sql = read_parquet_sql


# def get_s3_xml_path(match_id: str, xml_type: str) -> str:
#     """Return the full S3 path to an XML file for a given match."""
#     prefix = config.MATCHES.get(match_id)
#     if not prefix:
#         raise ValueError(f"Unknown match_id '{match_id}'")
#     xml_files = config.MATCH_XML_FILES.get(match_id, {})
#     filename = xml_files.get(xml_type)
#     if not filename:
#         raise ValueError(
#             f"No XML file registered for match '{match_id}' type '{xml_type}'. "
#             f"Available types: {list(xml_files.keys())}"
#         )
#     return f"s3://{config.S3_BUCKET}/{prefix}{filename}"
