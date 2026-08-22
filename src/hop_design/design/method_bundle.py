"""Replay-verified artifact boundary for one complete production-method plan."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from types import MappingProxyType

from hop_design.design.linear_source_method import (
    compile_linear_source_multinick_hairpin_pcr,
)
from hop_design.design.method_views import build_method_trajectory_view
from hop_design.export.bundle import (
    BundleIntegrityError,
    verify_manifested_bundle_contents,
    write_manifested_bundle_files,
)
from hop_design.export.fasta import render_fasta, render_fasta_records
from hop_design.export.genbank import render_hairpin_pcr_genbank
from hop_design.export.svg import render_workflow_svg
from hop_design.kernel.bundle_identity import (
    manifest_digest_for_method_bundle,
    method_bundle_id,
    method_manifest_seed,
)
from hop_design.models.bundle import ArtifactManifestEntry, MethodBundle
from hop_design.models.linear_source_method import (
    LinearSourceMultinickHairpinPcrPlan,
    LinearSourceMultinickHairpinPcrRequest,
    LinearSourceMultinickHairpinPcrResult,
)
from hop_design.models.method import MethodKind
from hop_design.models.plan import SequenceRecord
from hop_design.serialization import canonical_json_bytes, sha256_digest

_MANIFEST_NAME = "method-bundle.json"
_MEDIA_TYPES = {
    "hairpin-encoding.fasta": "text/x-fasta",
    "hairpin-pcr-duplex.fasta": "text/x-fasta",
    "hairpin-pcr-duplex.gb": "text/plain; format=genbank",
    "method-plan.json": "application/json",
    "method-request.json": "application/json",
    "method-trajectory.json": "application/json",
    "method-trajectory.svg": "image/svg+xml",
    "restriction-product.fasta": "text/x-fasta",
}


class MethodResolutionError(ValueError):
    """Raised when a complete method plan is required but resolution is infeasible."""

    def __init__(self, result: LinearSourceMultinickHairpinPcrResult) -> None:
        self.result = result
        codes = ", ".join(item.code for item in result.outcome.diagnostics)
        super().__init__(f"HOP method did not resolve a complete plan: {codes}")


@dataclass(frozen=True)
class MethodCompilation:
    """One complete method result, portable manifest, and generated artifacts."""

    request: LinearSourceMultinickHairpinPcrRequest
    result: LinearSourceMultinickHairpinPcrResult
    bundle: MethodBundle
    artifacts: Mapping[str, bytes]

    def write(self, output: str | Path) -> Path:
        """Atomically write this method bundle after complete semantic verification."""
        return write_method_bundle(self, Path(output))


@dataclass(frozen=True)
class VerifiedMethodBundle:
    """Method content admitted only after integrity checks and semantic replay."""

    bundle: MethodBundle
    request: LinearSourceMultinickHairpinPcrRequest
    plan: LinearSourceMultinickHairpinPcrPlan
    artifacts: Mapping[str, bytes]


def _sequence_record(record_id: str, sequence: str) -> SequenceRecord:
    return SequenceRecord(record_id=record_id, sequence=sequence)


def _method_artifacts(
    request: LinearSourceMultinickHairpinPcrRequest,
    plan: LinearSourceMultinickHairpinPcrPlan,
) -> dict[str, bytes]:
    duplex = plan.hairpin_pcr_duplex
    restriction = plan.restriction_digest_product
    trajectory = build_method_trajectory_view(plan)
    return {
        "hairpin-encoding.fasta": render_fasta(
            _sequence_record(
                "hairpin-encoding",
                restriction.hairpin_encoding_projection.sequence,
            )
        ),
        "hairpin-pcr-duplex.fasta": render_fasta_records(
            (
                _sequence_record("hairpin-pcr-top", duplex.top_strand.sequence),
                _sequence_record("hairpin-pcr-bottom", duplex.bottom_strand.sequence),
            )
        ),
        "hairpin-pcr-duplex.gb": render_hairpin_pcr_genbank(plan),
        "method-plan.json": canonical_json_bytes(plan),
        "method-request.json": canonical_json_bytes(request),
        "method-trajectory.json": canonical_json_bytes(trajectory),
        "method-trajectory.svg": render_workflow_svg(trajectory),
        "restriction-product.fasta": render_fasta_records(
            (
                _sequence_record(
                    "restriction-primary",
                    restriction.primary_strand.sequence,
                ),
                _sequence_record(
                    "restriction-complementary",
                    restriction.complementary_strand.sequence,
                ),
            )
        ),
    }


def compile_linear_source_method_bundle(
    request: LinearSourceMultinickHairpinPcrRequest,
) -> MethodCompilation:
    """Compile one complete method plan into replayable portable artifacts."""
    result = compile_linear_source_multinick_hairpin_pcr(request)
    if result.plan is None:
        raise MethodResolutionError(result)
    plan = result.plan
    compiler_version = version("hop-design")
    artifacts = _method_artifacts(request, plan)
    entries = tuple(
        ArtifactManifestEntry(
            path=path,
            media_type=_MEDIA_TYPES[path],
            digest=sha256_digest(content),
            size_bytes=len(content),
        )
        for path, content in sorted(artifacts.items())
    )
    request_digest = sha256_digest(artifacts["method-request.json"])
    plan_digest = sha256_digest(artifacts["method-plan.json"])
    hairpin_encoding_digest = sha256_digest(
        plan.restriction_digest_product.hairpin_encoding_projection.sequence.encode()
    )
    manifest_digest = sha256_digest(
        canonical_json_bytes(
            method_manifest_seed(
                request_id=request.request_id,
                method_kind=request.method_kind,
                compiler_version=compiler_version,
                request_digest=request_digest,
                plan_digest=plan_digest,
                hairpin_encoding_digest=hairpin_encoding_digest,
                artifacts=entries,
            )
        )
    )
    bundle = MethodBundle(
        bundle_id=method_bundle_id(
            request_id=request.request_id,
            manifest_digest=manifest_digest,
        ),
        request_id=request.request_id,
        method_kind=MethodKind(request.method_kind),
        compiler_version=compiler_version,
        request_digest=request_digest,
        plan_digest=plan_digest,
        hairpin_encoding_digest=hairpin_encoding_digest,
        manifest_digest=manifest_digest,
        artifacts=entries,
    )
    return MethodCompilation(
        request=request,
        result=result,
        bundle=bundle,
        artifacts=MappingProxyType(artifacts),
    )


def load_verified_method_bundle(bundle_path: str | Path) -> VerifiedMethodBundle:
    """Load one method bundle only after byte integrity and full semantic replay."""
    bundle, artifact_mapping = verify_manifested_bundle_contents(
        bundle_path,
        manifest_name=_MANIFEST_NAME,
        manifest_model=MethodBundle,
    )
    artifacts = dict(artifact_mapping)
    missing = sorted(set(_MEDIA_TYPES) - artifacts.keys())
    extra = sorted(artifacts.keys() - set(_MEDIA_TYPES))
    if missing or extra:
        raise BundleIntegrityError(
            f"Method bundle artifact set differs from its schema; missing={missing}, extra={extra}."
        )
    if manifest_digest_for_method_bundle(bundle) != bundle.manifest_digest:
        raise BundleIntegrityError("Method bundle manifest digest mismatch.")
    if (
        method_bundle_id(
            request_id=bundle.request_id,
            manifest_digest=bundle.manifest_digest,
        )
        != bundle.bundle_id
    ):
        raise BundleIntegrityError("Method bundle identifier does not match its content digest.")
    if sha256_digest(artifacts["method-request.json"]) != bundle.request_digest:
        raise BundleIntegrityError("Method request digest does not match the root manifest.")
    if sha256_digest(artifacts["method-plan.json"]) != bundle.plan_digest:
        raise BundleIntegrityError("Method plan digest does not match the root manifest.")
    try:
        request = LinearSourceMultinickHairpinPcrRequest.model_validate_json(
            artifacts["method-request.json"]
        )
        plan = LinearSourceMultinickHairpinPcrPlan.model_validate_json(
            artifacts["method-plan.json"]
        )
    except Exception as exc:
        raise BundleIntegrityError(f"Method request or plan is invalid: {exc}") from exc
    if request.request_id != bundle.request_id or plan.request_id != bundle.request_id:
        raise BundleIntegrityError("Method bundle request identity is inconsistent.")
    if request.method_kind != bundle.method_kind or plan.method_kind != bundle.method_kind:
        raise BundleIntegrityError("Method bundle kind is inconsistent.")
    if plan.request_digest != bundle.request_digest:
        raise BundleIntegrityError("Method plan does not reference its exact request.")
    observed_encoding_digest = sha256_digest(
        plan.restriction_digest_product.hairpin_encoding_projection.sequence.encode()
    )
    if observed_encoding_digest != bundle.hairpin_encoding_digest:
        raise BundleIntegrityError("Method bundle hairpin-encoding digest is inconsistent.")
    try:
        expected = compile_linear_source_method_bundle(request)
    except Exception as exc:
        raise BundleIntegrityError(f"Method request cannot be replayed: {exc}") from exc
    if canonical_json_bytes(expected.result.plan) != canonical_json_bytes(plan):
        raise BundleIntegrityError("Method request and plan disagree after deterministic replay.")
    if dict(expected.artifacts) != artifacts:
        raise BundleIntegrityError("Method artifacts disagree with deterministic replay.")
    if expected.bundle != bundle:
        raise BundleIntegrityError("Method manifest disagrees with deterministic replay.")
    return VerifiedMethodBundle(
        bundle=bundle,
        request=request,
        plan=plan,
        artifacts=MappingProxyType(artifacts),
    )


def verify_method_bundle(bundle_path: str | Path) -> MethodBundle:
    """Verify one method bundle and return its root manifest."""
    return load_verified_method_bundle(bundle_path).bundle


def write_method_bundle(compilation: MethodCompilation, output: Path) -> Path:
    """Write one method bundle atomically after complete semantic verification."""
    return write_manifested_bundle_files(
        compilation,
        output,
        manifest_name=_MANIFEST_NAME,
        verifier=verify_method_bundle,
    )


__all__ = [
    "MethodCompilation",
    "MethodResolutionError",
    "VerifiedMethodBundle",
    "compile_linear_source_method_bundle",
    "load_verified_method_bundle",
    "verify_method_bundle",
    "write_method_bundle",
]
