"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/authority_content.py

Defines canonical construction-authority paths and deterministic artifact bytes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Mapping

from hop_design.kernel.bundle_identity import construction_bundle_id, construction_manifest_seed
from hop_design.models.bundle import ArtifactManifestEntry, HopBundle
from hop_design.models.construction import ConstructionBundle
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .discovery import VerifiedConstructionSpaceResult

RESULT_PATH = "construction-result.json"
DESIGN_ROOT = "authorities/design"
DESIGN_MANIFEST_PATH = f"{DESIGN_ROOT}/hop-bundle.json"


def construction_artifacts(
    construction: VerifiedConstructionSpaceResult,
) -> dict[str, bytes]:
    """Return the canonical artifact bytes for one verified construction result."""
    design = construction.design
    artifacts = {
        RESULT_PATH: canonical_json_bytes(construction.result),
        DESIGN_MANIFEST_PATH: canonical_json_bytes(design.bundle),
    }
    artifacts.update(
        {f"{DESIGN_ROOT}/{path}": content for path, content in design.artifacts.items()}
    )
    return artifacts


def artifact_media_types(
    construction: VerifiedConstructionSpaceResult,
) -> dict[str, str]:
    """Return the declared media type for every canonical artifact path."""
    design_types = {item.path: item.media_type for item in construction.design.bundle.artifacts}
    return {
        RESULT_PATH: "application/json",
        DESIGN_MANIFEST_PATH: "application/json",
        **{f"{DESIGN_ROOT}/{path}": design_types[path] for path in construction.design.artifacts},
    }


def construction_manifest(
    construction: VerifiedConstructionSpaceResult, artifacts: Mapping[str, bytes]
) -> ConstructionBundle:
    """Seal canonical artifact bytes without performing another molecular replay."""
    media_types = artifact_media_types(construction)
    entries = tuple(
        ArtifactManifestEntry(
            path=path,
            media_type=media_types[path],
            digest=sha256_digest(content),
            size_bytes=len(content),
        )
        for path, content in sorted(artifacts.items())
    )
    result_digest = sha256_digest(artifacts[RESULT_PATH])
    seed = construction_manifest_seed(
        result_id=construction.result.result_id,
        design_bundle_id=construction.design.bundle.bundle_id,
        result_digest=result_digest,
        artifacts=entries,
    )
    manifest_digest = sha256_digest(canonical_json_bytes(seed))
    return ConstructionBundle(
        bundle_id=construction_bundle_id(
            result_id=construction.result.result_id,
            manifest_digest=manifest_digest,
        ),
        result_id=construction.result.result_id,
        design_bundle_id=construction.design.bundle.bundle_id,
        result_digest=result_digest,
        manifest_digest=manifest_digest,
        artifacts=entries,
    )


def expected_artifact_paths(design_bundle: HopBundle) -> set[str]:
    """Return the exact artifact inventory implied by an embedded design manifest."""
    return {
        RESULT_PATH,
        DESIGN_MANIFEST_PATH,
        *(f"{DESIGN_ROOT}/{item.path}" for item in design_bundle.artifacts),
    }


__all__ = [
    "DESIGN_MANIFEST_PATH",
    "DESIGN_ROOT",
    "RESULT_PATH",
    "artifact_media_types",
    "construction_artifacts",
    "construction_manifest",
    "expected_artifact_paths",
]
