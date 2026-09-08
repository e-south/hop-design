"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/source.py

Derives the source cleavage and retained strands required for hairpin PCR.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from dataclasses import dataclass

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import MolecularStrand
from hop_design.models.reactions import ReactionProgram
from hop_design.models.sequence import reverse_complement_iupac

from ..basal_embedding import basal_nick_boundary
from ..evaluation_inputs import replay_linear_source_embedding
from ..source_partition.plan import SourcePartitionPlan
from ..source_partition.route import partitioned_source_strands
from ..source_preparation import SourceDuplexPreparationAuthority
from .route import pcr_cleaved_strands, select_pcr_fragments
from .schedule import derive_pcr_reaction_program


@dataclass(frozen=True, slots=True)
class PcrSourceRealization:
    """Exact cleavage program and ordered local survivors before hairpin association."""

    reaction: ReactionProgram
    cleaved: tuple[MolecularStrand, ...]
    selected: tuple[MolecularStrand, MolecularStrand]


def derive_pcr_source(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    preparation: SourceDuplexPreparationAuthority,
    partition: SourcePartitionPlan | None,
) -> PcrSourceRealization:
    """Compose exact local survival requirements with the selected cleanup program."""
    source, complement = (binding.material for binding in preparation.produced_material_bindings)
    top_use, bottom_use = preparation.prepared_top_use, preparation.prepared_bottom_use
    prefix, return_arm, _ = replay_linear_source_embedding(
        foldback=foldback,
        source_sequence=source.sequence_5prime,
        complement_sequence=complement.sequence_5prime,
    )
    local_program = derive_pcr_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        source_return_arm=return_arm,
        source=source,
        source_complement=complement,
    )
    local_strands = pcr_cleaved_strands(
        local_program,
        foldback=foldback,
        prefix_length=len(prefix),
        source=source,
        source_complement=complement,
        source_use_id=top_use.use_id,
        source_complement_use_id=bottom_use.use_id,
    )
    selected = select_pcr_fragments(
        local_strands,
        foldback=foldback,
        source_material_use_id=top_use.use_id,
        source_complement_material_use_id=bottom_use.use_id,
        removed_return_sequence=reverse_complement_iupac(
            prefix[: basal_nick_boundary(basal, prefix)]
        ),
    )
    if partition is None:
        return PcrSourceRealization(local_program, local_strands, selected)
    reaction, cleaved, retained = partitioned_source_strands(
        plan=partition,
        preparation=preparation,
        payload_sequence=foldback.payload_sequence,
        local_program=local_program,
        required_strands=selected,
    )
    return PcrSourceRealization(reaction, cleaved, retained)
