"""A product feature is one teachable concept even when several measurements name it."""

from hop_design.design.construction.navigation.features.operations import parameter_operations
from hop_design.design.construction.variants.explanation import parameter_capabilities
from hop_design.models.construction.variants.parameters import PARAMETERS, parameter_definition


def test_equivalent_arm_measurements_share_a_product_concept_without_losing_coordinates():
    arm = parameter_definition("foldback_arm_bp")
    extension = parameter_definition("loop_side_paired_bp")
    assert arm.label == extension.label == "Loop-side extension"
    assert arm.canonical_key == extension.canonical_key == "foldback_arm_bp"
    assert arm.design_role == extension.design_role == "product"
    assert arm.boundaries == extension.boundaries == ("supplied_stem_end", "loop_start")
    assert arm.stage == extension.stage == "hairpin"


def test_product_constraints_can_be_derived_while_preparation_requirements_stay_distinct():
    loop = parameter_definition("loop_nt")
    assert loop.design_role == "product"
    assert loop.dependencies == ("loop_word",)
    assert loop.role == "derived"
    paired = parameter_definition("self_paired_arm_bp")
    assert paired.design_role == "outcome"
    assert paired.dependencies == ("foldback_arm_bp", "join_offset_nt")
    assert parameter_definition("join_offset_nt").design_role == "construction"
    assert parameter_definition("adapter_annealing_min_nt").design_role == "construction"
    assert parameter_definition("adapter_annealing_achieved_nt").design_role == "outcome"
    assert parameter_definition("open_side_paired_positions").design_role == "product"


def test_public_explanation_carries_the_same_map_and_endpoint_applicability():
    result = {"axes": [], "paths": []}
    parameters = {p.key: p for p in parameter_capabilities("hairpin", result)}
    assert parameters["loop_nt"].applicable
    assert parameters["loop_nt"].design_role == "product"
    assert parameters["loop_side_paired_bp"].canonical_key == "foldback_arm_bp"
    assert not parameters["left_gap"].applicable
    assert parameters["left_gap"].stage == "released_insert"
    assert parameters["left_gap"].design_role == "product"
    assert all(
        parameter_definition(p.canonical_key).canonical_key == p.canonical_key for p in PARAMETERS
    )


def test_operations_respect_endpoint_and_aliases_without_conflating_derived_with_uneditable():
    def operations(key, product="released_insert"):
        return parameter_operations(
            parameter_definition(key),
            product=product,
            permissions={"foldback": {}, "basal": {}, "release": {}},
            live=True,
        )

    assert operations("foldback_arm_bp") == operations("loop_side_paired_bp")
    assert operations("loop_nt")["revise"]["available"]
    assert not operations("self_paired_arm_bp")["revise"]["available"]
    assert operations("adapter_annealing_min_nt")["revise"]["available"]
    assert not operations("adapter_annealing_achieved_nt")["revise"]["available"]
    for key in ("left_gap", "basal_method", "adapter_annealing_min_nt"):
        result = operations(key, "hairpin")
        assert result["inspect"]["available"]
        assert not any(op["available"] for name, op in result.items() if name != "inspect")
    assert operations("basal_method", "adapter_ligated_hairpin")["revise"]["available"]


def test_captured_parameter_mismatch_is_inspectable_without_reinterpreting_operations():
    from copy import deepcopy
    from types import SimpleNamespace

    from hop_design.design.construction.navigation.features.vocabulary import describe_parameters

    definition = parameter_definition("loop_nt").model_dump(mode="json")
    definition["measurement"] = "Different captured boundaries."
    answer = {"axes": [definition], "query": {"parameters": []}}
    original = deepcopy(answer)
    source = SimpleNamespace(
        resolution={"intent": {"product": "released_insert"}, "permissions": {}}
    )
    result = describe_parameters(source, answer)[0]
    assert result["measurement"] == "Different captured boundaries."
    assert result["operations"]["inspect"]["available"]
    assert not any(
        op["available"] for name, op in result["operations"].items() if name != "inspect"
    )
    assert answer == original
