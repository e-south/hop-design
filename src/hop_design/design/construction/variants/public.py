"""Opaque immutable exploration receipts and bounded public choice queries."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, cast

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.molecular.primer_boundary import (
    render_primer_boundaries,
    render_primer_boundary,
)
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.variants.query import ScaffoldVariantQuery
from hop_design.serialization import canonical_json_bytes

from ..packets.publication import SourceBoundConstructionPacket
from .admission import CapturedVariants, captured_variant_source
from .coverage import interface_branch_facts
from .envelopes.revision import editable_envelope
from .explanation import explain_variants
from .facts import option_facts
from .parameters.coverage import parameter_metadata
from .query import query_summary


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldExploration:
    """Admitted immutable facts; each query reads a fresh value, not mutable caller state."""

    _metadata: bytes
    _options: bytes
    _root: ProtectedRoot
    _routes: tuple[tuple[str, MaterializedConstructionRealization], ...]
    _request: bytes
    _source: Path

    @property
    def source_path(self) -> Path:
        return self._source

    @property
    def result_digest(self) -> str:
        return str(json.loads(self._metadata)["result_digest"])

    @property
    def json_bytes(self) -> bytes:
        return self._metadata


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldVariantChoices:
    """Query facts are immediate; reports and packet inventories are created only on export."""

    _packet_schema: ClassVar[str] = "hop.scaffold-variant-choices-packet/v1"
    _summary: bytes
    _roots: tuple[ProtectedRoot, ...]
    _answer: bytes

    def explain(self) -> dict[str, Any]:
        """Describe this exact conditional result without selecting a preparation."""
        return cast(dict[str, Any], json.loads(self._answer))

    @property
    def json_bytes(self) -> bytes:
        return self._summary

    @property
    def primer_boundary_views(self) -> list[dict[str, Any]]:
        """Representative source-only drawings; exact rejected rows remain in JSON."""
        rows = json.loads(self._summary)["choice_space"]["primer_boundaries"]
        grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault((row["primer"], row["required_nt"], row["available_nt"]), []).append(
                row
            )
        return [
            {
                "primer": key[0],
                "required_nt": key[1],
                "available_nt": key[2],
                "examined_continuations": len(members),
                "representative": members[0],
                "svg": render_primer_boundary(members[0]).decode(),
            }
            for key, members in sorted(grouped.items())
        ]

    @property
    def report_text(self) -> str:
        summary = json.loads(self._summary)
        query = summary["query"]
        failures = sorted(
            {
                (r["primer"], r["required_nt"], r["available_nt"])
                for r in summary["choice_space"]["primer_boundaries"]
            }
        )
        primer_text = "".join(
            f"- Examined source {primer} primer: {required} nt required; "
            f"{available} nt available. This continuation fails.\n"
            for primer, required, available in failures
        )
        return (
            "# Conditional scaffold choices\n\n"
            f"Stage: {query['stage']}. Neighborhood: {query['focus']}.\n"
            f"Complete compatible preparations: {len(summary['compatible_options'])}; "
            f"distinct products: {len(summary['products'])}.\n\n"
            "Replacement choices omit only the focused neighborhood pin; "
            "all other controls remain active. No product is selected. "
            "Absence from this evaluated pool is not global impossibility.\n\n" + primer_text
        )

    @property
    def _files(self) -> tuple[tuple[str, bytes], ...]:
        return self._packet()._files

    def _packet(self) -> SourceBoundConstructionPacket:
        summary = json.loads(self._summary)
        files = {"query.json": canonical_json_bytes(summary["query"])}
        if rows := summary["choice_space"]["primer_boundaries"]:
            files["primer-boundaries.svg"] = render_primer_boundaries(rows)
        packet = _ChoicesPacket._create(files, summary, self.report_text)
        object.__setattr__(packet, "_roots", self._roots)
        return packet

    def write(self, destination: str | Path) -> Path:
        return self._packet().write(destination)


@dataclass(frozen=True, init=False, repr=False)
class _ChoicesPacket(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = ScaffoldVariantChoices._packet_schema


def load_scaffold_exploration(path: str | Path) -> ScaffoldExploration:
    with captured_variant_source(path) as admitted:
        return _admitted_exploration(admitted, source_path=Path(path))


def _admitted_exploration(
    admitted: CapturedVariants, *, source_path: Path | None = None
) -> ScaffoldExploration:
    captured, _, protected, digest, edit_digest = admitted
    root, native, receipts, _ = captured
    options = option_facts(root, native, receipts)
    request = ScaffoldDiscoveryRequest.model_validate_json(
        (root / "intent/request.json").read_bytes()
    )
    metadata = {
        "schema": "hop.scaffold-exploration/v1",
        "result_digest": digest,
        "request_digest": native["request_digest"],
        "edit_digest": edit_digest,
        "producer": native["producer"],
        "source_producers": native.get("source_producers", [native["producer"]]),
        "endpoint": native["endpoint"],
        "coverage": native["coverage"],
        "envelope": {
            "fields": editable_envelope(request),
            "locked": {
                "supplied_stem": request.product.stem_arm,
                "receiving_ends": request.product.ends.model_dump(mode="json")
                if request.product.ends
                else None,
                "material_policies": request.product.materialization.model_dump(mode="json"),
                "whole_route_requirements": request.product.whole_route_constraints.model_dump(
                    mode="json"
                ),
                "scaffold": request.scaffold.model_dump(mode="json") if request.scaffold else None,
            },
        },
        "interface_branches": interface_branch_facts(root, native),
        **parameter_metadata(root, native),
        "options": [
            {
                k: o[k]
                for k in (
                    "label",
                    "molecular_identity",
                    "materialized_realization_id",
                    "loop_sequence",
                    "geometry",
                )
            }
            for o in options
        ],
        "examined_failures": [
            {"branch": b["label"], **f} for b in native["branches"] for f in b["failures"]
        ],
        "local_coverage": [
            {"branch": b["label"], "coverage": b["local_coverage"]} for b in native["branches"]
        ],
    }
    instance = object.__new__(ScaffoldExploration)
    object.__setattr__(instance, "_metadata", canonical_json_bytes(metadata))
    object.__setattr__(instance, "_options", canonical_json_bytes(options))
    object.__setattr__(instance, "_root", protected)
    object.__setattr__(instance, "_source", source_path or protected.path)
    object.__setattr__(instance, "_request", (root / "intent/request.json").read_bytes())
    object.__setattr__(
        instance,
        "_routes",
        tuple(
            (
                o["label"],
                next(
                    r
                    for r in receipts[o["label"]]._verified_source().result.realizations
                    if r.materialized_realization_id == o["materialized_realization_id"]
                ),
            )
            for o in native["options"]
        ),
    )
    return instance


def query_scaffold_variants(
    pool: ScaffoldExploration, request: str | Path | dict[str, Any]
) -> ScaffoldVariantChoices:
    if not isinstance(pool, ScaffoldExploration) or not hasattr(pool, "_metadata"):
        raise TypeError("Variant queries require an admitted scaffold exploration receipt.")
    value = load_source_mapping(request) if isinstance(request, str | Path) else request
    query = ScaffoldVariantQuery.model_validate_json(canonical_json_bytes(value)).canonical()
    summary = query_summary(json.loads(pool._metadata), json.loads(pool._options), query)
    packet = object.__new__(ScaffoldVariantChoices)
    object.__setattr__(packet, "_summary", canonical_json_bytes(summary))
    object.__setattr__(packet, "_roots", (pool._root,))
    object.__setattr__(
        packet,
        "_answer",
        canonical_json_bytes(
            explain_variants(json.loads(pool._metadata), json.loads(pool._options), summary)
        ),
    )
    return packet
