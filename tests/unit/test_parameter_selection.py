"""Molecular measurements are shared, typed predicates, including derived quantities."""

import pytest
from pydantic import ValidationError


def test_derived_arm_is_a_constraint_not_an_independent_geometry():
    from hop_design.models.construction.variants.parameters import (
        ParameterSelection,
        parameter_definition,
    )

    definition = parameter_definition("self_paired_arm_bp")
    assert definition.symbol == "R"
    assert definition.dependencies == ("foldback_arm_bp", "join_offset_nt")
    assert definition.relationship == "R = A - D"
    selection = ParameterSelection(key="self_paired_arm_bp", minimum=7, maximum=8)
    assert selection.accepts(7)
    assert selection.accepts(8)
    assert not selection.accepts(6)
    assert not selection.accepts(None)


def test_discrete_and_numeric_selection_reject_ambiguous_or_unknown_constraints():
    from hop_design.models.construction.variants.parameters import ParameterSelection

    words = ParameterSelection(key="loop_word", values=("AAAA", "AACA"))
    assert words.accepts("AACA")
    assert not words.accepts("AAAC")
    for value in (
        {"key": "loop_word", "minimum": 0, "maximum": 4},
        {"key": "join_offset_nt", "values": ("2",)},
        {"key": "join_offset_nt", "minimum": 2, "maximum": 1},
        {"key": "join_offset_nt", "minimum": 1.5, "maximum": 2},
        {"key": "join_offset_nt", "values": (True,)},
        {"key": "join_offset_nt", "values": (2,), "minimum": 1, "maximum": 2},
        {"key": "unknown", "values": (1,)},
        {"key": "loop_word", "values": ("AAAA", "AAAA")},
    ):
        with pytest.raises(ValidationError):
            ParameterSelection.model_validate(value)


def test_pair_position_definition_retains_coordinate_meaning():
    from hop_design.models.construction.variants.parameters import parameter_definition

    position = parameter_definition("basal_source_base_3")
    assert position.group == "basal"
    assert position.stage == "source_adapter_association"
    assert position.position_from_ligation == 3
    assert "ligation" in position.measurement
