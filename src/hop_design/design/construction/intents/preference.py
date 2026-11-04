"""Capture a supplied preparation as portable search-order evidence."""

from pathlib import Path

from hop_design.export.publication import ProtectedRoot
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.construction.comparisons.materials import SelectedPreparationReference
from hop_design.models.construction.surveys.preference import SurveyPreparationReference
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..complete.bundle import load_verified_construction_bundle
from ..selection_reference import load_construction_selection

PREFERENCE_DIRECTORY = "preferred-preparation"
PREFERENCE_SELECTION = "preferred-selection.json"


def capture_preference(
    reference: SelectedPreparationReference, directory: Path
) -> tuple[
    SelectedPreparationReference,
    SurveyPreparationReference,
    dict[str, bytes],
    tuple[ProtectedRoot, ...],
]:
    """Replay the input; capture its authority, never its result as a new witness."""
    bundle = ProtectedRoot.capture(directory / reference.bundle_path)
    selection_root = ProtectedRoot.capture(directory / reference.selection_path)
    receipt = load_verified_construction_bundle(bundle.path)
    selection = load_construction_selection(selection_root.path, receipt=receipt)
    if receipt.endpoint != "clone_ready_duplex":
        raise ValueError("A preferred preparation must contain a released insert.")
    contents = {
        "construction-bundle.json": canonical_json_bytes(receipt._bundle),
        **receipt._artifacts,
    }
    media_types = {entry.path: entry.media_type for entry in receipt._bundle.artifacts}
    binding = SurveyPreparationReference(
        result_id=receipt.result_id,
        materialized_realization_id=selection.materialized_realization_id,
        files=tuple(
            ArtifactManifestEntry(
                path=name,
                media_type=media_types.get(name, "application/json"),
                digest=sha256_digest(data),
                size_bytes=len(data),
            )
            for name, data in sorted(contents.items())
        ),
    )
    bundle.require_unchanged()
    selection_root.require_unchanged()
    files = {f"{PREFERENCE_DIRECTORY}/{name}": data for name, data in contents.items()}
    files[PREFERENCE_SELECTION] = selection.json_bytes
    return (
        SelectedPreparationReference(
            bundle_path=PREFERENCE_DIRECTORY, selection_path=PREFERENCE_SELECTION
        ),
        binding,
        files,
        (bundle, selection_root),
    )
