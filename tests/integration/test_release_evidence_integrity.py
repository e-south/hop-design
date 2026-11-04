"""Challenge released-insert evidence independently of its enclosing hashes."""

import hashlib

import pytest

from hop_design.models.construction.complete.clone.geometry import derive_clone_cut_geometry
from hop_design.models.construction.complete.clone.validation import validate_clone_realization
from hop_design.models.construction.enzyme_binding import ConstructionEnzymeBinding
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.method import BindingOrientation
from tests.integration.test_complete_construction_clone import _valid_clone_result


@pytest.fixture(scope="module")
def realized(tmp_path_factory):
    result, _, _, _ = _valid_clone_result(tmp_path_factory.mktemp("release-evidence"))
    return result.realizations[0]


@pytest.mark.parametrize(
    "field",
    [
        "parent_state_id",
        "primary_parent_strand_id",
        "complementary_parent_strand_id",
        "primary_parent_span",
        "complementary_parent_span",
        "union_span",
        "union_sequence",
        "union_orientation",
        "core_orientation",
    ],
)
def test_semantic_replay_rejects_each_changed_release_fact(realized, field):
    evidence = realized.final_product.release_evidence
    if field.endswith("_id"):
        changed = evidence.model_copy(update={field: "wrong-parent"})
    elif field.endswith("_parent_span"):
        span = getattr(evidence, field)
        changed = evidence.model_copy(
            update={
                field: Span(
                    start=Boundary(offset=span.start.offset + 1),
                    end=span.end,
                )
            }
        )
    else:
        key = (
            "design_parent_projection"
            if field == "core_orientation"
            else "released_union_projection"
        )
        projection = getattr(evidence, key)
        if field == "union_span":
            update = {
                "source_span": Span(
                    start=Boundary(offset=projection.source_span.start.offset + 1),
                    end=Boundary(offset=projection.source_span.end.offset + 1),
                )
            }
        elif field == "union_sequence":
            sequence = ("C" if projection.sequence[0] != "C" else "A") + projection.sequence[1:]
            update = {
                "sequence": sequence,
                "sequence_digest": f"sha256:{hashlib.sha256(sequence.encode()).hexdigest()}",
            }
        else:
            update = {"orientation": BindingOrientation.REVERSE_COMPLEMENT_5TO3}
        changed = evidence.model_copy(update={key: projection.model_copy(update=update)})
    altered = realized.model_copy(
        update={
            "final_product": realized.final_product.model_copy(update={"release_evidence": changed})
        }
    )
    with pytest.raises(ValueError):
        validate_clone_realization(altered)


@pytest.mark.parametrize("side", ["left", "right"])
def test_one_strand_cut_into_payload_is_rejected_even_if_union_preserves_it(realized, side):
    operations = realized.construction_program.reaction_programs[-1].stages[0].operations
    bindings = tuple(
        ConstructionEnzymeBinding.create(
            enzyme_id=op.enzyme_id,
            role=EnzymeRole.END_GENERATION,
            strand=None,
            **op.intended_binding.model_dump(mode="python"),
        )
        for op in operations
    )
    core = realized.final_product.design_projection
    a, b = realized.design.payload_boundaries
    if side == "left":
        bindings = (
            bindings[0].model_copy(
                update={"complement_cut": Boundary(offset=core.source_span.start.offset + a + 1)}
            ),
            bindings[1],
        )
    else:
        bindings = (
            bindings[0],
            bindings[1].model_copy(
                update={"reference_cut": Boundary(offset=core.source_span.start.offset + b - 1)}
            ),
        )
    parent = realized.construction_program.states[-2].molecules[0].sequence
    with pytest.raises(ValueError, match="both strands"):
        derive_clone_cut_geometry(
            bindings=bindings,
            parent_length=len(parent),
            template_sequence=parent,
            design_sequence=core.sequence,
            design_parent_span=core.source_span,
            payload_boundaries=(a, b),
        )


@pytest.mark.parametrize("form", ["both", "neither", "legacy"])
def test_clone_requires_only_explicit_release_evidence(realized, form):
    data = realized.final_product.model_dump(mode="python")
    if form in {"both", "legacy"}:
        data["encoding_projection"] = realized.final_product.design_projection
    if form in {"neither", "legacy"}:
        data.pop("release_evidence")
    with pytest.raises(ValueError, match="separate parent-core"):
        type(realized.final_product).model_validate(data)


def test_unreleased_product_rejects_release_evidence(realized, tmp_path):
    from tests.integration.test_complete_construction_pcr import _valid_pcr_result

    result, _, _ = _valid_pcr_result(tmp_path)
    product = result.realizations[0].final_product
    data = product.model_dump(mode="python")
    data["release_evidence"] = realized.final_product.release_evidence
    with pytest.raises(ValueError, match="Unreleased products"):
        type(product).model_validate(data)
