"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/reaction.py

Derives the concurrent nick program and exact products of a source partition.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.models.construction.payload import _content_id
from hop_design.models.construction.source_partition.result import SourcePartitionRealization
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.junction import Strand
from hop_design.models.reactions import (
    DeclaredEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionProgram,
    ReactionStage,
    ReactionState,
)


def derive_partition_reaction_program(realization: SourcePartitionRealization) -> ReactionProgram:
    """Translate replay-verified partition facts without searching or selecting fragments."""
    duplex = realization.nicked_duplex
    source = ReactionState(
        state_id="partition-source-duplex",
        molecules=(
            ReactionMolecule(
                molecule_id="partition-source",
                reference_sequence_5prime=duplex.top_strand.sequence,
                complement_sequence_5prime=duplex.bottom_strand.sequence,
            ),
        ),
    )
    products = ReactionState(
        state_id="partition-cleavage-products",
        molecules=tuple(
            ReactionMolecule(
                molecule_id=fragment.fragment_id,
                reference_sequence_5prime=fragment.sequence,
                complement_sequence_5prime=None,
            )
            for fragment in realization.denatured.fragments
        ),
    )
    stage = ReactionStage(
        stage_id="partition-concurrent-nicks",
        pre_state_id=source.state_id,
        post_state_id=products.state_id,
        operations=tuple(
            ReactionOperation(
                operation_id=f"partition-nick-{index}",
                enzyme_id=site.agent_id,
                role=EnzymeRole.STRAND_EXPOSURE,
                molecule_id=source.molecules[0].molecule_id,
                intended_binding=DeclaredEnzymeBinding(
                    recognition_span=site.site_span,
                    orientation=site.orientation,
                    reference_cut=site.nick.boundary if site.nick.strand is Strand.TOP else None,
                    complement_cut=site.nick.boundary
                    if site.nick.strand is Strand.BOTTOM
                    else None,
                ),
            )
            for index, site in enumerate(duplex.sites)
        ),
    )
    states = (source, products)
    stages = (stage,)
    digest = (
        _content_id(
            "partition-reaction",
            1,
            {
                "states": tuple(state.model_dump(mode="json") for state in states),
                "stages": tuple(item.model_dump(mode="json") for item in stages),
            },
        )
        .split("/")[-1]
        .split("@")[0]
    )
    return ReactionProgram(program_id=f"partition-reaction-{digest}", states=states, stages=stages)


__all__ = ["derive_partition_reaction_program"]
