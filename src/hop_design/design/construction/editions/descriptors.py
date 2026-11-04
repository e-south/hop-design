"""Edition-owned descriptor admission with fresh byte checks and detached results."""

from typing import TYPE_CHECKING

from hop_design.models.construction.editions.descriptors import CapturedDescriptorIndex
from hop_design.models.construction.variants.similarity import MolecularDescriptor

if TYPE_CHECKING:
    from .reader import AtlasEdition


class CapturedDescriptors:
    def __init__(self, raw: bytes, edition: "AtlasEdition"):
        content = CapturedDescriptorIndex.model_validate_json(raw)
        if content.snapshot_digest != edition._store.manifest.snapshot_digest:
            raise ValueError("Captured descriptor index disagrees with its schema or snapshot.")
        self._rows = content.preparations
        self._by_identity = {row.identity: row for row in self._rows}
        expected = {m.materialized_realization_id for m in edition._store.manifest.members}
        if len(self._rows) != len(expected) or self._by_identity.keys() != expected:
            raise ValueError("Captured descriptors disagree with edition membership.")
        intent = edition.resolution["intent"]
        endpoint = {
            "hairpin": "ssdna_hairpin",
            "released_insert": "clone_ready_duplex",
            "adapter_ligated_hairpin": "adapter_ligated_hairpin",
        }[intent["product"]]
        if any(p.stem != intent["stem_arm"] or p.endpoint != endpoint for p in self._rows):
            raise ValueError("Captured descriptors disagree with the experimental scope.")

    @staticmethod
    def _copy(row: MolecularDescriptor) -> MolecularDescriptor:
        # Frozen models still contain mutable dictionaries. Values here are
        # numbers, strings and nested tuples; detach all three dictionaries.
        return row.model_copy(
            update={
                "shape": dict(row.shape),
                "sequences": dict(row.sequences),
                "interfaces": None if row.interfaces is None else dict(row.interfaces),
                "retained_terminal_bases": None
                if row.retained_terminal_bases is None
                else dict(row.retained_terminal_bases),
            }
        )

    def all(self) -> tuple[MolecularDescriptor, ...]:
        return tuple(self._copy(row) for row in self._rows)

    def get(self, identity: str) -> MolecularDescriptor:
        return self._copy(self._by_identity[identity])


def descriptor_index(edition: "AtlasEdition") -> CapturedDescriptors:
    # Never infer byte integrity from inode, mtime or a previous successful read.
    raw = edition._store.read("descriptors.json")
    if edition._descriptors is None:
        edition._descriptors = CapturedDescriptors(raw, edition)
    return edition._descriptors


def edition_descriptors(edition: "AtlasEdition") -> tuple[MolecularDescriptor, ...]:
    return descriptor_index(edition).all()
