"""Regional marks follow physical positions, including complementary copies."""

import pytest

from hop_design.design.construction.projections.atlas_comparison import _regional_occurrences
from hop_design.design.construction.projections.inspection import inspection_states
from hop_design.design.construction.projections.sequence_difference import compare_sequence_region
from hop_design.models.construction import SourceOrientation
from tests.integration.test_hairpin_geometry_orientation import routes  # noqa: F401


@pytest.mark.parametrize("orientation", list(SourceOrientation))
def test_loop_uncertainty_marks_only_its_exact_ancestry_in_both_source_orientations(
    routes,  # noqa: F811
    orientation,
):
    route = routes[orientation]
    states = inspection_states(route)
    # This fixture's hairpin is AAAAGACAACA[AAA]TGTTGTCTTTT. The cap
    # occupies 11:14; the adjacent A at 10 is not part of the cap.
    assert states[-1].molecules[0].sequence == "AAAAGACAACAAAATGTTGTCTTTT"
    region = compare_sequence_region("loop", "AA", "AAA", (11, 13), (11, 14))
    assert region.correspondence == "ambiguous_minimum_edit"
    added, unknown = _regional_occurrences(route, (region,))
    assert not added

    # Literal coordinates derived from the 17-nt source and its cuts:
    # forward source 11:14 (TTT) copies to reverse strand 3:6 (AAA).
    # Mirroring the source swaps these two tracks. Joining appends the
    # survivor after the eight-base stem fragment, giving cap 11:14.
    if orientation is SourceOrientation.FORWARD:
        expected = [
            [(0, 11)],
            [(0, 11), (1, 3)],
            [(1, 3), (2, 3)],
            [(1, 3), (2, 3)],
            [(1, 3)],
            [(1, 3)],
            [(0, 11)],
        ]
    else:
        expected = [
            [(0, 3)],
            [(0, 3), (1, 11)],
            [(0, 3), (2, 3)],
            [(0, 3), (2, 3)],
            [(0, 3)],
            [(0, 3)],
            [(0, 11)],
        ]
    assert len(states) == len(expected)
    assert {(a.state_id, a.strand_id, a.index) for a in unknown} == {
        (state.state_id, state.molecules[track].strand_id, i)
        for state, spans in zip(states, expected, strict=True)
        for track, start in spans
        for i in range(start, start + 3)
    }
