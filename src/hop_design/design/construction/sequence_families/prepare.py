"""Expand only the authored stem; all paired arms and preparations remain derived."""

import json
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.molecular.sequence_family import SequenceFamilyRequest
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.models.sequence import iupac_bases
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..packets.publication import SourceBoundConstructionPacket


@dataclass(frozen=True, init=False, repr=False)
class PreparedSequenceFamily(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.sequence-family-preview-packet/v1"


def prepare_sequence_family(path: str | Path) -> PreparedSequenceFamily:
    protected = ProtectedRoot.capture(path)
    mapping = load_source_mapping(path)
    if _contains_internal_schema_name(mapping):
        raise ValueError("Sequence families require external schema fields.")
    request = SequenceFamilyRequest.model_validate_json(json.dumps(mapping))
    files = {"request.json": canonical_json_bytes(mapping)}
    members = []
    for name, word in exact_members(request.stem_domain):
        value = request.base_request.model_dump(mode="json", by_alias=True)
        value["product"]["stem_arm"] = word
        relative = f"requests/{name}.json"
        files[relative] = canonical_json_bytes(value)
        members.append({"name": name, "stem_arm": word, "request": relative})
    summary = {
        "schema": "hop.sequence-family-preview/v1",
        "request_digest": sha256_digest(files["request.json"]),
        "execution": "not_started",
        "required_members": len(members),
        "members": members,
        "shared_properties": list(request.shared_properties),
        "shared_material_roles": list(request.shared_material_roles),
        "max_total_branches": request.max_total_branches,
        "pooled_library": "not_assessed",
    }
    report = (
        f"# Exact sequence family\n\n{len(members)} required exact stems. "
        "Paired arms are derived; preparation permissions remain as authored.\n\n"
        "Shared flanks and materials are checked on explicit selection, "
        "not assumed from dimensions. "
        "Missing complete members remain explicit. No pooled-library guarantee.\n"
    )
    packet = PreparedSequenceFamily._create(files, summary, report)
    object.__setattr__(packet, "_roots", (protected,))
    return packet


def exact_members(domain: str) -> tuple[tuple[str, str], ...]:
    """Expand a validated bounded domain in the family's stable member order."""
    return tuple(
        (f"member-{i:04d}", "".join(bases))
        for i, bases in enumerate(product(*(sorted(iupac_bases(s)) for s in domain)), 1)
    )
