"""Release programs stay fixed while source lengths and placements vary."""

from dataclasses import replace

import pytest

from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.release_pair_relation import necessary_end_pairs
from hop_design.models.construction.basal_release import BasalFutureReleaseAction
from hop_design.models.construction.complete.auxiliary.policy import ConstrainedEndpointPrimerPolicy
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.enzymes import CharacterizedEnzyme
from tests.support.context_completion import policy
from tests.unit.test_release_pair_projection import domain
from tests.unit.test_survey_completion_binding import product


def test_equivalent_upstream_frames_share_projection_only_within_one_domain(monkeypatch):
    from hop_design.kernel.construction import release_pair_relation as module

    p, d = product(), domain()
    auxiliary = p.materialization.endpoint_auxiliaries
    p = p.model_copy(
        update={
            "materialization": p.materialization.model_copy(
                update={
                    "endpoint_auxiliaries": auxiliary.model_copy(
                        update={
                            "forward_primer": ConstrainedEndpointPrimerPolicy(
                                mode="constrain",
                                min_annealing_length_nt=14,
                                max_annealing_length_nt=14,
                                five_prime_handle_sequence="G",
                            )
                        }
                    )
                }
            )
        }
    )
    upstream = policy({"min_length_nt": 14, "max_length_nt": 24, "base_spec": "N"})
    original, calls = module.project_end_pairs, []
    windows, placements = module.release_action_windows, []

    def counted(*args):
        calls.append(args)
        return original(*args)

    def placed(*args):
        placements.append(args)
        return windows(*args)

    monkeypatch.setattr(module, "project_end_pairs", counted)
    monkeypatch.setattr(module, "release_action_windows", placed)
    first = necessary_end_pairs(p, (d,), upstream, DEFAULT_SEQUENCE_LIMITS)
    assert first.cardinality == 1
    assert len(calls) == 1
    assert len(placements) == 22  # Both ends still check every permitted length.
    # Another domain or invocation has separate permissions and root ownership.
    assert necessary_end_pairs(p, (d, d), upstream, DEFAULT_SEQUENCE_LIMITS) == first
    assert len(calls) == 3
    assert len(placements) == 66


def test_release_actions_are_resolved_once_per_definition_and_end_per_projection(monkeypatch):
    p, d = product(), domain()
    upstream = policy({"min_length_nt": 14, "max_length_nt": 24, "base_spec": "N"})
    original = BasalFutureReleaseAction.create.__func__
    calls = []

    def counted(cls, **content):
        calls.append((content["enzyme_digest"], content["requirement"].product_end))
        return original(cls, **content)

    monkeypatch.setattr(BasalFutureReleaseAction, "create", classmethod(counted))
    # Repeated domains and eleven handle lengths share the same two cut programs.
    result = necessary_end_pairs(p, (d, d), upstream, DEFAULT_SEQUENCE_LIMITS)
    assert result.cardinality == 1
    assert len(calls) == len(set(calls)) == 2
    assert {side for _, side in calls} == {"left", "right"}
    # Reuse is invocation-local, without retaining authority across requests.
    assert necessary_end_pairs(p, (d,), upstream, DEFAULT_SEQUENCE_LIMITS) == result
    assert len(calls) == 4


def test_release_action_reuse_distinguishes_full_definitions_with_the_same_name(monkeypatch):
    p, d = product(), domain()
    enzyme = d.program.future_release_enzyme
    data = enzyme.model_dump()
    data["recognition_pattern"] = "GGTCTG"
    other = CharacterizedEnzyme.model_validate(data)
    assert other.enzyme_id == enzyme.enzyme_id and other != enzyme
    changed = replace(d, program=replace(d.program, future_release_enzyme=other))
    upstream = policy("N" * 14)
    separate = [
        necessary_end_pairs(p, (value,), upstream, DEFAULT_SEQUENCE_LIMITS)
        for value in (d, changed)
    ]
    expected = {r.member_at(i) for r in separate for i in range(r.cardinality)}
    original = BasalFutureReleaseAction.create.__func__
    calls = []

    def counted(cls, **content):
        calls.append((content["enzyme_digest"], content["requirement"].product_end))
        return original(cls, **content)

    monkeypatch.setattr(BasalFutureReleaseAction, "create", classmethod(counted))
    result = necessary_end_pairs(p, (d, changed, d), upstream, DEFAULT_SEQUENCE_LIMITS)
    assert {result.member_at(i) for i in range(result.cardinality)} == expected
    assert len(calls) == len(set(calls)) == 4


@pytest.mark.parametrize("bases", ["N", "R"])
def test_length_union_preserves_individual_recognition_placements(bases):
    p, d = product(anneal=30), domain()
    separate = [
        necessary_end_pairs(p, (d,), policy(bases * n), DEFAULT_SEQUENCE_LIMITS)
        for n in range(1, 25)
    ]
    assert all(r is not None for r in separate)
    assert any(r.cardinality == 0 for r in separate)
    if bases == "N":
        assert any(r.cardinality > 0 for r in separate)
    expected = {r.member_at(i) for r in separate for i in range(r.cardinality)}
    combined = necessary_end_pairs(
        p,
        (d,),
        policy({"min_length_nt": 1, "max_length_nt": 24, "base_spec": bases}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert {combined.member_at(i) for i in range(combined.cardinality)} == expected


def test_source_index_is_reused_across_lengths_but_not_local_domains(monkeypatch):
    p, d = product(), domain()
    upstream = policy({"min_length_nt": 14, "max_length_nt": 24, "base_spec": "N"})
    original = BasalSequenceIndex.create.__func__
    calls = []

    def counted(cls, value):
        calls.append(value)
        return original(cls, value)

    monkeypatch.setattr(BasalSequenceIndex, "create", classmethod(counted))
    result = necessary_end_pairs(p, (d, d), upstream, DEFAULT_SEQUENCE_LIMITS)
    assert result.cardinality == 1
    assert len(calls) == 2
    # An impossible association span still rejects before building an index.
    assert (
        necessary_end_pairs(
            product(anneal=100), (d,), upstream, DEFAULT_SEQUENCE_LIMITS
        ).cardinality
        == 0
    )
    assert len(calls) == 2
