"""An unbound placement domain cannot masquerade as an exact molecular choice."""

import pytest

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from tests.unit.test_survey_completion_binding import product


def test_deferred_end_domain_has_no_materialization_authority():
    p = product()
    local = p.construction_source().basal
    for overhead in range(local.search.max_retained_overhead_nt + 1):
        for u in iter_basal_work_units(local, retained_overhead_nt=overhead):
            d = solve_basal_sequence_domain(
                payload_sequence=u.payload_sequence,
                target=u.target,
                endpoint=p.endpoint,
                program=u.program,
                defer_end_sequence=True,
            )
            if isinstance(d, BasalPlacementFailure):
                continue
            with pytest.raises(ValueError, match="not a materializable"):
                BasalSequenceIndex.create(d).member_at(0)
            return
    pytest.fail("Expected a deferred domain in the stated fixture")
