"""Project an explicitly previewed complete option relative to the query's stable reference."""

import json
from dataclasses import dataclass
from typing import Any, ClassVar

from hop_design.export.construction.molecular.folded_sequence import render_folded_sequence
from hop_design.export.construction.molecular.variant_endpoint import render_variant_endpoint
from hop_design.models.construction.complete.product import MaterializedFinalProduct
from hop_design.models.construction.projections.folded_sequence import FoldedSequenceView
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.models.construction.projections.product_stages import ProductStageProjection
from hop_design.serialization import canonical_json_bytes

from ..packets.publication import SourceBoundConstructionPacket
from ..projections.folded_sequence import folded_sequence_view
from .public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldVariantView(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-variant-view-packet/v1"

    @property
    def svg_bytes(self) -> bytes:
        return dict(self._files)["projection.svg"]


def project_scaffold_variant(
    pool: ScaffoldExploration, choices: ScaffoldVariantChoices, *, option_label: str
) -> ScaffoldVariantView:
    """A preview names an existing option; it never selects it or changes the reference."""
    return _project_variant(pool, choices, option_label=option_label)


def _project_variant(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    *,
    option_label: str,
    display_stage: str | None = None,
) -> ScaffoldVariantView:
    summary = json.loads(choices.json_bytes)
    current = query_scaffold_variants(pool, summary["query"])
    if current.json_bytes != choices.json_bytes:
        raise ValueError("Choices no longer agree with this admitted exploration.")
    if option_label not in summary["compatible_options"]:
        raise ValueError("Preview must name a compatible complete option in the active query.")
    return _render_variant(pool, summary, option_label=option_label, display_stage=display_stage)


def _render_variant(
    pool: ScaffoldExploration,
    summary: dict[str, Any],
    *,
    option_label: str,
    display_stage: str | None = None,
) -> ScaffoldVariantView:
    """Render after the public operation has verified query agreement and membership."""
    projection, view, stages_data = _variant_projection(
        pool, summary, option_label=option_label, display_stage=display_stage
    )
    stage, reference_label = projection["stage"], projection["reference"]
    reference_caption = (
        "self (no comparison reference)" if reference_label is None else reference_label
    )
    svg = (
        render_variant_endpoint(
            ProductStageProjection.model_validate_json(canonical_json_bytes(stages_data)),
            view,
        )
        if stage == "endpoint" and view.portrait.stage_role == "intermediate"
        else render_folded_sequence(
            view, display_label=option_label, reference_label=reference_caption
        )
    )
    packet = ScaffoldVariantView._create(
        {"projection.svg": svg},
        projection,
        "# Complete molecule preview\n\nNo product has been selected. "
        "The drawing shows specified pairing, not a predicted physical conformation.\n",
    )
    object.__setattr__(packet, "_roots", (pool._root,))
    return packet


def _variant_projection(
    pool: ScaffoldExploration,
    summary: dict[str, Any],
    *,
    option_label: str,
    display_stage: str | None = None,
) -> tuple[dict[str, Any], FoldedSequenceView, dict[str, Any]]:
    """Immutable comparison facts without constructing an unused drawing or packet."""
    options = {o["label"]: o for o in json.loads(pool._options)}
    option = options[option_label]
    reference_label = summary["query"]["reference"]
    reference = options[reference_label] if reference_label is not None else option
    view = folded_sequence_view(
        HairpinPortraitProjection.model_validate_json(
            canonical_json_bytes(option["portrait_data"])
        ),
        HairpinPortraitProjection.model_validate_json(
            canonical_json_bytes(reference["portrait_data"])
        ),
        label=option_label,
        reference_label=reference["label"],
        materials=option["material_roles"],
        reference_materials=reference["material_roles"],
        endpoint=MaterializedFinalProduct.model_validate_json(
            canonical_json_bytes(option["endpoint_data"])
        ),
        reference_endpoint=MaterializedFinalProduct.model_validate_json(
            canonical_json_bytes(reference["endpoint_data"])
        ),
    )
    stage = display_stage or summary["query"]["stage"]
    projection = {
        "schema": "hop.scaffold-variant-view/v1",
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "stage": stage,
        "option_label": option_label,
        "reference": reference_label,
        "selected_product": None,
        "molecule_id": option["molecular_identity"][stage],
        "view": json.loads(canonical_json_bytes(view)),
    }
    return projection, view, option["stages_data"]
