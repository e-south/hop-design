"""Existing molecular projections reused as whole-scaffold, crop and product-stage views."""

import json

from hop_design.export.construction.scaffold.closing_svg import render_closing_svg
from hop_design.export.construction.scaffold.product_stages_svg import render_product_stages_svg
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..projections.product_stages import project_product_stages
from ..projections.trajectory import project_complete_construction_trajectory
from ..public import VerifiedConstructionBundle


def complementary_drawings(
    receipt: VerifiedConstructionBundle, identity: str, portrait: bytes, drawing: bytes
) -> dict[str, bytes]:
    facts = HairpinPortraitProjection.model_validate_json(portrait)
    trajectory = project_complete_construction_trajectory(
        receipt._verified_source(), materialized_realization_id=identity
    )
    stage = project_product_stages(facts, trajectory)
    return {
        "closing.svg": render_closing_svg(facts, paired_context=2, nucleotide_font_size=18),
        "stages.svg": render_product_stages_svg(stage, drawing),
        "dimensions.json": json.dumps(
            {
                "stem_bp": facts.stem_bp,
                **facts.scaffold_dimensions,
                "stage_role": facts.stage_role,
            },
            sort_keys=True,
        ).encode(),
    }
