"""Review a permission revision before spending a construction-search budget."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...discovery.prepare import prepare_scaffold_discovery
from ...packets.capture import capture_packet
from ...packets.publication import SourceBoundConstructionPacket
from ..parameter_evaluation import InheritedParameterConflict, selected_evaluation_request
from ..parameters.domains import parameter_domains
from ..public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants
from .revision import editable_envelope, revise_request


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldEnvelopePreview(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-envelope-preview-packet/v1"


def preview_scaffold_envelope_revision(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    revision: str | Path | dict[str, Any],
) -> ScaffoldEnvelopePreview:
    query = json.loads(choices.json_bytes)["query"]
    if query_scaffold_variants(pool, query).json_bytes != choices.json_bytes:
        raise ValueError("Envelope revision requires current verified choices.")
    mapping = load_source_mapping(revision) if isinstance(revision, str | Path) else revision
    source = ScaffoldDiscoveryRequest.model_validate_json(pool._request)
    revised, changes = revise_request(source, mapping)
    envelope = revised.model_dump(mode="json", by_alias=True)
    conflict = None
    try:
        request = selected_evaluation_request(
            envelope, query, revised.max_branches, revised.max_continuations_per_branch
        )
    except InheritedParameterConflict as error:
        # The conflicting target remains in query.json. This base request is only
        # used to describe bounds; a conflicting preview cannot be evaluated.
        request = envelope
        conflict = {
            "code": "inherited-parameter-conflict",
            "requested_field": f"parameters.{error.key}",
            "explicit_edit": (
                f"Revise the inherited {error.key} restriction "
                "or explicitly change that chart selection."
            ),
        }
    with tempfile.TemporaryDirectory(prefix="hop-envelope-preview-") as temporary:
        path = Path(temporary) / "request.json"
        path.write_bytes(canonical_json_bytes(request))
        prepared = prepare_scaffold_discovery(path)
    plan = json.loads(prepared.json_bytes)
    if conflict is not None:
        plan["status"] = "conflicting_requirements"
        plan["conflicts"] = [conflict, *plan["conflicts"]]
    summary = {
        "schema": "hop.scaffold-envelope-preview/v1",
        "parent_result_digest": pool.result_digest,
        "query": query,
        "query_digest": json.loads(choices.json_bytes)["query_digest"],
        "revision_digest": sha256_digest(canonical_json_bytes(mapping)),
        "envelope_digest": sha256_digest(canonical_json_bytes(envelope)),
        "status": plan["status"],
        "changes": changes,
        "conflicts": plan["conflicts"],
        "bounds": plan["bounds"],
        "parameter_domains": parameter_domains(revised),
        "fields": editable_envelope(revised),
        "preserved": [
            "supplied_stem",
            "receiving_ends",
            "material_policies",
            "whole_route_requirements",
            "query_reference_and_controls",
        ],
        "scope": "permission_revision_preview_not_molecular_feasibility",
    }
    report = "# Construction envelope revision\n\n"
    report += "No construction has been evaluated. The original result remains unchanged.\n\n"
    for c in changes:
        report += f"- {c['label']}: {json.dumps(c['before'])} → {json.dumps(c['after'])}\n"
    if conflict:
        report += "\n" + conflict["explicit_edit"] + "\n"
    report += "\n" + prepared.report_text
    packet = ScaffoldEnvelopePreview._create(
        {
            "revision.json": canonical_json_bytes(mapping),
            "query.json": canonical_json_bytes(query),
            "envelope-request.json": canonical_json_bytes(envelope),
            "evaluation-request.json": canonical_json_bytes(request),
        },
        summary,
        report,
    )
    object.__setattr__(packet, "_roots", (pool._root,))
    return packet


def load_scaffold_envelope_revision(
    pool: ScaffoldExploration,
    path: str | Path,
) -> ScaffoldEnvelopePreview:
    protected, files = capture_packet(path, schema=ScaffoldEnvelopePreview._packet_schema)
    choices = query_scaffold_variants(pool, json.loads(files["query.json"]))
    expected = preview_scaffold_envelope_revision(pool, choices, json.loads(files["revision.json"]))
    if dict(expected._files) != files:
        raise ValueError("Envelope preview disagrees with its original query and permission edits.")
    object.__setattr__(expected, "_roots", (pool._root, protected))
    return expected
