"""One authority for bundle content identity."""

from __future__ import annotations

from collections.abc import Sequence

from hop_design.models.bundle import ArtifactManifestEntry, HopBundle
from hop_design.models.references import ExternalRef
from hop_design.serialization import canonical_json_bytes, sha256_digest


def manifest_seed(
    *,
    design_id: str,
    spec_digest: str,
    plan_digest: str,
    artifacts: Sequence[ArtifactManifestEntry],
    external_refs: Sequence[ExternalRef],
) -> dict[str, object]:
    """Return the canonical payload used to derive a bundle manifest digest."""
    return {
        "artifacts": [item.model_dump(mode="json") for item in artifacts],
        "design_id": design_id,
        "external_refs": [item.model_dump(mode="json") for item in external_refs],
        "plan_digest": plan_digest,
        "spec_digest": spec_digest,
    }


def manifest_digest_for_bundle(bundle: HopBundle) -> str:
    """Recompute the manifest digest of a loaded bundle."""
    seed = manifest_seed(
        design_id=bundle.design_id,
        spec_digest=bundle.spec_digest,
        plan_digest=bundle.plan_digest,
        artifacts=bundle.artifacts,
        external_refs=bundle.external_refs,
    )
    return sha256_digest(canonical_json_bytes(seed))


def bundle_id(*, design_id: str, manifest_digest: str) -> str:
    """Derive the stable public bundle identifier from its manifest digest."""
    suffix = manifest_digest.removeprefix("sha256:")[:16]
    return f"hop:bundle/{design_id}/{suffix}"
