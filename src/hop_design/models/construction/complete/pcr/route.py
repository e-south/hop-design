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
from hop_design.models.construction.payload import SourceOrientation
from hop_design.models.molecular_state import MolecularStrand
from hop_design.models.reactions import ReactionProgram

from ..evaluation_inputs import replay_linear_source_embedding
from ..material import ExactConstructionMaterial
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
    prefix, _, embedding = replay_linear_source_embedding(
        foldback=foldback,
        source_sequence=source.sequence_5prime,
        complement_sequence=source_complement.sequence_5prime,
    )
    if len(prefix) != prefix_length:
        raise ValueError("PCR prefix length must equal the exact source embedding.")
    return derive_post_cleavage_strands(
        reaction.states[-1].molecules,
        namespace="pcr-enzyme-product",
        foldback=foldback,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
    )


def select_pcr_fragments(
    molecules: tuple[MolecularStrand, ...],
    *,
    foldback: FoldbackLocalRealization,
    source_material_id: str,
    source_complement_material_id: str,
    source_return_arm: str,
) -> tuple[MolecularStrand, MolecularStrand]:
    """Select exact source fragments after removing the source-return arm."""
    orientation = foldback.payload_source_map.segments[0].orientation
    released_suffix = (
        "-pcr-bottom-source-return-arm-top"
        if orientation is SourceOrientation.FORWARD
        else "-pcr-top-source-return-arm-top"
    )
    released_material_id = (
        source_complement_material_id
        if orientation is SourceOrientation.FORWARD
        else source_material_id
    )
    released = next((item for item in molecules if item.strand_id.endswith(released_suffix)), None)
    if (
        released is None
        or released.sequence != source_return_arm
        or any(item.origin_id != released_material_id for item in released.lineage)
    ):
        raise ValueError("PCR basal nick must create the exact removable source-return fragment.")
    selected = tuple(
        item
        for item in molecules
        if item.strand_id != released.strand_id
        and not any(
            item.strand_id.endswith(fragment_id + "-top")
            for fragment_id in foldback.released_fragment_ids
        )
    )

    def exact_ligation_strand(local_id: str) -> MolecularStrand | None:
        matches = tuple(item for item in selected if f"-{local_id}-" in item.strand_id)
        return matches[0] if len(matches) == 1 else None

    upstream = exact_ligation_strand(foldback.ligation_bond.upstream_strand_id)
    downstream = exact_ligation_strand(foldback.ligation_bond.downstream_strand_id)
    if upstream is None or downstream is None or upstream.strand_id == downstream.strand_id:
        raise ValueError("PCR fragment selection must bind exact retained local identities.")
    return upstream, downstream


__all__ = ["pcr_cleaved_strands", "select_pcr_fragments"]
