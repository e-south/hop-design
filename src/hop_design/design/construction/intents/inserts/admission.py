"""Replay only when molecular comparisons are requested; retain immutable derived facts."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from hop_design.design.runtime import producer_identity
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.serialization import canonical_json_bytes

from ...comparisons.controls import stage_facts
from ...navigation.molecular_descriptor import molecular_descriptor
from ...public import project_hairpin_portrait
from ...surveys.admission import open_survey
from ...surveys.selection import admit_selection
from ...surveys.witness import recover_witness
from ...variants.facts import regional_variants

if TYPE_CHECKING:
    from ..results import InsertDesignChoices


def admitted_options(choices: InsertDesignChoices) -> list[dict[str, Any]]:
    cached = getattr(choices, "_comparison_options", None)
    if cached is not None:
        return cast(list[dict[str, Any]], json.loads(cached))
    pool = choices._pool
    index, limits = open_survey(
        choices._directory / "survey.sqlite", request=pool._request, producer=producer_identity()
    )
    options: list[dict[str, Any]] = []
    seen = set()
    with index, tempfile.TemporaryDirectory(prefix="hop-insert-comparison-") as temporary:
        for path in json.loads(pool._snapshot)["paths"]:
            identity = path["materialized_realization_id"]
            if identity in seen:
                continue
            seen.add(identity)
            selected = pool.select(**path["address"], materialized_realization_id=identity)
            admit_selection(selected, pool._request, index)
            receipt, _, _ = recover_witness(
                index,
                pool._request,
                limits,
                **path["address"],
                root=Path(temporary) / str(len(options)),
            )
            route = next(
                r
                for r in receipt._verified_source().result.realizations
                if r.materialized_realization_id == identity
            )
            portrait = project_hairpin_portrait(receipt, materialized_realization_id=identity)
            architecture = HairpinPortraitProjection.model_validate_json(portrait.json_bytes)
            options.append(
                {
                    **path,
                    "label": identity,
                    "geometry": architecture.scaffold_dimensions,
                    "portrait_data": json.loads(portrait.json_bytes),
                    "loop_sequence": path["values"]["loop_word"],
                    "release_enzyme_id": path["values"]["release_method"],
                    "variants": regional_variants(route),
                    "descriptor": molecular_descriptor(route).model_dump(mode="json"),
                    "stage_facts": stage_facts(route),
                }
            )
    object.__setattr__(choices, "_comparison_options", canonical_json_bytes(options))
    return options
