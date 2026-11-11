"""Open one stable checkpoint snapshot and validate its physical schema/binding."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes

from .legacy import MAX_RECORD_BYTES
from .origins import OriginLedger

_TABLES = {"metadata", "objects", "steps", "cache"}
_ORIGINS = {"producers", "writer", "transitions"}


def metadata_bytes(
    request: InterfaceSurveyRequest, producer: dict[str, str], limits: dict[str, Any] | None
) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "hop.interface-survey-index/v1",
            "request": request.model_dump(mode="json", by_alias=True),
            "producer": producer,
            "evaluation_limits": limits,
        }
    )


def create(
    path: Path,
    request: InterfaceSurveyRequest,
    producer: dict[str, str],
    limits: dict[str, Any] | None,
    format_version: int,
) -> tuple[sqlite3.Connection, OriginLedger | None]:
    if type(format_version) is not int or format_version not in (1, 2):
        raise ValueError("Unknown survey checkpoint format.")
    with path.open("xb"):
        pass
    db = sqlite3.connect(path)
    try:
        db.execute("PRAGMA foreign_keys = ON")
        ledger = OriginLedger.create(db, producer) if format_version == 2 else None
        origin = ", creator INTEGER NOT NULL REFERENCES producers(id)" if ledger else ""
        if ledger:
            db.execute(
                "CREATE TABLE blocks (id INTEGER PRIMARY KEY, digest TEXT NOT NULL, "
                "raw_size INTEGER NOT NULL, content BLOB NOT NULL)"
            )
        objects = (
            "CREATE TABLE objects (digest TEXT PRIMARY KEY, "
            "block INTEGER NOT NULL REFERENCES blocks(id), "
            f"offset INTEGER NOT NULL, size INTEGER NOT NULL{origin})"
            if ledger
            else "CREATE TABLE objects (digest TEXT PRIMARY KEY, content BLOB NOT NULL)"
        )
        for sql in (
            "CREATE TABLE metadata (content BLOB NOT NULL)",
            objects,
            "CREATE TABLE cache (key TEXT PRIMARY KEY, "
            "digest TEXT NOT NULL REFERENCES objects(digest)"
            f"{origin})",
            "CREATE TABLE steps (ordinal INTEGER NOT NULL, step INTEGER NOT NULL, "
            "record_digest TEXT NOT NULL REFERENCES objects(digest), "
            "witness_count INTEGER NOT NULL, "
            f"exhausted INTEGER NOT NULL, digest TEXT NOT NULL{origin}, PRIMARY KEY(ordinal,step))",
        ):
            db.execute(sql)
        db.execute("INSERT INTO metadata VALUES (?)", (metadata_bytes(request, producer, limits),))
        if ledger:
            db.execute("PRAGMA user_version=2")
            db.execute("CREATE INDEX object_block_order ON objects(block,offset)")
            for table, tail in (("objects", "digest"), ("steps", "ordinal,step"), ("cache", "key")):
                db.execute(f"CREATE INDEX {table}_origin_order ON {table}(creator,{tail})")
        db.commit()
        return db, ledger
    except BaseException:
        db.close()
        path.unlink()
        raise


def open_snapshot(
    path: Path,
    request: InterfaceSurveyRequest,
    producer: dict[str, str],
    limits: dict[str, Any] | None,
    read_only: bool,
) -> tuple[sqlite3.Connection, dict[str, str], OriginLedger | None]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Survey checkpoint must be an existing regular file.")
    mode = "ro" if read_only else "rw"
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode={mode}", uri=True)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        if read_only:
            db.execute("BEGIN")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 2):
            raise ValueError("Unknown survey checkpoint format.")
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if (
            tables != _TABLES | (_ORIGINS | {"blocks"} if version == 2 else set())
            or db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')").fetchone()
            or db.execute("PRAGMA integrity_check").fetchone() != ("ok",)
        ):
            raise ValueError("Survey checkpoint integrity check failed.")
        rows = db.execute("SELECT content FROM metadata").fetchall()
        if (
            len(rows) != 1
            or not isinstance(rows[0][0], bytes)
            or len(rows[0][0]) > MAX_RECORD_BYTES
        ):
            raise ValueError("Invalid survey checkpoint metadata.")
        original = json.loads(rows[0][0])["producer"]
        if rows != [(metadata_bytes(request, original if version == 2 else producer, limits),)]:
            raise ValueError(
                "Survey checkpoint request or producer disagrees with this invocation."
            )
        ledger = OriginLedger.load(db, original, producer) if version == 2 else None
        return db, original, ledger
    except BaseException as error:
        db.close()
        if isinstance(error, (sqlite3.Error, KeyError, TypeError)):
            raise ValueError("Survey checkpoint integrity check failed.") from error
        raise
