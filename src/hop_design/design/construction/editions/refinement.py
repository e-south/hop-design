"""Regional preservation from captured routes, using the live regional identity rules."""

import json
from typing import TYPE_CHECKING, Any, cast

from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.variants.applicability import validate_product_parameters
from hop_design.serialization import canonical_json_bytes

from ..discovery.molecules import route_materials
from ..intents.base import Source
from ..intents.query import resolve_query
from ..intents.refinement import load_design_query
from ..navigation.neighbor_work import NeighborStopped, check_neighbor_work
from ..variants.facts import regional_variants
from ..variants.refinement import refine_options
from .comparison import captured_route
from .materials import member_materials
from .projection import project_choices

if TYPE_CHECKING:
    from .reader import AtlasEdition


def validate_reference(edition: "AtlasEdition", query: DesignRefinementQuery) -> None:
    index = json.loads(edition._index)
    reference = query.reference
    if (
        reference.request_digest != index["request_digest"]
        or reference.snapshot_digest != index["snapshot_digest"]
        or reference.materialized_realization_id
        not in {p["materialized_realization_id"] for p in index["paths"]}
    ):
        raise ValueError("Preservation reference belongs to a different recorded snapshot.")


def captured_options(
    edition: "AtlasEdition", *, identities: set[str] | None = None
) -> list[dict[str, Any]]:
    """Derive control facts only for explicit members and their reference.

    Parameter filters alone cannot narrow this set: conditional facets relax one
    axis at a time. Exact membership does not relax, so its excluded routes need
    no preservation proof. A partial result never populates the whole-pool cache.
    """
    cached = getattr(edition, "_regional_options", None)
    paths = json.loads(edition._index)["paths"]
    if cached is None:
        try:
            options = []
            for path in paths:
                check_neighbor_work()
                if identities is not None and path["materialized_realization_id"] not in identities:
                    continue
                route = captured_route(edition, path["materialized_realization_id"])
                options.append(
                    {
                        **path,
                        "label": path["materialized_realization_id"],
                        "variants": regional_variants(route),
                        "material_roles": route_materials(route),
                    }
                )
        except NeighborStopped:
            raise
        except ValueError as error:
            raise ValueError(
                "This edition cannot verify preserved surroundings from its captured routes. "
                "Viewing and retrieval remain available."
            ) from error
        cached = canonical_json_bytes(options)
        if identities is None:
            edition._regional_options = cached
    else:
        # Cached derivations confer no authority on subsequently changed bytes.
        # Check the requested archives afresh before reusing their regional facts.
        for path in paths:
            check_neighbor_work()
            identity = path["materialized_realization_id"]
            if identities is None or identity in identities:
                member_materials(edition, identity)
    result = cast(list[dict[str, Any]], json.loads(cached))
    check_neighbor_work()
    return [o for o in result if identities is None or o["label"] in identities]


def _resolved_query(
    edition: "AtlasEdition", source: Source | None
) -> tuple[InterfaceSurveyQuery | DesignRefinementQuery, InterfaceSurveyQuery]:
    query = load_design_query(source)
    validate_product_parameters(query.parameters, edition.resolution["intent"]["product"])
    if isinstance(query, DesignRefinementQuery):
        validate_reference(edition, query)
    native = resolve_query(
        InterfaceSurveyQuery(parameters=query.parameters, membership=query.membership),
        edition.resolution["permissions"],
    )
    return query, native


def query_edition(edition: "AtlasEdition", source: Source | None) -> dict[str, Any]:
    query, native = _resolved_query(edition, source)
    result = project_choices(json.loads(edition._index), native)
    if isinstance(query, DesignRefinementQuery):
        query = query.model_copy(update={"parameters": native.parameters})
        result = refine_options(
            result,
            query,
            captured_options(
                edition,
                identities=(
                    {
                        p["materialized_realization_id"]
                        for p in result["paths"]
                        if query.includes_preparation(p["materialized_realization_id"])
                    }
                    | {query.reference.materialized_realization_id}
                    if query.membership is not None
                    else None
                ),
            ),
            validation="captured_complete_routes; no_current_producer_replay",
        )
    return result


def selection_query(
    edition: "AtlasEdition", identity: str, source: Source | None
) -> dict[str, Any]:
    """Validate a member without calculating every axis's conditional counts.

    Regional preservation still uses the complete proof operation. Ordinary
    predicates share normalization and membership checks with the cohort query.
    """
    query, native = _resolved_query(edition, source)
    if isinstance(query, DesignRefinementQuery):
        result = query_edition(edition, source)
        matched = any(
            p["matches"] and p["materialized_realization_id"] == identity for p in result["paths"]
        )
        normalized = result["query"]
    else:
        matched = edition._selection_index.accepts(identity, native)
        normalized = native.model_dump(mode="json", by_alias=True)
    if not matched:
        raise ValueError("No matching captured preparation; no search or relaxation occurred.")
    return cast(dict[str, Any], normalized)


def preserved_query(
    edition: "AtlasEdition", reference: Source, *, stage: str, except_neighborhood: str
) -> dict[str, Any]:
    selected = edition._selected(reference)
    index = json.loads(edition._index)
    query = DesignRefinementQuery.model_validate_json(
        canonical_json_bytes(
            {
                "reference": {
                    "request_digest": index["request_digest"],
                    "snapshot_digest": index["snapshot_digest"],
                    "materialized_realization_id": selected.materialized_realization_id,
                },
                "surroundings": {"stage": stage, "except_neighborhood": except_neighborhood},
            }
        )
    )
    validate_reference(edition, query)
    return query.model_dump(mode="json", by_alias=True)
