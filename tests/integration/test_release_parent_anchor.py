"""Repeated sequence cannot move the supplied stem to a different occurrence."""

import pytest

from hop_design.models.construction.complete.pcr.products import endpoint_fate_spans
from hop_design.models.construction.complete.pcr.validation import validate_pcr_realization
from hop_design.models.coordinates import Boundary, Span
from tests.integration.test_complete_construction_clone import _clone_request
from tests.integration.test_complete_construction_discovery import _discover_raw


def test_repeated_core_keeps_source_anchored_occurrence_even_if_fates_are_rewritten(tmp_path):
    request, foldback, basal, design, _, encoding = _clone_request(tmp_path)
    data = request.model_dump(mode="python", by_alias=True)
    oligo = data["materialization"]["endpoint_auxiliaries"]["forward_primer"]["primer"]["oligo"]
    oligo["sequence_5prime"] = "GGTCTC" + encoding + encoding[:4]
    del oligo["material_id"]
    data["release"]["left"]["payload_end_offset_bp"] = len(encoding)
    modified = type(request).model_validate(data)
    result = _discover_raw(modified, foldback=foldback, basal=basal, design=design)
    assert result.realizations, result.failure_reasons
    item = result.realizations[0]
    assert item.final_product.design_projection.source_span.start.offset == 6 + len(encoding)
    wrong_span = Span(start=Boundary(offset=6), end=Boundary(offset=6 + len(encoding)))
    evidence = item.final_product.release_evidence
    bad_evidence = evidence.model_copy(
        update={
            "design_parent_projection": evidence.design_parent_projection.model_copy(
                update={"source_span": wrong_span}
            )
        }
    )
    product = item.final_product.model_copy(update={"release_evidence": bad_evidence})
    program = item.construction_program
    transition = program.transitions[-2]
    extension = transition.pcr_authority
    wrong_fates = endpoint_fate_spans(
        item.design.plan.hairpin_encoding_insert.features,
        len(extension.products[0].sequence),
        design_source_span=wrong_span,
    )
    altered_transition = transition.model_copy(
        update={
            "pcr_authority": extension.model_copy(
                update={"endpoint_sequence_fate_spans": wrong_fates}
            )
        }
    )
    altered_program = program.model_copy(
        update={
            "transitions": (*program.transitions[:-2], altered_transition, program.transitions[-1])
        }
    )
    # Call the semantic replay validator directly, independently of content IDs.
    with pytest.raises(ValueError, match="anchored"):
        validate_pcr_realization(
            item.model_copy(
                update={
                    "final_product": product,
                    "construction_program": altered_program,
                }
            )
        )
