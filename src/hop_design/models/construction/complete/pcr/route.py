"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/route.py

Replays the exact basal-open source fragments retained by a hairpin PCR route.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import MolecularStrand
from hop_design.models.reactions import ReactionProgram

from ..request import ExactConstructionMaterial
from ..route_lineage import derive_post_cleavage_strands


def pcr_cleaved_strands(
    reaction: ReactionProgram,
    *,
    foldback: FoldbackLocalRealization,
    prefix_length: int,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> tuple[MolecularStrand, ...]:
    """Lift the exact enzyme product into material-coordinate strands."""
    return derive_post_cleavage_strands(
        reaction.states[-1].molecules,
        namespace="pcr-enzyme-product",
        foldback=foldback,
        prefix_length=prefix_length,
        source=source,
        source_complement=source_complement,
    )


def select_pcr_fragments(
    molecules: tuple[MolecularStrand, ...],
    *,
    foldback: FoldbackLocalRealization,
    source_material_id: str,
    source_complement_material_id: str,
    return_arm: str,
) -> tuple[MolecularStrand, MolecularStrand]:
    """Select exact source and return-arm-excluded complement fragment identities."""
    released = next(
        (item for item in molecules if item.strand_id.endswith("-pcr-bottom-return-arm-top")),
        None,
    )
    if (
        released is None
        or released.sequence != return_arm
        or any(item.origin_id != source_complement_material_id for item in released.lineage)
    ):
        raise ValueError("PCR basal nick must create the exact removable return-arm fragment.")
    retained_local_id = foldback.annealing_pairs[0].right_strand_id
    retained = next(
        (
            item
            for item in molecules
            if f"-{retained_local_id}-" in item.strand_id
            and item.strand_id != released.strand_id
            and all(lineage.origin_id == source_complement_material_id for lineage in item.lineage)
        ),
        None,
    )
    source = next(
        (
            item
            for item in molecules
            if all(lineage.origin_id == source_material_id for lineage in item.lineage)
            and not any(
                item.strand_id.endswith(fragment_id + "-top")
                for fragment_id in foldback.released_fragment_ids
            )
        ),
        None,
    )
    if source is None or retained is None:
        raise ValueError("PCR fragment selection must bind exact retained local identities.")
    return source, retained


__all__ = ["pcr_cleaved_strands", "select_pcr_fragments"]
