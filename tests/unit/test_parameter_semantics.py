"""The explorer teaches relationships, measurements and requirements separately."""

from hop_design.models.construction.variants.parameters import PARAMETERS, parameter_definition


def test_every_parameter_declares_its_measurement_role_and_teaching_location():
    for definition in (*PARAMETERS, parameter_definition("basal_pair_class_2")):
        assert definition.role in {"achieved", "required", "derived", "comparison"}
        assert definition.glyph_frame in {"source", "association", "hairpin", "insert", "context"}
        assert definition.representation
        if definition.representation in {"span", "threshold", "sequence"}:
            assert len(definition.boundaries) == 2


def test_derived_and_duplicate_measurements_are_explicit_without_independent_knobs():
    arm = parameter_definition("foldback_arm_bp")
    assert "loop_side_paired_bp" in arm.equivalent_measurements
    loop = parameter_definition("loop_nt")
    assert loop.role == "derived"
    assert loop.dependencies == ("loop_word",)
    assert loop.relationship == "C = length(loop word)"
    assert parameter_definition("self_paired_arm_bp").role == "derived"
    assert parameter_definition("background").role == "comparison"


def test_primer_and_adapter_requirements_are_distinct_from_available_spans():
    required = parameter_definition("source_reverse_primer_required_nt")
    available = parameter_definition("source_reverse_primer_available_nt")
    assert required.role == "required"
    assert required.representation == "threshold"
    assert available.role == "achieved"
    assert available.boundaries == ("supplied_stem_end", "source_3prime_terminus")
    assert required.glyph_frame == available.glyph_frame == "source"
    assert parameter_definition("adapter_annealing_min_nt").role == "required"
    assert parameter_definition("adapter_annealing_achieved_nt").role == "achieved"


def test_permission_diversity_is_separate_from_complete_product_variation():
    from hop_design.design.construction.variants.choice_space import choice_space
    from tests.unit.test_choice_space import candidates

    data = choice_space(
        candidates(),
        ["a", "b", "c"],
        "hairpin",
        {"parameter_domains": {"loop_nt": {"values": [3, 4, 5]}}},
    )
    loop = next(a for a in data["axes"] if a["key"] == "loop_nt")
    assert loop["observed_variation"] is False
    assert loop["fixed_by_request"] is False
    assert loop["observed_values"] == [4]
    assert loop["domain_status"] == "declared"
