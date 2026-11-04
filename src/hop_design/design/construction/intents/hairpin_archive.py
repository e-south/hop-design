"""Portable capture of a selected page history, only for explicit export or revision."""

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import sha256_digest

from ..packets.capture import capture_packet, write_snapshot
from ..packets.publication import SourceBoundConstructionPacket
from ..variants.admission import CapturedVariants
from .hairpin_history import HairpinSnapshot, snapshot_paths, snapshot_source
from .hairpin_pages import captured_hairpin_pages


class HairpinHistoryArchive(SourceBoundConstructionPacket):
    _packet_schema = "hop.hairpin-history-packet/v1"


def capture_hairpin_history(target: Path, digest: str) -> tuple[ProtectedRoot, dict[str, bytes]]:
    """Copies are explicit portable exports, never part of ordinary continuation."""
    root = target.parent.parent
    protected = ProtectedRoot.capture(root)
    source, _ = snapshot_source(root, digest)
    if source != target / "scaffolds":
        raise ValueError("The selected page history changed before export.")
    files = {}
    if (root / "scaffolds").exists():
        _, legacy = capture_packet(root / "scaffolds", schema="hop.scaffold-discovery-packet/v1")
        files.update({f"history/scaffolds/{name}": data for name, data in legacy.items()})
    for page in snapshot_paths(root):
        _, contents = capture_packet(page, schema=HairpinSnapshot._packet_schema)
        files.update(
            {
                f"history/hairpin-snapshots/{page.name}/{name}": data
                for name, data in contents.items()
            }
        )
        if page == target:
            break
    packet = HairpinHistoryArchive._create(
        files,
        {
            "schema": "hop.hairpin-history/v1",
            "target": target.name,
            "result_digest": digest,
        },
        "# Hairpin history\n\nExact selected page and preceding molecular authorities.\n",
    )
    protected.require_unchanged()
    return protected, dict(packet._files)


@contextmanager
def captured_hairpin_history(path: Path) -> Iterator[CapturedVariants]:
    protected, files = capture_packet(path, schema=HairpinHistoryArchive._packet_schema)
    saved = json.loads(files["summary.json"])
    with tempfile.TemporaryDirectory(prefix="hop-hairpin-history-") as temporary:
        root = Path(temporary)
        write_snapshot(files, root)
        pages = snapshot_paths(root / "history")
        if not pages:
            raise ValueError("A portable hairpin history requires its selected page.")
        target = pages[-1]
        digest = sha256_digest((target / "scaffolds/manifest.json").read_bytes())
        if saved != {
            "schema": "hop.hairpin-history/v1",
            "target": target.name,
            "result_digest": digest,
        }:
            raise ValueError("Portable history selection disagrees with its bound pages.")
        with captured_hairpin_pages(target) as admitted:
            captured, _, _, result_digest, edit = admitted
            scene, summary, receipts, _ = captured
            protected.require_unchanged()
            yield (scene, summary, receipts, protected), None, protected, result_digest, edit
