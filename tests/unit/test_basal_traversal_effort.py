"""Geometry excludes irrelevant overhead levels before enzyme program construction."""

import pytest

from hop_design.design.construction.basal import traversal
from hop_design.design.construction.surveys.basal_population import admit_population
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction import (
    BasalGeometryDomain,
    ConstructionEndpoint,
    NickStrandSelection,
)
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.payload import DegeneratePayload
from tests.contract.test_basal_construction_discovery import _pairing_constraints, _request


def request():
    return _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload=DegeneratePayload(sequence="CCCR"),
        extra_nickase=True,
        max_retained_overhead_nt=5,
        domain=BasalGeometryDomain(
            nick_strand=NickStrandSelection.ANY,
            nick_offsets_nt=(0, 1),
            pairing_constraints=_pairing_constraints(),
        ),
    )


def test_each_target_constructs_programs_only_at_its_matching_overhead(monkeypatch):
    original = traversal.iter_basal_programs
    calls = []

    def counted(policy, *, target, endpoint):
        calls.append((target.nick_offset_nt, target.nick_strand.value))
        return original(policy, target=target, endpoint=endpoint)

    monkeypatch.setattr(traversal, "iter_basal_programs", counted)
    local = request()
    roster = [
        (
            level,
            unit.target.nick_strand.value,
            unit.payload_sequence,
            str(unit.program.nick_enzyme.enzyme_id),
        )
        for level in range(9)
        for unit in traversal.iter_basal_work_units(local, retained_overhead_nt=level)
    ]
    assert roster == [
        (level, strand, payload, f"example:enzyme/basal-nick-{method}@1")
        for level in (4, 5)
        for strand in ("top", "bottom")
        for payload in ("CCCA", "CCCG")
        for method in ("a", "b")
    ]
    assert calls == [(0, "top"), (0, "bottom"), (1, "top"), (1, "bottom")]


@pytest.mark.parametrize("maximum", [15, 16, 17])
def test_population_program_budget_still_counts_payload_and_program_multiplicity(maximum):
    # Two offsets, two strands, two payload assignments, two enzyme programs.
    limits = DEFAULT_SEQUENCE_LIMITS.model_copy(update={"max_programs": maximum})
    if maximum < 16:
        with pytest.raises(SequenceSetLimitError, match="program budget"):
            admit_population(request(), limits)
    else:
        population = admit_population(request(), limits)
        assert population.program_count == 16
