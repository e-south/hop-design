"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_sequence_domain.py

Checks basal source domains and exact materialization against molecular solutions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from dataclasses import replace
from itertools import product

import pytest

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.kernel.construction.basal import BasalPlacementFailure, iter_basal_program_solutions
from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint
from hop_design.models.enzymes import EnzymeClass
from hop_design.models.physical import Strand
from hop_design.models.sequence import reverse_complement_iupac
from tests.contract.test_basal_construction_discovery import _enzyme, _pairing_constraints, _request


def _unit(*, strand=Strand.TOP, adapter_bases=None):
    constraints = _pairing_constraints((BasalPairAllowance.MATCH,) * 4)
    if adapter_bases is not None:
        constraints = (
            constraints[0].model_copy(update={"allowed_adapter_bases": adapter_bases}),
            *constraints[1:],
        )
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload="CCCC" if strand is Strand.TOP else "TTCC",
        pairing_constraints=constraints,
    )
    request = request.model_copy(
        update={
            "geometry_domain": request.geometry_domain.model_copy(update={"nick_strand": strand})
        }
    )
    return request, next(iter_basal_work_units(request, retained_overhead_nt=4))


@pytest.mark.parametrize("strand", [Strand.TOP, Strand.BOTTOM])
def test_canonical_source_domain_has_exact_independent_members(strand):
    from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain

    request, unit = _unit(strand=strand)
    domain = solve_basal_sequence_domain(
        payload_sequence=unit.payload_sequence,
        target=unit.target,
        endpoint=request.endpoint,
        program=unit.program,
    )
    expected = (
        {"".join(bases) + "AACCCC" for bases in product("ACGT", repeat=2)}
        if strand is Strand.TOP
        else {"".join(bases) + "GTTCC" for bases in product("ACGT", repeat=3)}
    )
    source_domains = domain.canonical_source_domains()
    assert {"".join(bases) for bases in product(*source_domains)} == expected
    materialized = [
        domain.materialize(source, reverse_complement_iupac(source[:4]))
        for source in sorted(expected)
    ]
    assert materialized == list(
        iter_basal_program_solutions(
            payload_sequence=unit.payload_sequence,
            target=unit.target,
            endpoint=request.endpoint,
            program=unit.program,
        )
    )


def test_canonical_source_domain_applies_adapter_masks_before_counting():
    from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain

    request, unit = _unit(adapter_bases=("G",))
    domain = solve_basal_sequence_domain(
        payload_sequence=unit.payload_sequence,
        target=unit.target,
        endpoint=request.endpoint,
        program=unit.program,
    )
    assert any(not bases for bases in domain.canonical_source_domains())
    assert not tuple(
        iter_basal_program_solutions(
            payload_sequence=unit.payload_sequence,
            target=unit.target,
            endpoint=request.endpoint,
            program=unit.program,
        )
    )


def test_materialization_retains_recognition_context_beyond_the_paired_adapter():
    from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain

    request, unit = _unit()
    enzyme = _enzyme(
        "example:enzyme/extended-footprint@1",
        enzyme_class=EnzymeClass.NICKASE,
        pattern="AACCCCTTNNGN",
        reference_cut=2,
        complement_cut=None,
    )
    program = replace(unit.program, nick_enzyme=enzyme)
    arguments = {
        "payload_sequence": unit.payload_sequence,
        "target": unit.target,
        "endpoint": request.endpoint,
        "program": program,
    }
    solutions = list(iter_basal_program_solutions(**arguments))
    assert len(solutions) == 64
    assert solutions[0].source_precursor_sequence == "AAAACCCC"
    assert solutions[0].adapter_sequence == "TTTTGA"
    assert solutions[3].adapter_sequence == "TTTTGT"
    assert len(solutions[0].pairing_state.pairs) == 4
    domain = solve_basal_sequence_domain(**arguments)
    assert len(domain.canonical_source_domains()) == 8
    assert domain.materialize("AAAACCCC", "TTTTGA") == solutions[0]
    assert domain.materialize_canonical_source("AAAACCCC") == solutions[0]


def test_domain_preserves_placement_exclusion_before_sequence_allocation():
    from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain

    request, unit = _unit()
    result = solve_basal_sequence_domain(
        payload_sequence="TTCC", target=unit.target, endpoint=request.endpoint, program=unit.program
    )
    assert result == BasalPlacementFailure("recognition-payload-conflict")


def test_canonical_domain_rejects_noncanonical_pair_permissions():
    from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain

    request = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    unit = next(iter_basal_work_units(request, retained_overhead_nt=4))
    domain = solve_basal_sequence_domain(
        payload_sequence=unit.payload_sequence,
        target=unit.target,
        endpoint=request.endpoint,
        program=unit.program,
    )
    with pytest.raises(ValueError, match="canonical"):
        domain.canonical_source_domains()


@pytest.mark.parametrize(
    "source,adapter", [("AACCCC", "TTTT"), ("AAAACCCC", "GGGG"), ("ACACCCCC", "GTGT")]
)
def test_materialization_rejects_sequences_outside_the_solved_domain(source, adapter):
    from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain

    request, unit = _unit()
    domain = solve_basal_sequence_domain(
        payload_sequence=unit.payload_sequence,
        target=unit.target,
        endpoint=request.endpoint,
        program=unit.program,
    )
    with pytest.raises(ValueError):
        domain.materialize(source, adapter)
