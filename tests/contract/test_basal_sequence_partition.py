"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_sequence_partition.py

Checks exact basal sequence outcomes selected before molecular materialization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import pytest

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.kernel.construction.basal import BasalPlacementFailure, iter_basal_program_solutions
from hop_design.models.construction import ConstructionEndpoint, SequenceDomainPartition
from hop_design.models.physical import Strand
from tests.contract.test_basal_construction_discovery import _request


def _outcomes(request, unit, partition=None):
    options = {} if partition is None else {"sequence_partition": partition}
    return tuple(
        iter_basal_program_solutions(
            payload_sequence=unit.payload_sequence,
            target=unit.target,
            endpoint=request.endpoint,
            program=unit.program,
            **options,
        )
    )


@pytest.mark.parametrize(
    "endpoint", [ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, ConstructionEndpoint.CLONE_READY_DUPLEX]
)
@pytest.mark.parametrize("strand", [Strand.TOP, Strand.BOTTOM])
@pytest.mark.parametrize("pair_cap", [None, 0])
@pytest.mark.parametrize("part_count", [2, 5])
def test_selected_basal_outcomes_equal_the_canonical_modulo_subsequence(
    endpoint, strand, pair_cap, part_count
):
    request = _request(endpoint, payload="CCCC" if strand is Strand.TOP else "TTCC")
    request = request.model_copy(
        update={
            "geometry_domain": request.geometry_domain.model_copy(
                update={"nick_strand": strand, "max_noncanonical_pairs": pair_cap}
            )
        }
    )
    units = tuple(iter_basal_work_units(request, retained_overhead_nt=4))
    assert units
    for unit in units:
        complete = _outcomes(request, unit)
        if strand is Strand.TOP and endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            assert complete
        for part_index in range(part_count):
            partition = SequenceDomainPartition(part_count=part_count, part_index=part_index)
            assert _outcomes(request, unit, partition) == complete[part_index::part_count]


@pytest.mark.parametrize("failure", ["recognition-payload-conflict", "basal-source-conflict"])
def test_a_single_placement_failure_belongs_only_to_the_first_part(failure):
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload="TTCC" if failure == "recognition-payload-conflict" else "CCCC",
    )
    if failure == "basal-source-conflict":
        constraints = request.geometry_domain.pairing_constraints
        request = request.model_copy(
            update={
                "geometry_domain": request.geometry_domain.model_copy(
                    update={
                        "pairing_constraints": (
                            constraints[0].model_copy(update={"allowed_source_bases": ("C",)}),
                            *constraints[1:],
                        )
                    }
                )
            }
        )
    unit = next(iter_basal_work_units(request, retained_overhead_nt=4))
    assert _outcomes(request, unit) == (BasalPlacementFailure(failure),)
    assert _outcomes(request, unit, SequenceDomainPartition(part_count=256, part_index=0)) == (
        BasalPlacementFailure(failure),
    )
    assert _outcomes(request, unit, SequenceDomainPartition(part_count=256, part_index=255)) == ()
