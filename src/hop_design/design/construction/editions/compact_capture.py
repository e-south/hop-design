"""Capture one verified preparation without rendering its processing scenes."""

from pathlib import Path
from tempfile import TemporaryDirectory

from hop_design.models.construction.variants.similarity import MolecularDescriptor

from ..intents.base import Source
from ..navigation.molecular_descriptor import molecular_descriptor
from .materials import archive_materials, route_from_materials
from .retrieval import RetrievePreparation
from .storage import DirectoryFiles


def capture_member(
    retrieve: RetrievePreparation,
    selection: Source,
    member: Path,
    identity: str,
    *,
    recorded_descriptor: MolecularDescriptor | None = None,
) -> MolecularDescriptor:
    with TemporaryDirectory(prefix="hop-edition-member-") as temporary:
        materials = Path(temporary) / "materials"
        receipt = retrieve(selection, materials)
        if receipt.materialized_realization_ids != (identity,):
            raise ValueError("Captured material handoff disagrees with the selected preparation.")
        route = route_from_materials(DirectoryFiles(materials), identity)
        descriptor = molecular_descriptor(route)
        if recorded_descriptor is not None:
            # Check the original feature scope against the retrieved authority.
            # A storage conversion or metric experiment must not introduce v2 tails.
            if recorded_descriptor.retained_terminal_bases is None:
                descriptor = descriptor.model_copy(update={"retained_terminal_bases": None})
            if descriptor != recorded_descriptor:
                raise ValueError(
                    "Recorded molecular descriptor disagrees with retrieved materials."
                )
            descriptor = recorded_descriptor
        archive_materials(materials, member / "evidence.zip")
    return descriptor
