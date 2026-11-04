"""Admit saved edits once through their original request and complete discovery."""

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import canonical_json_bytes

from ..discovery.admission import CapturedDiscovery, captured_discovery
from ..packets.capture import capture_packet, write_snapshot
from .drawings import sequence_drawings
from .prepare import prepare_molecular_edit
from .results import edit_result_summary

type CapturedEdit = tuple[CapturedDiscovery, dict[str, Any], dict[str, bytes], ProtectedRoot]


@contextmanager
def captured_molecular_edit(
    path: str | Path, *, edit_digest: str | None = None
) -> Iterator[CapturedEdit]:
    protected, files = capture_packet(path, schema="hop.molecular-edit-result-packet/v1")
    with tempfile.TemporaryDirectory(prefix="hop-edit-admission-") as temporary:
        root = Path(temporary)
        write_snapshot(files, root)
        prepared = prepare_molecular_edit(root / "intent/edit.json")
        preview = json.loads(prepared.json_bytes)
        if edit_digest is not None and edit_digest != preview["edit_digest"]:
            raise ValueError("Stale molecular edit digest; select from the evaluated revision.")
        expected = dict(prepared._files)["compiled-request.json"]
        if expected != files.get("intent/compiled-request.json") or expected != files.get(
            "options/intent/request.json"
        ):
            raise ValueError("Saved discovery is not bound to this molecular edit.")
        with captured_discovery(root / "options") as captured:
            native = captured[1]
            if canonical_json_bytes(edit_result_summary(preview, native)) != files["summary.json"]:
                raise ValueError("Molecular edit summary differs from its verified discovery.")
            expected_views, _ = sequence_drawings(captured[0], native, captured[2])
            if {k: v for k, v in files.items() if k.startswith("views/")} != expected_views:
                raise ValueError(
                    "Saved sequence view differs from its verified molecular authority."
                )
            yield captured, preview, files, protected
