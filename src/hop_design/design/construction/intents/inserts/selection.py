"""Bind public preservation to exact native records without weakening older selections."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from hop_design.models.construction.intents.insert_selection import InsertDesignSelection
from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.surveys.selection import InterfaceSurveySelection
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...packets.atlas import MolecularAtlasPacket
from ...variants.query import surroundings_reasons
from ..base import Source
from ..comparisons import source_value
from .admission import admitted_options

if TYPE_CHECKING:
    from ..results import InsertDesignChoices


def bind_public_selection[Packet: MolecularAtlasPacket](packet: Packet, source: Source) -> Packet:
    value = source_value(source)
    if value.get("schema") != "hop.insert-design-selection/v1":
        return packet
    bound = type(packet)._create(
        {**dict(packet._files), "design-selection.json": canonical_json_bytes(value)},
        {**json.loads(packet.json_bytes), "design_selection": value},
        packet.report_text,
    )
    object.__setattr__(bound, "_roots", packet._roots)
    return bound


def wrap_selection(
    choices: InsertDesignChoices, native: dict[str, Any], query: DesignRefinementQuery
) -> dict[str, Any]:
    reference = next(
        p
        for p in choices._pool.query()["paths"]
        if p["materialized_realization_id"] == query.reference.materialized_realization_id
    )
    selected = InsertDesignSelection.model_validate_json(
        canonical_json_bytes(
            {
                **{
                    k: native[k]
                    for k in ("request_digest", "snapshot_digest", "materialized_realization_id")
                },
                "query_digest": sha256_digest(canonical_json_bytes(query)),
                "query": query.model_dump(mode="json", by_alias=True),
                "native": native,
                "reference": choices._pool.select(
                    **reference["address"],
                    materialized_realization_id=reference["materialized_realization_id"],
                ),
            }
        )
    )
    return selected.model_dump(mode="json", by_alias=True)


def native_selection(choices: InsertDesignChoices, source: Source) -> dict[str, Any]:
    value = source_value(source)
    if value.get("schema") != "hop.insert-design-selection/v1":
        return InterfaceSurveySelection.model_validate_json(canonical_json_bytes(value)).model_dump(
            mode="json", by_alias=True
        )
    selected = InsertDesignSelection.model_validate_json(canonical_json_bytes(value))
    query = selected.query
    if (
        selected.query_digest != sha256_digest(canonical_json_bytes(query))
        or selected.materialized_realization_id != selected.native.materialized_realization_id
        or selected.request_digest != selected.native.request_digest
        or selected.snapshot_digest != selected.native.snapshot_digest
        or query.reference.request_digest != selected.reference.request_digest
        or query.reference.snapshot_digest != selected.reference.snapshot_digest
        or query.reference.snapshot_digest != selected.snapshot_digest
        or query.reference.materialized_realization_id
        != selected.reference.materialized_realization_id
        or selected.native.query
        != InterfaceSurveyQuery(parameters=query.parameters, membership=query.membership)
    ):
        raise ValueError("Preserved insert selection disagrees with its query or native records.")
    for native in (selected.native, selected.reference):
        expected = choices._pool.select(
            **native.address.model_dump(),
            materialized_realization_id=native.materialized_realization_id,
            query=native.query.model_dump(mode="json", by_alias=True),
        )
        # As for native survey selections, appended evaluations do not invalidate a record.
        if {k: v for k, v in expected.items() if k != "snapshot_digest"} != native.model_dump(
            mode="json", by_alias=True, exclude={"snapshot_digest"}
        ):
            raise ValueError(
                "Preserved insert selection disagrees with an exact recorded preparation."
            )
    options = {o["label"]: o for o in admitted_options(choices)}
    if surroundings_reasons(
        options[selected.materialized_realization_id],
        options[selected.reference.materialized_realization_id],
        (query.surroundings,),
    ):
        raise ValueError("Selected insert violates preserved surroundings at the requested stage.")
    return selected.native.model_dump(mode="json", by_alias=True)
