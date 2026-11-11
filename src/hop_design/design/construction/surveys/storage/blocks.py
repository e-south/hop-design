"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/surveys/storage/blocks.py

Shares immutable object bytes in bounded, independently checked compressed blocks.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import hashlib
import sqlite3
from collections import OrderedDict

import zstandard as zstd

from hop_design.serialization import sha256_digest

from .legacy import MAX_RECORD_BYTES

_BLOCK_FIELDS = "digest,raw_size,CASE WHEN length(content)<=68157440 THEN content ELSE NULL END"


class BlockStore:
    """The caller owns transactions; pending bytes never establish committed state."""

    target_block_bytes = 4 * 1024**2
    maximum_cache_bytes = 8 * 1024**2

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.compressor = zstd.ZstdCompressor(level=3, threads=0, write_checksum=True)
        self.decoder = zstd.ZstdDecompressor(max_window_size=128 * 1024)
        self.pending: dict[str, tuple[bytes, int]] = {}
        self.pending_bytes = 0
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.cache_bytes = 0

    def reset(self) -> None:
        self.pending.clear()
        self.pending_bytes = 0
        self.cache.clear()
        self.cache_bytes = 0

    def pending_creator(self, digest: str) -> int | None:
        item = self.pending.get(digest)
        return None if item is None else item[1]

    def put(self, content: bytes, *, creator: int = 0) -> str:
        if not isinstance(content, bytes) or not 0 < len(content) <= MAX_RECORD_BYTES:
            raise ValueError("Survey object exceeds its size limit.")
        digest = sha256_digest(content)
        if (
            digest in self.pending
            or self.db.execute("SELECT 1 FROM objects WHERE digest=?", (digest,)).fetchone()
        ):
            return digest
        if self.pending_bytes + len(content) > self.target_block_bytes:
            self.flush()
        self.pending[digest] = content, creator
        self.pending_bytes += len(content)
        if self.pending_bytes >= self.target_block_bytes:
            self.flush()
        return digest

    def flush(self) -> None:
        if not self.pending:
            return
        raw = b"".join(value[0] for value in self.pending.values())
        encoded = self.compressor.compress(raw)
        block = self.db.execute(
            "INSERT INTO blocks(digest,raw_size,content) VALUES (?,?,?)",
            (sha256_digest(encoded), len(raw), encoded),
        ).lastrowid
        offset = 0
        for digest, (content, creator) in self.pending.items():
            self.db.execute(
                "INSERT INTO objects VALUES (?,?,?,?,?)",
                (digest, block, offset, len(content), creator),
            )
            offset += len(content)
        self.pending.clear()
        self.pending_bytes = 0

    @staticmethod
    def _check_range(block: int, offset: int, size: int) -> None:
        if (
            any(type(v) is not int or v < 0 for v in (block, offset, size))
            or not 0 < size <= MAX_RECORD_BYTES
        ):
            raise ValueError("Object range integrity check failed.")

    def _read_block(self, block: int, saved: tuple[str, int, bytes] | None = None) -> bytes:
        if block in self.cache:
            self.cache.move_to_end(block)
            return self.cache[block]
        row = (
            saved
            if saved is not None
            else self.db.execute(
                f"SELECT {_BLOCK_FIELDS} FROM blocks WHERE id=?", (block,)
            ).fetchone()
        )
        if row is None:
            raise ValueError("Survey checkpoint references a missing block.")
        expected, size, encoded = row
        if (
            type(size) is not int
            or not 0 < size <= MAX_RECORD_BYTES
            or not isinstance(encoded, bytes)
            or len(encoded) > MAX_RECORD_BYTES + 1_048_576
            or sha256_digest(encoded) != expected
        ):
            raise ValueError("Block size or integrity check failed.")
        try:
            if zstd.frame_content_size(encoded) != size:
                raise ValueError("Block frame size integrity check failed.")
            raw = self.decoder.decompress(encoded, max_output_size=size, allow_extra_data=False)
        except zstd.ZstdError as error:
            raise ValueError("Block integrity check failed.") from error
        if len(raw) != size:
            raise ValueError("Block decoded size integrity check failed.")
        if size <= self.maximum_cache_bytes:
            while self.cache_bytes + size > self.maximum_cache_bytes:
                _, removed = self.cache.popitem(last=False)
                self.cache_bytes -= len(removed)
            self.cache[block] = raw
            self.cache_bytes += size
        return raw

    def get(self, digest: str) -> bytes:
        if digest in self.pending:
            return self.pending[digest][0]
        row = self.db.execute(
            "SELECT block,offset,size FROM objects WHERE digest=?", (digest,)
        ).fetchone()
        if row is None:
            raise ValueError("Survey checkpoint references a missing object.")
        block, offset, size = row
        self._check_range(block, offset, size)
        result = self._read_block(block)[offset : offset + size]
        if len(result) != size or sha256_digest(result) != digest:
            raise ValueError("Object range or integrity check failed.")
        return result

    def verify(self) -> None:
        """Check every hash and exact range coverage with two ordered cursors."""
        if self.pending:
            raise ValueError("Flush pending object bytes before checking storage integrity.")
        self.reset()
        objects = iter(
            self.db.execute("SELECT digest,block,offset,size FROM objects ORDER BY block,offset")
        )
        current = next(objects, None)
        for block, expected, size, encoded in self.db.execute(
            f"SELECT id,{_BLOCK_FIELDS} FROM blocks ORDER BY id"
        ):
            view, end = memoryview(self._read_block(block, (expected, size, encoded))), 0
            while current is not None and current[1] == block:
                digest, object_block, offset, length = current
                self._check_range(object_block, offset, length)
                member = view[offset : offset + length]
                if (
                    offset != end
                    or len(member) != length
                    or "sha256:" + hashlib.sha256(member).hexdigest() != digest
                ):
                    raise ValueError("Object range or integrity check failed.")
                end += length
                current = next(objects, None)
            if end != size:
                raise ValueError("Block ranges do not cover its stored bytes.")
        if current is not None:
            raise ValueError("Object references a missing block.")
