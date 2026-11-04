"""Capture the full selected authority for explicit parameter or envelope revisions."""

import json
from typing import TYPE_CHECKING

from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import sha256_digest

from ..packets.capture import capture_packet

if TYPE_CHECKING:
    from .public import ScaffoldExploration


def capture_exploration(pool: "ScaffoldExploration") -> tuple[ProtectedRoot, dict[str, bytes]]:
    source = pool.source_path
    schema = json.loads((source / "manifest.json").read_bytes())["schema"]
    if schema == "hop.hairpin-design-snapshot/v1":
        from ..intents.hairpin_archive import capture_hairpin_history

        return capture_hairpin_history(source, pool.result_digest)
    protected, files = capture_packet(source, schema=schema)
    digest = sha256_digest(files["manifest.json"])
    if schema == "hop.hairpin-history-packet/v1":
        digest = json.loads(files["summary.json"])["result_digest"]
    if digest != pool.result_digest:
        raise ValueError("The admitted exploration changed before further evaluation.")
    return protected, files
