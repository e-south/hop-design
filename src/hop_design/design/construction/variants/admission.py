"""Keep packet admission and immutable exploration facts outside presentation clients."""

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from hop_design.design.source_documents import _read_source_bytes
from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import sha256_digest

from ..discovery.admission import CapturedDiscovery, captured_discovery
from ..discovery.explore import ScaffoldDiscovery
from ..edits.admission import captured_molecular_edit
from ..packets.capture import capture_packet, write_snapshot
from ..public import VerifiedConstructionBundle

type CapturedVariants = tuple[
    CapturedDiscovery, dict[str, bytes] | None, ProtectedRoot, str, str | None
]


@contextmanager
def captured_generated_variants(
    packet: ScaffoldDiscovery, receipts: dict[str, VerifiedConstructionBundle], source: Path
) -> Iterator[CapturedVariants]:
    """Bind just-produced files to invocation-local proofs, without another replay.

    This is not disk admission: the generating owner supplies both the packet and
    its replay-verified candidate receipts. Public reopening still replays afresh.
    """
    protected, files = capture_packet(source, schema=ScaffoldDiscovery._packet_schema)
    if files != dict(packet._files):
        raise ValueError(
            "Published scaffold files disagree with this invocation's verified packet."
        )
    with tempfile.TemporaryDirectory(prefix="hop-generated-exploration-") as temporary:
        root = Path(temporary)
        write_snapshot(files, root)
        captured = (root, json.loads(packet.json_bytes), receipts, protected)
        yield captured, None, protected, sha256_digest(files["manifest.json"]), None


@contextmanager
def captured_variant_source(path: str | Path, *, depth: int = 0) -> Iterator[CapturedVariants]:
    manifest = _read_source_bytes(
        Path(path) / "manifest.json", max_bytes=2_000_000, source_label="Exploration manifest"
    )
    schema = json.loads(manifest).get("schema")
    if schema == "hop.hairpin-design-snapshot/v1":
        from ..intents.hairpin_pages import captured_hairpin_pages

        with captured_hairpin_pages(Path(path)) as captured:
            yield captured
    elif schema == "hop.hairpin-history-packet/v1":
        from ..intents.hairpin_archive import captured_hairpin_history

        with captured_hairpin_history(Path(path)) as captured:
            yield captured
    elif schema == "hop.scaffold-envelope-evaluation-packet/v1":
        from .envelopes.admission import captured_envelope_evaluation

        with captured_envelope_evaluation(path, depth) as captured:
            yield captured
    elif schema == "hop.scaffold-parameter-evaluation-packet/v1":
        from .extended_admission import captured_parameter_evaluation

        with captured_parameter_evaluation(path, depth) as captured:
            yield captured
    elif schema == "hop.molecular-edit-result-packet/v1":
        with captured_molecular_edit(path) as (captured, preview, files, protected):
            if files["manifest.json"] != manifest:
                raise ValueError("Exploration source changed during admission.")
            yield captured, files, protected, sha256_digest(manifest), preview["edit_digest"]
    elif schema == "hop.scaffold-discovery-packet/v1":
        with captured_discovery(path) as captured:
            root, _, _, protected = captured
            if (root / "manifest.json").read_bytes() != manifest:
                raise ValueError("Exploration source changed during admission.")
            yield captured, None, protected, sha256_digest(manifest), None
    else:
        raise ValueError("Explore a verified scaffold discovery or molecular edit result packet.")
