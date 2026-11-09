"""Projection reuse preserves masks, copied bases and builder/domain ownership."""

from random import Random

import pytest

from hop_design.kernel.construction import release_pair_relation as module
from hop_design.kernel.construction.foldback.domains import SequenceVariable
from hop_design.kernel.construction.release_pair_projection import project_end_pairs
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.support.context_completion import policy
from tests.unit.test_release_pair_hidden_cost import unconstrained_contacts
from tests.unit.test_survey_completion_binding import product


def builder(length):
    return SequenceSetBuilder(length_nt=length, max_nodes=10000, max_operations=100000)


@pytest.mark.parametrize("budget", [0, 1, None])
def test_compacted_frames_match_uncached_projection_with_masks_and_aliases(budget):
    d = unconstrained_contacts(budget)
    local = len(d.base_domains)
    owner = builder(4)
    project = module._end_pair_projector(d, owner)
    rng = Random(219)
    for number in range(96):
        extra = rng.randrange(2, 9)
        masks = [tuple("ACGT")] * (local + extra)
        for position in (d.source_span.end.offset - 1, d.adapter_span.start.offset, local):
            masks[position] = tuple(rng.choice(("A", "CG", "GT", "ACGT")))
        first = local + rng.randrange(extra)
        second = local + rng.randrange(extra)
        ends = (
            SequenceVariable(first),
            SequenceVariable(second, complemented=bool(number % 2)),
            SequenceVariable(d.source_span.end.offset - 1),
            SequenceVariable(first, complemented=True),
        )
        reference = builder(4)
        expected = reference.freeze(project_end_pairs(d, tuple(masks), ends, reference))
        assert owner.freeze(project(tuple(masks), ends)) == expected


def test_projection_reuse_is_bounded_and_eviction_recomputes(monkeypatch):
    d = unconstrained_contacts(0)
    original, calls = module.project_end_pairs, []

    def counted(*args):
        calls.append(None)
        return original(*args)

    monkeypatch.setattr(module, "project_end_pairs", counted)
    owner = builder(2)
    project = module._end_pair_projector(d, owner)
    frames = []
    # Distinct conservative local-mask keys with the same exact fixed output.
    for number in range(129):
        masks = [tuple("ACGT")] * len(d.base_domains)
        for bit in range(8):
            masks[d.payload_span.start.offset + bit] = ("C" if number & (1 << bit) else "A",)
        frames.append(tuple(masks))
        assert owner.freeze(project(frames[-1], tuple("AA"))).contains("AA")
    assert len(calls) == 129
    assert owner.freeze(project(frames[0], tuple("AA"))).contains("AA")
    assert len(calls) == 130


def test_different_contact_budgets_do_not_share_projection_results():
    owner = builder(2)
    for budget, expected in ((0, 0), (1, 1), (0, 0)):
        d = unconstrained_contacts(budget)
        masks = [tuple("ACGT")] * len(d.base_domains)
        masks[d.source_span.end.offset - 1], masks[d.adapter_span.start.offset] = ("G",), ("T",)
        project = module._end_pair_projector(d, owner)
        assert owner.freeze(project(tuple(masks), tuple("AA"))).cardinality == expected


def test_original_frame_length_limit_precedes_projection_reuse():
    d = unconstrained_contacts(0)
    # The long prefixes could normalize to a short projection, but the complete
    # frame must still obey the variable ceiling before any cached root is used.
    upstream = policy({"min_length_nt": 14, "max_length_nt": 256, "base_spec": "N"})
    with pytest.raises(ValueError, match="length_nt must be an integer between"):
        module.necessary_end_pairs(product(), (d,), upstream, DEFAULT_SEQUENCE_LIMITS)
