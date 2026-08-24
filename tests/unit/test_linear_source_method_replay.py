from __future__ import annotations

import hop_design.methods as methods
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.linear_source_method.replay import _validate_annealing_and_ligation
from tests.support.linear_source_method import linear_source_method_request


def test_annealing_replay_normalizes_precursor_coordinates_to_fragment_indexes() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(linear_source_method_request())
    assert result.plan is not None
    plan = result.plan
    retained_ids = set(plan.length_selected_fragment_set.retained_fragment_ids)
    top = next(
        fragment
        for fragment in plan.denatured_fragment_set.fragments
        if fragment.fragment_id in retained_ids and fragment.precursor_strand == "top"
    )
    bottom = next(
        fragment
        for fragment in plan.denatured_fragment_set.fragments
        if fragment.fragment_id in retained_ids and fragment.precursor_strand == "bottom"
    )
    adapter = next(
        material
        for material in plan.materials.materials
        if material.role is methods.ProcessMaterialRole.LIGATION_ADAPTER
    )

    def shifted(fragment: methods.Fragment) -> methods.Fragment:
        return fragment.model_copy(
            update={
                "precursor_span": Span(
                    start=Boundary(offset=fragment.precursor_span.start.offset + 5),
                    end=Boundary(offset=fragment.precursor_span.end.offset + 5),
                )
            }
        )

    assert (
        _validate_annealing_and_ligation(
            plan,
            top=shifted(top),
            bottom=shifted(bottom),
            adapter=adapter,
        )
        == plan.ligated_hairpin.strand.sequence
    )
