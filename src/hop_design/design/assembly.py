"""Shared final-insert, plan, artifact, and bundle assembly."""

from __future__ import annotations

from collections.abc import Mapping
from importlib.metadata import version
from types import MappingProxyType

from hop_design.design.result import Compilation
from hop_design.export.fasta import render_fasta
from hop_design.kernel.bundle_identity import bundle_id, manifest_seed
from hop_design.models.bundle import ArtifactManifestEntry, HopBundle, ProvenanceRecord
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport
from hop_design.models.plan import (
    CompilationLock,
    FeatureRole,
    HopPlan,
    SequenceFeature,
    SequenceRecord,
)
from hop_design.models.processing import PlanProcessingRoute
from hop_design.models.spec import DesignSpec
from hop_design.models.stem import PairedStemExtension
from hop_design.serialization import canonical_json_bytes, sha256_digest


def assemble_compilation(
    *,
    spec: DesignSpec,
    report: CheckReport,
    route: PlanProcessingRoute,
    catalog_ref: str,
    foldback_ref: str,
    basal_ref: str,
    foldback_sequence: str,
    basal_left_arm: str,
    basal_right_arm: str,
    stem_extension: PairedStemExtension | None,
    route_source_sequence: str | None,
    additional_artifacts: Mapping[str, tuple[bytes, str]],
) -> Compilation:
    """Assemble the shared sequence, plan, provenance, and bundle artifacts."""
    report.raise_for_errors()
    compiler_version = version("hop-design")

    spec_bytes = canonical_json_bytes(spec)
    spec_digest = sha256_digest(spec_bytes)
    lock = CompilationLock(
        compiler_version=compiler_version,
        defaults_ref=spec.defaults_ref,
        catalog_ref=catalog_ref,
        constraint_profile_ref=spec.constraint_profile_ref,
        processing_route_ref=route.route_id,
        foldback_junction_ref=foldback_ref,
        basal_junction_ref=basal_ref,
    )

    paired_payload = spec.payload.paired_sequence
    pieces = [(FeatureRole.BASAL_LEFT_ARM, basal_left_arm)]
    if stem_extension is not None:
        pieces.append((FeatureRole.STEM_EXTENSION_LEFT_ARM, stem_extension.left_arm))
    pieces.extend(
        (
            (FeatureRole.PAYLOAD, spec.payload.sequence),
            (FeatureRole.FOLDBACK_JUNCTION, foldback_sequence),
            (FeatureRole.PAIRED_PAYLOAD, paired_payload),
        )
    )
    if stem_extension is not None:
        pieces.append((FeatureRole.STEM_EXTENSION_RIGHT_ARM, stem_extension.right_arm))
    pieces.append((FeatureRole.BASAL_RIGHT_ARM, basal_right_arm))
    cursor = 0
    features: list[SequenceFeature] = []
    for role, sequence in pieces:
        end = cursor + len(sequence)
        features.append(
            SequenceFeature(
                role=role,
                span=Span(start=Boundary(offset=cursor), end=Boundary(offset=end)),
                sequence=sequence,
            )
        )
        cursor = end
    final_sequence = "".join(sequence for _, sequence in pieces)
    final_insert = SequenceRecord(
        record_id=f"{spec.design_id}-final-insert", sequence=final_sequence
    )
    source_oligo = SequenceRecord(
        record_id=f"{spec.design_id}-source-oligo",
        sequence=final_sequence if route_source_sequence is None else route_source_sequence,
    )

    plan_seed = canonical_json_bytes(
        {
            "compiler_version": compiler_version,
            "lock": lock.model_dump(mode="json"),
            "route": route.model_dump(mode="json"),
            "spec_digest": spec_digest,
        }
    )
    plan_id = f"hop:plan/{spec.design_id}/{sha256_digest(plan_seed).removeprefix('sha256:')[:16]}"
    plan = HopPlan(
        plan_id=plan_id,
        design_id=spec.design_id,
        spec_digest=spec_digest,
        payload_sequence=spec.payload.sequence,
        paired_payload_sequence=paired_payload,
        source_oligo=source_oligo,
        final_insert=final_insert,
        features=tuple(features),
        processing_route=route,
        lock=lock,
    )
    plan_bytes = canonical_json_bytes(plan)
    plan_digest = sha256_digest(plan_bytes)
    provenance = ProvenanceRecord(
        compiler_version=compiler_version,
        plan_id=plan.plan_id,
        spec_digest=spec_digest,
        defaults_ref=lock.defaults_ref,
        catalog_ref=lock.catalog_ref,
        constraint_profile_ref=lock.constraint_profile_ref,
        processing_route_ref=lock.processing_route_ref,
    )
    artifact_bytes: dict[str, bytes] = {
        "final-insert.fasta": render_fasta(final_insert),
        "hop-plan.json": plan_bytes,
        "hop-spec.json": spec_bytes,
        "provenance.json": canonical_json_bytes(provenance),
    }
    media_types: dict[str, str] = {
        "final-insert.fasta": "text/x-fasta",
        "hop-plan.json": "application/json",
        "hop-spec.json": "application/json",
        "provenance.json": "application/json",
    }
    if source_oligo.sequence != final_insert.sequence:
        artifact_bytes["source-oligo.fasta"] = render_fasta(source_oligo)
        media_types["source-oligo.fasta"] = "text/x-fasta"
    for path, (content, media_type) in additional_artifacts.items():
        if path in artifact_bytes:
            raise ValueError(f"Additional artifact collides with required bundle path: {path}.")
        artifact_bytes[path] = content
        media_types[path] = media_type
    entries = tuple(
        ArtifactManifestEntry(
            path=path,
            media_type=media_types[path],
            digest=sha256_digest(content),
            size_bytes=len(content),
        )
        for path, content in sorted(artifact_bytes.items())
    )
    manifest_data = manifest_seed(
        design_id=spec.design_id,
        spec_digest=spec_digest,
        plan_digest=plan_digest,
        artifacts=entries,
        external_refs=spec.external_refs,
    )
    manifest_digest = sha256_digest(canonical_json_bytes(manifest_data))
    bundle = HopBundle(
        bundle_id=bundle_id(design_id=spec.design_id, manifest_digest=manifest_digest),
        design_id=spec.design_id,
        spec_digest=spec_digest,
        plan_digest=plan_digest,
        manifest_digest=manifest_digest,
        artifacts=entries,
        external_refs=spec.external_refs,
    )
    return Compilation(
        spec=spec,
        report=report,
        plan=plan,
        bundle=bundle,
        artifacts=MappingProxyType(artifact_bytes),
    )


__all__ = ["assemble_compilation"]
