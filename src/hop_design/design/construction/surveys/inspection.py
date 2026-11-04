"""Recover attempted local pairs from saved evidence without molecular replay."""

from typing import Any

from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.product_request import ProductRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..local_choices import _choices
from .index import SurveyIndex


def evaluated_local_pair(index: SurveyIndex, record: dict[str, Any]) -> dict[str, Any] | None:
    """Report the pair actually compiled, not the permitted/local-support roster.

    Navigation and empty local admissions have no complete compilation. Cached
    local records are checked against the saved request and coverage identities;
    this is structural inspection, not renewed discovery or molecular replay.
    """
    total = record.get("recorded_pairs", 0)
    if total == 0:
        return None
    product = ProductRequest.model_validate_json(index.get_object(record["product_request"]))
    source = product.construction_source()
    families = {}
    for family, request, model in (
        ("foldback", source.foldback, FoldbackNeighborhoodDiscoveryResult),
        ("basal", source.basal, BasalNeighborhoodDiscoveryResult),
    ):
        if request is None:
            raise ValueError("An evaluated survey pair requires both local requests.")
        content = index.cached(sha256_digest(canonical_json_bytes(request)))
        if content is None:
            raise ValueError("Evaluated local pair is missing its saved local result.")
        result = model.model_validate_json(content)
        embedded = (
            result.neighborhood.request
            if isinstance(result, FoldbackNeighborhoodDiscoveryResult)
            else result.discovery.request
        )
        coverage = record["local_coverage"][family]
        if (
            canonical_json_bytes(embedded) != canonical_json_bytes(request)
            or result.result_id != coverage["result_id"]
            or len(result.realizations) != coverage["realization_count"]
        ):
            raise ValueError("Evaluated local pair disagrees with saved local coverage.")
        families[family] = _choices(result)
    foldbacks, basals = families["foldback"], families["basal"]
    pair = record["pair"]
    if total != len(foldbacks) * len(basals) or not 0 <= pair < total:
        raise ValueError("Evaluated local pair lies outside its saved local results.")
    fi, bi = divmod(pair, len(basals))
    return {
        family: {
            "result_id": choice.source_result_id,
            "realization_id": choice.realization_id,
            "geometry": choice.geometry.model_dump(mode="json"),
            "enzyme_ids": list(choice.enzyme_ids),
            "nick_enzyme_id": choice.nick_enzyme_id,
        }
        for family, choice in (("foldback", foldbacks[fi]), ("basal", basals[bi]))
    }
