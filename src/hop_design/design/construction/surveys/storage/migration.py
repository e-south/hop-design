"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/surveys/storage/migration.py

Converts stopped checkpoints into create-only targets without molecular replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import hashlib
import json
import shutil
import sqlite3
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.export.publication import publish_directory_create_only
from hop_design.serialization import canonical_json_bytes

from ..admission import open_survey
from ..execute import load_request
from ..index import SurveyIndex
from .compatibility import authorize_transition
from .origins import _producer


def _file_digest(path: Path) -> str:
    with path.open("rb") as handle:
        return "sha256:" + hashlib.file_digest(handle, "sha256").hexdigest()


@contextmanager
def stopped_source(path: Path) -> Iterator[sqlite3.Connection]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Migration source must be an existing regular checkpoint.")
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-journal")):
        raise ValueError("Close checkpoint writers and their journals before migration.")
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=rw", uri=True, timeout=0)
    try:
        db.execute("PRAGMA trusted_schema=OFF")
        try:
            db.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as error:
            raise ValueError("Stop the checkpoint writer before migration.") from error
        yield db
    finally:
        db.rollback()
        db.close()


def _source_writer(db: sqlite3.Connection) -> dict[str, str]:
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')").fetchone():
        raise ValueError("Migration source contains an invalid schema.")
    if version == 0:
        sizes = db.execute(
            "SELECT length(content),typeof(content) FROM metadata LIMIT 2"
        ).fetchall()
        if len(sizes) != 1 or sizes[0][1] != "blob" or not 0 < sizes[0][0] <= 64 * 1024**2:
            raise ValueError("Invalid migration source metadata.")
        return _producer(
            canonical_json_bytes(
                json.loads(db.execute("SELECT content FROM metadata").fetchone()[0])["producer"]
            )
        )
    if version == 2:
        rows = db.execute(
            "SELECT length(content),typeof(content) FROM producers "
            "WHERE id=(SELECT producer FROM writer) LIMIT 2"
        ).fetchall()
        if len(rows) != 1 or rows[0][1] != "blob" or not 0 < rows[0][0] <= 65_536:
            raise ValueError("Invalid migration source writer.")
        return _producer(
            db.execute(
                "SELECT content FROM producers WHERE id=(SELECT producer FROM writer)"
            ).fetchone()[0]
        )
    raise ValueError("Unknown migration source format.")


def _copy_content(
    source: SurveyIndex,
    target: SurveyIndex,
    should_stop: Callable[[], bool] | None,
    on_converted: Callable[[int, int], None] | None,
) -> None:
    target.origins.import_history(source.origins)
    tracked = source.origins.ledger is not None
    creator = "creator" if tracked else "0"
    buffered = count = decoded = 0
    try:
        for digest, origin in source._db.execute(
            f"SELECT digest,{creator} FROM objects ORDER BY digest"
        ):
            if should_stop is not None and should_stop():
                raise InterruptedError("Checkpoint migration cancelled.")
            raw = source.get_object(digest)
            if target._objects.put(raw, creator=origin) != digest:
                raise ValueError("Object identity changed during checkpoint migration.")
            buffered += len(raw)
            count, decoded = count + 1, decoded + len(raw)
            if buffered >= 4 * 1024**2:
                target._objects.flush()
                target._db.commit()
                buffered = 0
            if on_converted is not None:
                on_converted(count, decoded)
        target._objects.flush()
        for table, columns in (
            ("steps", "ordinal,step,record_digest,witness_count,exhausted,digest"),
            ("cache", "key,digest"),
        ):
            for row in source._db.execute(f"SELECT {columns},{creator} FROM {table}"):
                if should_stop is not None and should_stop():
                    raise InterruptedError("Checkpoint migration cancelled.")
                marks = ",".join("?" for _ in row)
                target._db.execute(f"INSERT INTO {table} VALUES ({marks})", row)
        target._objects.flush()
        target._db.commit()
    except BaseException:
        target._db.rollback()
        raise


def migrate_interface_survey(
    request_path: str | Path,
    index_path: str | Path,
    *,
    destination: str | Path,
    max_checkpoint_bytes: int = 1_073_741_824,
    minimum_free_bytes: int = 0,
    should_stop: Callable[[], bool] | None = None,
    on_converted: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Copy every original object/record and authorize one supported new writer.

    Original creator bytes and identities are retained. This operation checks
    stored content; it does not rerun the historical molecular search.
    """
    path, output = Path(index_path), Path(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace checkpoint migration: {output}")
    if type(max_checkpoint_bytes) is not int or max_checkpoint_bytes < 1_048_576:
        raise ValueError("Checkpoint migration limit must be at least 1048576 bytes.")
    if type(minimum_free_bytes) is not int or minimum_free_bytes < 0:
        raise ValueError("Migration free-space reserve must be nonnegative bytes.")
    request, producer = load_request(request_path), producer_identity()
    output.parent.mkdir(parents=True, exist_ok=True)
    if (
        shutil.disk_usage(output.parent).free
        < max_checkpoint_bytes + minimum_free_bytes + 134_217_728
    ):
        raise ValueError("Insufficient free space for the checkpoint migration and its reserve.")
    with stopped_source(path) as guard:
        writer = _source_writer(guard)
        if writer != producer:
            authorize_transition(writer, producer)
        before = _file_digest(path)
        saved, limits = open_survey(path, request=request, producer=writer)
        with saved:
            staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
            try:
                checkpoint = staging / "survey.sqlite"
                with SurveyIndex.create(
                    checkpoint,
                    request=request,
                    producer=saved.creator_producer,
                    limits=limits.model_dump(mode="json"),
                    format_version=2,
                ) as target:
                    target.set_storage_limit(max_checkpoint_bytes)
                    source_digest = saved.logical_digest()
                    _copy_content(saved, target, should_stop, on_converted)
                    target._validate()
                    if target.logical_digest() != source_digest:
                        raise ValueError("Checkpoint logical content changed during migration.")
                    source_writer = target.origins.writer
                    target.transition_producer(producer)
                    target._validate()
                    report = {
                        "schema": "hop.interface-survey-migration/v1",
                        "verification": "lossless_content_conversion",
                        "source_producer": writer,
                        "producer": producer,
                        "source_format": 1 if saved.origins.ledger is None else 2,
                        "target_format": 2,
                        "source_logical_digest": source_digest,
                        "retained_prefix_digest": target.prefix_digest(source_writer),
                        "objects": target.object_count,
                        "evaluations": sum(step + 1 for step in target.last_steps().values()),
                        "coverage": target.coverage(),
                        "storage": target.storage_info(),
                    }
                if _file_digest(path) != before or producer_identity() != producer:
                    raise ValueError(
                        "Source checkpoint or migration runtime changed during conversion."
                    )
                if should_stop is not None and should_stop():
                    raise InterruptedError("Checkpoint migration cancelled before publication.")
                report.update(
                    source_checkpoint_digest=before, checkpoint_digest=_file_digest(checkpoint)
                )
                (staging / "request.json").write_bytes(canonical_json_bytes(request))
                (staging / "migration.json").write_bytes(canonical_json_bytes(report))
                publish_directory_create_only(staging, output)
                return report
            except BaseException as error:
                shutil.rmtree(staging, ignore_errors=True)
                if isinstance(error, sqlite3.Error):
                    raise ValueError("Checkpoint migration storage operation failed.") from error
                raise
