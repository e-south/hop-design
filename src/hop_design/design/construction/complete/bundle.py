"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/bundle.py

Compiles and replays portable complete-construction authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Self

from hop_design.design.bundle import load_verified_bundle
from hop_design.design.construction.verification import (
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.export.bundle import (
    BundleIntegrityError,
    verify_manifested_bundle_contents,
    write_manifested_bundle_files,
)
from hop_design.kernel.bundle_identity import (
    construction_bundle_id,
    construction_manifest_seed,
    manifest_digest_for_construction_bundle,
)
from hop_design.models.bundle import ArtifactManifestEntry, HopBundle
from hop_design.models.construction import ConstructionBundle
from hop_design.models.construction.complete import ConstructionSpaceResult
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .authority_content import (
    DESIGN_MANIFEST_PATH,
    DESIGN_ROOT,
    RESULT_PATH,
    artifact_media_types,
    construction_artifacts,
    expected_artifact_paths,
)
from .discovery import (
    VerifiedConstructionSpaceResult,
    verify_construction_space_result,
)

_MANIFEST_NAME = "construction-bundle.json"


@dataclass(frozen=True)
class _WritableConstruction:
    """Internal adapter for the generic manifested-bundle writer."""

    bundle: ConstructionBundle
    artifacts: Mapping[str, bytes]


class _ConstructionReceipt:
    """Shared scalar receipt over one private construction authority."""

    _construction: VerifiedConstructionSpaceResult
    _bundle: ConstructionBundle

    @property
    def bundle_id(self) -> str:
        """Return the portable construction authority identity."""
        return self._bundle.bundle_id

    @property
    def result_id(self) -> str:
        """Return the exact complete-construction result identity."""
        return self._bundle.result_id

    @property
    def design_bundle_id(self) -> str:
        """Return the embedded verified design authority identity."""
        return self._bundle.design_bundle_id

    @property
    def status(self) -> str:
        """Return complete, infeasible, or truncated discovery status."""
        return self._construction.result.status.value

    @property
    def endpoint(self) -> str:
        """Return the requested construction endpoint."""
        return self._construction.result.request.endpoint.value

    @property
    def valid_realizations(self) -> int:
        """Return the number of accepted exact route realizations."""
        return self._construction.result.accounting.valid_realizations

    @property
    def examined_combinations(self) -> int:
        """Return the number of local combinations actually examined."""
        return self._construction.result.accounting.examined_combinations

    @property
    def nominal_combinations(self) -> int:
        """Return the declared complete local cross-product cardinality."""
        return self._construction.result.accounting.nominal_combinations

    @property
    def materialized_realization_ids(self) -> tuple[str, ...]:
        """Return accepted exact route identities in canonical order."""
        return tuple(
            item.materialized_realization_id for item in self._construction.result.realizations
        )

    def _verified_source(self) -> VerifiedConstructionSpaceResult:
        return self._construction

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(bundle_id={self.bundle_id!r}, "
            f"status={self.status!r}, endpoint={self.endpoint!r}, "
            f"valid_realizations={self.valid_realizations})"
        )


@dataclass(frozen=True, init=False, repr=False)
class ConstructionCompilation(_ConstructionReceipt):
    """One write-capable receipt over a verified construction authority."""

    _construction: VerifiedConstructionSpaceResult
    _bundle: ConstructionBundle
    _artifacts: Mapping[str, bytes]

    @classmethod
    def _create(
        cls,
        *,
        construction: VerifiedConstructionSpaceResult,
        bundle: ConstructionBundle,
        artifacts: Mapping[str, bytes],
    ) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_construction", construction)
        object.__setattr__(instance, "_bundle", bundle)
        object.__setattr__(instance, "_artifacts", MappingProxyType(dict(artifacts)))
        return instance

    def write(self, output: str | Path) -> Path:
        """Atomically write the construction bundle after complete replay."""
        return write_construction_bundle(self, Path(output))


@dataclass(frozen=True, init=False, repr=False)
class VerifiedConstructionBundle(_ConstructionReceipt):
    """Read-only receipt over replay-verified construction content."""

    _construction: VerifiedConstructionSpaceResult
    _bundle: ConstructionBundle
    _artifacts: Mapping[str, bytes]

    @classmethod
    def _create(
        cls,
        *,
        construction: VerifiedConstructionSpaceResult,
        bundle: ConstructionBundle,
        artifacts: Mapping[str, bytes],
    ) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_construction", construction)
        object.__setattr__(instance, "_bundle", bundle)
        object.__setattr__(instance, "_artifacts", MappingProxyType(dict(artifacts)))
        return instance


def compile_construction_bundle(
    construction: VerifiedConstructionSpaceResult,
) -> ConstructionCompilation:
    """Compile only a replay-verified complete-construction result."""
    if not isinstance(construction, VerifiedConstructionSpaceResult):
        raise TypeError("Construction bundle compilation requires a verified result.")
    construction = verify_construction_space_result(
        construction.result,
        foldback=construction.foldback,
        basal=construction.basal,
        design=construction.design,
    )
    artifacts = construction_artifacts(construction)
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
    bundle = ConstructionBundle(
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
    return ConstructionCompilation._create(
        construction=construction,
        bundle=bundle,
        artifacts=artifacts,
    )


def load_verified_construction_bundle(
    bundle_path: str | Path,
) -> VerifiedConstructionBundle:
    """Load one construction bundle after exact authority replay."""
    root = Path(bundle_path)
    bundle, artifact_mapping = verify_manifested_bundle_contents(
        root,
        manifest_name=_MANIFEST_NAME,
        manifest_model=ConstructionBundle,
    )
    artifacts = dict(artifact_mapping)
    try:
        embedded_design = HopBundle.model_validate_json(artifacts[DESIGN_MANIFEST_PATH])
    except KeyError as exc:
        raise BundleIntegrityError("Construction bundle omits its design manifest.") from exc
    except Exception as exc:
        raise BundleIntegrityError(f"Construction design manifest is invalid: {exc}") from exc
    expected_paths = expected_artifact_paths(embedded_design)
    if set(artifacts) != expected_paths:
        missing = sorted(expected_paths - artifacts.keys())
        extra = sorted(artifacts.keys() - expected_paths)
        raise BundleIntegrityError(
            "Construction bundle artifact set differs from its schema; "
            f"missing={missing}, extra={extra}."
        )
    if manifest_digest_for_construction_bundle(bundle) != bundle.manifest_digest:
        raise BundleIntegrityError("Construction bundle manifest digest mismatch.")
    if (
        construction_bundle_id(
            result_id=bundle.result_id,
            manifest_digest=bundle.manifest_digest,
        )
        != bundle.bundle_id
    ):
        raise BundleIntegrityError("Construction bundle identifier does not match its content.")
    if sha256_digest(artifacts[RESULT_PATH]) != bundle.result_digest:
        raise BundleIntegrityError("Construction result digest does not match the root manifest.")
    design = load_verified_bundle(root / DESIGN_ROOT)
    if design.bundle != embedded_design or design.bundle.bundle_id != bundle.design_bundle_id:
        raise BundleIntegrityError("Construction design authority is inconsistent.")
    try:
        result = ConstructionSpaceResult.model_validate_json(artifacts[RESULT_PATH])
    except Exception as exc:
        raise BundleIntegrityError(f"Construction result is invalid: {exc}") from exc
    if result.result_id != bundle.result_id:
        raise BundleIntegrityError("Construction result identity is inconsistent.")
    try:
        foldback = verify_foldback_neighborhood_result(result.foldback_authority)
        basal = (
            None
            if result.basal_authority is None
            else verify_basal_neighborhood_result(result.basal_authority)
        )
        construction = verify_construction_space_result(
            result,
            foldback=foldback,
            basal=basal,
            design=design,
        )
    except Exception as exc:
        raise BundleIntegrityError(f"Construction result cannot be replayed: {exc}") from exc
    expected = compile_construction_bundle(construction)
    if dict(expected._artifacts) != artifacts:
        raise BundleIntegrityError("Construction artifacts disagree with deterministic replay.")
    if expected._bundle != bundle:
        raise BundleIntegrityError("Construction manifest disagrees with deterministic replay.")
    return VerifiedConstructionBundle._create(
        construction=construction,
        bundle=bundle,
        artifacts=artifacts,
    )


def verify_construction_bundle(bundle_path: str | Path) -> ConstructionBundle:
    """Verify one construction bundle and return its root manifest."""
    return load_verified_construction_bundle(bundle_path)._bundle


def write_construction_bundle(
    compilation: ConstructionCompilation,
    output: Path,
) -> Path:
    """Write one construction bundle atomically after semantic replay."""
    return write_manifested_bundle_files(
        _WritableConstruction(
            bundle=compilation._bundle,
            artifacts=compilation._artifacts,
        ),
        output,
        manifest_name=_MANIFEST_NAME,
        verifier=verify_construction_bundle,
    )


__all__ = [
    "ConstructionCompilation",
    "VerifiedConstructionBundle",
    "compile_construction_bundle",
    "load_verified_construction_bundle",
    "verify_construction_bundle",
    "write_construction_bundle",
]
