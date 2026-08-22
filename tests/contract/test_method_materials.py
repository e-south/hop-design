from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

import hop_design as hop


def _oligo(
    material_id: str,
    sequence: str,
    *,
    phosphorylated: bool = False,
) -> hop.ProcessOligo:
    modifications = (hop.OligoModification.FIVE_PRIME_PHOSPHATE,) if phosphorylated else ()
    return hop.ProcessOligo(
        material_id=material_id,
        sequence=sequence,
        modifications=modifications,
    )


def _spec() -> hop.LinearSourceHairpinPcrMaterialsSpec:
    return hop.LinearSourceHairpinPcrMaterialsSpec(
        schema="hop.linear-source-hairpin-pcr-materials/v1",
        method_id="synthetic-linear-source",
        source_oligo=_oligo("source", "ACGTACGTNNRYGCTTAG"),
        source_pcr_forward_primer=_oligo("source-fwd", "ACGTAC"),
        source_pcr_reverse_primer=_oligo(
            "source-rev",
            "CTAAGC",
            phosphorylated=True,
        ),
        ligation_adapter=_oligo(
            "adapter",
            "TTGACCGTAACC",
            phosphorylated=True,
        ),
        hairpin_pcr_forward_primer=_oligo("hairpin-fwd", "ACGTACGT"),
        hairpin_pcr_reverse_primer=_oligo("hairpin-rev", "GGTTACGG"),
        ligation_end_preparation=hop.LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS,
    )


def test_method_materials_resolve_terminal_primer_binding_and_chemistry() -> None:
    plan = hop.resolve_linear_source_hairpin_pcr_materials(_spec())

    assert plan.schema_id == "hop.linear-source-hairpin-pcr-materials-plan/v1"
    assert tuple(binding.binding_id for binding in plan.bindings) == (
        "source-pcr-forward",
        "source-pcr-reverse",
        "hairpin-pcr-forward",
        "hairpin-pcr-reverse",
    )
    assert tuple(
        (
            binding.primer_id,
            binding.template_id,
            binding.template_span.start.offset,
            binding.template_span.end.offset,
            binding.orientation,
        )
        for binding in plan.bindings
    ) == (
        ("source-fwd", "source", 0, 6, "same_5to3"),
        ("source-rev", "source", 12, 18, "reverse_complement_5to3"),
        ("hairpin-fwd", "source", 0, 8, "same_5to3"),
        ("hairpin-rev", "adapter", 4, 12, "reverse_complement_5to3"),
    )
    assert plan.required_material_ids == (
        "source",
        "source-fwd",
        "source-rev",
        "adapter",
        "hairpin-fwd",
        "hairpin-rev",
    )


def test_method_materials_reject_a_primer_that_does_not_bind_its_terminal_handle() -> None:
    spec = _spec().model_copy(
        update={"hairpin_pcr_reverse_primer": _oligo("hairpin-rev", "AAAAAAAA")}
    )

    with pytest.raises(
        ValueError,
        match="hairpin PCR reverse primer must reverse-complement the adapter suffix",
    ):
        hop.resolve_linear_source_hairpin_pcr_materials(spec)


def test_pre_phosphorylated_route_requires_both_ligation_end_modifications() -> None:
    data = _spec().model_dump(mode="python", by_alias=True)
    data["source_pcr_reverse_primer"]["modifications"] = ()

    with pytest.raises(ValidationError, match="source PCR reverse primer"):
        hop.LinearSourceHairpinPcrMaterialsSpec.model_validate(data)


def test_kinase_step_allows_unmodified_ligation_end_oligos() -> None:
    data = _spec().model_dump(mode="python", by_alias=True)
    data["source_pcr_reverse_primer"]["modifications"] = ()
    data["ligation_adapter"]["modifications"] = ()
    data["ligation_end_preparation"] = hop.LigationEndPreparation.KINASE_STEP

    plan = hop.resolve_linear_source_hairpin_pcr_materials(
        hop.LinearSourceHairpinPcrMaterialsSpec.model_validate(data)
    )

    assert plan.ligation_end_preparation == "kinase_step"


def test_material_plan_rejects_unmodified_pre_phosphorylated_claim() -> None:
    data = _spec().model_dump(mode="python", by_alias=True)
    data["source_pcr_reverse_primer"]["modifications"] = ()
    data["ligation_adapter"]["modifications"] = ()
    data["ligation_end_preparation"] = hop.LigationEndPreparation.KINASE_STEP
    plan = hop.resolve_linear_source_hairpin_pcr_materials(
        hop.LinearSourceHairpinPcrMaterialsSpec.model_validate(data)
    ).model_dump(mode="json", by_alias=True)
    plan["ligation_end_preparation"] = "pre_phosphorylated_oligos"

    with pytest.raises(ValidationError, match="require phosphates"):
        hop.LinearSourceHairpinPcrMaterialsPlan.model_validate_json(json.dumps(plan))


def test_method_materials_plan_rejects_serialized_binding_drift() -> None:
    data = hop.resolve_linear_source_hairpin_pcr_materials(_spec()).model_dump(
        mode="json", by_alias=True
    )
    data["bindings"][0]["template_span"]["end"]["offset"] = 5

    with pytest.raises(ValidationError, match="binding derivations"):
        hop.LinearSourceHairpinPcrMaterialsPlan.model_validate_json(json.dumps(data))
