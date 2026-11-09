"""A bounded basal work stream preserves the explicit overhead-level order."""

import pytest

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.models.construction.search import BasalGeometryDomain
from hop_design.models.construction.targets import NickStrandSelection
from hop_design.models.physical import Strand
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


@pytest.mark.parametrize("strand", [Strand.BOTTOM, NickStrandSelection.ANY])
@pytest.mark.parametrize("maximum", [0, 10, 11, 12, 32])
@pytest.mark.parametrize("end_word", ["AGTC", "AGTN"])
def test_single_pass_matches_all_explicit_levels_and_keeps_the_budget(strand, maximum, end_word):
    local = _two_method_product().construction_source().basal
    local = local.model_copy(
        update={
            "geometry_domain": local.geometry_domain.model_copy(
                update={
                    "nick_strand": strand,
                    "nick_offsets_nt": (0, 1, 2),
                    "future_release": local.geometry_domain.future_release.model_copy(
                        update={"cohesive_end_sequence": end_word}
                    ),
                }
            ),
            "search": local.search.model_copy(update={"max_retained_overhead_nt": maximum}),
        }
    )
    expected = tuple(
        unit
        for overhead in range(maximum + 1)
        for unit in iter_basal_work_units(local, retained_overhead_nt=overhead)
    )
    actual = tuple(iter_basal_work_units(local, retained_overhead_nt=None))
    assert actual == expected
    if maximum == 32:
        assert actual


def test_stream_visits_the_target_roster_once(monkeypatch):
    local = _two_method_product().construction_source().basal
    calls = []
    original = BasalGeometryDomain.exact_targets

    def measured(self):
        calls.append(None)
        yield from original(self)

    monkeypatch.setattr(BasalGeometryDomain, "exact_targets", measured)
    assert tuple(iter_basal_work_units(local, retained_overhead_nt=None))
    assert len(calls) == 1


def test_stream_stops_at_the_first_offset_above_its_budget(monkeypatch):
    local = _two_method_product().construction_source().basal
    local = local.model_copy(
        update={
            "geometry_domain": local.geometry_domain.model_copy(
                update={"nick_offsets_nt": tuple(range(1000))}
            ),
            "search": local.search.model_copy(update={"max_retained_overhead_nt": 10}),
        }
    )
    original, visited = BasalGeometryDomain.exact_targets, []

    def measured(self):
        for target in original(self):
            visited.append(target.nick_offset_nt)
            yield target

    monkeypatch.setattr(BasalGeometryDomain, "exact_targets", measured)
    assert tuple(iter_basal_work_units(local, retained_overhead_nt=None))
    assert visited == [0, 1]
