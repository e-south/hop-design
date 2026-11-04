"""Capture original intentions and preview explicit edits without molecular search."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.molecular.preview import edit_preview_report
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..packets.publication import SourceBoundConstructionPacket
from .compile import compile_edit


@dataclass(frozen=True, init=False, repr=False)
class PreparedMolecularEdit(SourceBoundConstructionPacket):
    """An explicit original request, edit and unevaluated effective intention."""

    _packet_schema: ClassVar[str] = "hop.molecular-edit-preview-packet/v1"


def _prepare(mapping: dict[str, Any], protected: ProtectedRoot) -> PreparedMolecularEdit:
    if _contains_internal_schema_name(mapping):
        raise ValueError("Molecular edits must use external 'schema' fields.")
    compiled, summary = compile_edit(mapping)
    summary["edit_digest"] = sha256_digest(canonical_json_bytes(mapping))
    packet = PreparedMolecularEdit._create(
        {
            "edit.json": canonical_json_bytes(mapping),
            "original-request.json": canonical_json_bytes(mapping["original_request"]),
            "compiled-request.json": canonical_json_bytes(compiled),
        },
        summary,
        edit_preview_report(summary),
    )
    object.__setattr__(packet, "_roots", (protected,))
    return packet


def author_molecular_edit(
    path: str | Path,
    *,
    loop_sequences: tuple[str, ...] | None = None,
    end_placements: tuple[tuple[int, int], ...] | None = None,
    end_words: tuple[str, str] | None = None,
    basal_nick_enzyme_ids: tuple[str, ...] | None = None,
    release_enzyme_ids: tuple[str, ...] | None = None,
) -> PreparedMolecularEdit:
    """Bind a loop-word edit to the exact original scaffold request; do not search."""
    protected = ProtectedRoot.capture(path)
    original = load_source_mapping(path)
    validated = ScaffoldDiscoveryRequest.model_validate_json(json.dumps(original))
    edits: list[dict[str, Any]] = []
    if loop_sequences is not None:
        edits.append({"region": "loop", "stage": "hairpin", "sequences": list(loop_sequences)})
    if end_placements is not None:
        ends = None
        if end_words is not None:
            if validated.product.ends is None:
                raise ValueError("Released-end edits require a released insert endpoint.")
            ends = validated.product.ends.model_dump(mode="json")
            for side, word in zip(("left", "right"), end_words, strict=True):
                ends[side]["cohesive_end_sequence"] = word
        edits.append(
            {
                "region": "released_ends",
                "stage": "released_insert",
                "placements": [{"left_bp": a, "right_bp": b} for a, b in end_placements],
                "ends": ends,
                "basal_nick_enzyme_ids": basal_nick_enzyme_ids,
                "release_enzyme_ids": release_enzyme_ids,
            }
        )
    elif any(v is not None for v in (end_words, basal_nick_enzyme_ids, release_enzyme_ids)):
        raise ValueError("End words and method edits require explicit end placements.")
    mapping = {
        "schema": "hop.molecular-edit/v1",
        "original_request": original,
        "original_request_digest": sha256_digest(canonical_json_bytes(validated)),
        "edits": edits,
    }
    return _prepare(mapping, protected)


def prepare_molecular_edit(path: str | Path) -> PreparedMolecularEdit:
    """Validate a captured edit and expose conflicts before any molecular evaluation."""
    return _prepare(load_source_mapping(path), ProtectedRoot.capture(path))
