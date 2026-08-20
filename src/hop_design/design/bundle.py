"""Semantic bundle verification and atomic write orchestration."""

from __future__ import annotations

from pathlib import Path

from hop_design.design.compile import compile_spec
from hop_design.export.bundle import (
    BundleIntegrityError,
    WritableCompilation,
    verify_bundle_contents,
    write_bundle_files,
)
from hop_design.models.bundle import HopBundle
from hop_design.serialization import canonical_json_bytes


def verify_bundle(bundle_path: str | Path) -> HopBundle:
    """Verify content identity and replay the complete spec-to-bundle derivation."""
    contents = verify_bundle_contents(bundle_path)
    try:
        expected = compile_spec(contents.spec)
    except Exception as exc:
        raise BundleIntegrityError(f"Bundle spec cannot be replayed: {exc}") from exc

    if canonical_json_bytes(expected.plan) != canonical_json_bytes(contents.plan):
        raise BundleIntegrityError("Bundle spec and plan disagree after deterministic replay.")
    if dict(expected.artifacts) != dict(contents.artifacts):
        raise BundleIntegrityError(
            "Bundle artifacts disagree with the deterministic spec-to-plan replay."
        )
    if expected.bundle != contents.bundle:
        raise BundleIntegrityError(
            "Bundle manifest disagrees with the deterministic spec-to-plan replay."
        )
    return contents.bundle


def write_bundle(compilation: WritableCompilation, output: Path) -> Path:
    """Write one bundle atomically only after complete semantic verification."""
    return write_bundle_files(compilation, output, verifier=verify_bundle)


__all__ = ["verify_bundle", "write_bundle"]
