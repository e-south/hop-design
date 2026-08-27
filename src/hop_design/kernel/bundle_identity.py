"""One authority for bundle content identity."""

from __future__ import annotations

from collections.abc import Sequence

from hop_design.models.bundle import ArtifactManifestEntry, HopBundle, MethodBundle
from hop_design.models.design_space import HairpinDesignSet
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


def design_set_manifest_seed(design_set: HairpinDesignSet) -> dict[str, object]:
    """Return design-set content that participates in its identity."""
    data = design_set.model_dump(mode="json", by_alias=True)
    data.pop("design_set_id")
    data.pop("manifest_digest")
    return data


def manifest_digest_for_design_set(design_set: HairpinDesignSet) -> str:
    """Recompute the manifest digest of a loaded design set."""
    return sha256_digest(canonical_json_bytes(design_set_manifest_seed(design_set)))


def design_set_id(*, manifest_digest: str) -> str:
    """Derive a stable design-set identifier from its manifest digest."""
    suffix = manifest_digest.removeprefix("sha256:")[:16]
    return f"hop:design-set/{suffix}"


def method_manifest_seed(
    *,
    request_id: str,
    method_kind: str,
    compiler_version: str,
    request_digest: str,
    plan_digest: str,
    hairpin_encoding_digest: str,
    artifacts: Sequence[ArtifactManifestEntry],
) -> dict[str, object]:
    """Return the canonical identity seed for one method bundle."""
    return {
        "artifacts": [item.model_dump(mode="json") for item in artifacts],
        "compiler_version": compiler_version,
        "hairpin_encoding_digest": hairpin_encoding_digest,
        "method_kind": method_kind,
        "plan_digest": plan_digest,
        "request_digest": request_digest,
        "request_id": request_id,
    }


def manifest_digest_for_method_bundle(bundle: MethodBundle) -> str:
    """Recompute the content identity of a loaded method bundle."""
    return sha256_digest(
        canonical_json_bytes(
            method_manifest_seed(
                request_id=bundle.request_id,
                method_kind=bundle.method_kind,
                compiler_version=bundle.compiler_version,
                request_digest=bundle.request_digest,
                plan_digest=bundle.plan_digest,
                hairpin_encoding_digest=bundle.hairpin_encoding_digest,
                artifacts=bundle.artifacts,
            )
        )
    )


def method_bundle_id(*, request_id: str, manifest_digest: str) -> str:
    """Derive a stable method-bundle id without embedding a caller path."""
    request_suffix = sha256_digest(request_id.encode()).removeprefix("sha256:")[:12]
    content_suffix = manifest_digest.removeprefix("sha256:")[:16]
    return f"hop:method-bundle/{request_suffix}/{content_suffix}"
