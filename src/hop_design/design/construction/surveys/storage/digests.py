"""Hash logical creator segments independently of object compression or location."""

import hashlib
import sqlite3
from collections.abc import Iterator

from hop_design.serialization import canonical_json_bytes

from .origins import OriginLedger


def prefix_digests(
    db: sqlite3.Connection,
    original: dict[str, str],
    ledger: OriginLedger | None,
    *,
    verify_only: bool = False,
) -> Iterator[tuple[int, str]]:
    digest = hashlib.sha256(b"hop.survey-creator-prefix/v1\n")
    digest.update(db.execute("SELECT content FROM metadata").fetchone()[0])
    producers = (original,) if ledger is None else ledger.producers()
    boundaries = [] if ledger is None else ledger.boundaries()
    for identity, producer in enumerate(producers):
        if identity:
            transition = boundaries[identity - 1]
            if "sha256:" + digest.hexdigest() != transition[3]:
                raise ValueError("Checkpoint creator prefix digest disagrees with its transition.")
            digest.update(canonical_json_bytes(["transition", *transition]))
        if verify_only and identity == len(producers) - 1:
            return
        digest.update(canonical_json_bytes(["producer", identity, producer]))
        for table, columns, order in (
            ("objects", "digest", "digest"),
            ("steps", "ordinal,step,record_digest,witness_count,exhausted,digest", "ordinal,step"),
            ("cache", "key,digest", "key"),
        ):
            where = " WHERE creator=?" if ledger is not None else ""
            args = (identity,) if ledger is not None else ()
            for row in db.execute(f"SELECT {columns} FROM {table}{where} ORDER BY {order}", args):
                digest.update(canonical_json_bytes([table, *row]))
        yield identity, "sha256:" + digest.hexdigest()
