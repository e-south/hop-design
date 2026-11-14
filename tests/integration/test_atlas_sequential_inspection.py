"""Recorded sequential stages retain exact recognition and cut annotations."""

import pytest

from hop_design.design.construction.projections.atlas import project_molecular_atlas
from hop_design.design.construction.projections.inspection import project_molecular_inspection
from tests.contract.test_complete_source_partition_replay import _routes


@pytest.fixture(scope="module")
def sequential_route(tmp_path_factory):
    return _routes(tmp_path_factory.mktemp("sequential-inspection"))[2][2]


def test_unchanged_precursor_in_later_stage_keeps_every_operation(sequential_route):
    route = sequential_route
    program = route.construction_program.reaction_programs[0]
    assert len(program.stages) == 2
    precursor = program.states[0].molecules[0]
    assert program.states[1].by_id(precursor.molecule_id) == precursor
    expected = {op.operation_id for stage in program.stages for op in stage.operations}
    assert len(expected) == 2

    for phase, timing in [("duplex", "planned"), ("cleaved_duplex", "applied")]:
        view = project_molecular_inspection(route, phase)
        assert {op.operation_id for op in view.operations} == expected
        assert {op.timing for op in view.operations} == {timing}
        assert {site.site_id for site in view.recognition_sites} == expected
        assert all(site.presence == "present" for site in view.recognition_sites)
        for operation in view.operations:
            assert operation.recognition
            assert operation.cuts
            assert all(base.state_id == view.state.state_id for base in operation.recognition)

    atlas = project_molecular_atlas(route)
    assert [view.state for view in atlas.states] == [
        route.source_preparation.input_state,
        *route.construction_program.states,
    ]
    assert all(
        {site.site_id for site in view.recognition_sites} == expected for view in atlas.states
    )


def test_changed_intermediate_still_requires_an_exact_mapping(sequential_route):
    # Projection seam only: a modified snapshot is not an admitted new route.
    program = sequential_route.construction_program.reaction_programs[0]
    intermediate = program.states[1]
    molecule = intermediate.molecules[0]
    sequence = molecule.reference_sequence_5prime
    changed = molecule.model_copy(
        update={"reference_sequence_5prime": ("A" if sequence[0] != "A" else "C") + sequence[1:]}
    )
    program = program.model_copy(
        update={
            "states": (
                program.states[0],
                intermediate.model_copy(
                    update={"molecules": (changed, *intermediate.molecules[1:])}
                ),
                *program.states[2:],
            )
        }
    )
    route = sequential_route.model_copy(
        update={
            "construction_program": sequential_route.construction_program.model_copy(
                update={"reaction_programs": (program,)}
            )
        }
    )
    with pytest.raises(ValueError, match="exact intermediate"):
        project_molecular_inspection(route, "duplex")
