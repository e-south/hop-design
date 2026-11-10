"""Independent exposed bases fit their Cartesian output-construction budget."""

from itertools import product

import pytest

from hop_design.kernel.construction.foldback.domains import SequenceVariable
from hop_design.kernel.construction.release_pair_projection import project_end_pairs
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from tests.unit.test_release_pair_hidden_cost import unconstrained_contacts


@pytest.mark.parametrize("empty", [False, True])
def test_independent_outputs_need_only_their_cartesian_construction_budget(empty):
    domain = unconstrained_contacts(0)
    local = len(domain.base_domains)
    choices = [("A",), tuple("CG"), tuple("GT"), tuple("ACGT")] * 2
    if empty:
        choices[0] = ()
    masks = (tuple("ACGT"),) * local + tuple(choices)
    ends = tuple(SequenceVariable(local + i, complemented=bool(i % 2)) for i in range(8))
    complement = dict(zip("ACGT", "TGCA", strict=True))
    expected = {
        "".join(complement[base] if i % 2 else base for i, base in enumerate(word))
        for word in product(*choices)
    }
    # No observed base participates in a contact or copy relationship. Their
    # independent masks need one bounded Cartesian construction, even though
    # hidden contacts must still be checked for a feasible matched witness.
    builder = SequenceSetBuilder(length_nt=8, max_nodes=100, max_operations=8)
    relation = builder.freeze(project_end_pairs(domain, masks, ends, builder))

    assert {relation.member_at(i) for i in range(relation.cardinality)} == expected
