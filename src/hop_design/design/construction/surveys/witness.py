"""Recover one exact survey witness for either inspection or preparation export."""

import json
from pathlib import Path, PurePosixPath
from typing import Any

from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes

from ..public import VerifiedConstructionBundle, load_verified_construction_bundle
from .branches import SurveyBranches
from .index import SurveyIndex
from .partitions import PartitionPlans
from .projection import witness_projection


def recover_witness(
    index: SurveyIndex,
    request: InterfaceSurveyRequest,
    limits: SurveyEvaluationLimits,
    *,
    target: int,
    step: int,
    root: Path,
) -> tuple[VerifiedConstructionBundle, ProductRequest, dict[str, Any]]:
    """Replay the selected authority and bind it to its exact target/page/pair."""
    record = json.loads(index.record(target, step=step))
    if len(record["witnesses"]) != 1 or record["bundle"] is None:
        raise ValueError("Selected survey evaluation does not contain one complete witness.")
    product = SurveyBranches(request).product(target, branch=record["branch"], limits=limits)
    product = (
        PartitionPlans(request=request, limits=limits.sequence_space_limits)
        .get(product)
        .product(product, record["page"])
    )
    if index.get_object(record["product_request"]) != canonical_json_bytes(product):
        raise ValueError(
            "Survey witness request does not derive from its declared target and branch."
        )
    for name, digest in record["bundle"].items():
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or any(part in {".", ".."} for part in relative.parts)
            or relative.as_posix() != name
            or not relative.parts
            or "\\" in name
        ):
            raise ValueError("Invalid survey bundle artifact path.")
        artifact = root / name
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(index.get_object(digest))
    receipt = load_verified_construction_bundle(root)
    authority = receipt._verified_source()
    source = product.construction_source()
    actual = authority.result.request
    if (
        canonical_json_bytes(authority.foldback.result.neighborhood.request)
        != canonical_json_bytes(source.foldback)
        or authority.basal is None
        or canonical_json_bytes(authority.basal.result.discovery.request)
        != canonical_json_bytes(source.basal)
        or actual.release != source.composition.release
        or actual.materialization != source.composition.materialization
        or actual.whole_route_constraints != source.composition.whole_route_constraints
        or list(receipt.materialized_realization_ids) != record["witnesses"]
    ):
        raise ValueError("Survey witness molecular authority disagrees with its declared request.")
    foldbacks = authority.foldback.result.realizations
    basals = authority.basal.result.realizations
    total = len(foldbacks) * len(basals)
    if type(record["pair"]) is not int or not 0 <= record["pair"] < total:
        raise ValueError("Survey witness pair address is outside its recorded local domain.")
    fi, bi = divmod(record["pair"], len(basals))
    if (
        actual.selected_foldback_realization_id != foldbacks[fi].foldback_realization_id
        or actual.selected_basal_realization_id != basals[bi].basal_realization_id
        or record["recorded_pairs"] != total
    ):
        raise ValueError("Survey witness pair identity disagrees with its declared address.")
    projection = witness_projection(
        receipt, product.model_dump(mode="json"), record["witnesses"][0]
    )
    if canonical_json_bytes(record["projections"]) != canonical_json_bytes([projection]):
        raise ValueError("Survey plotting facts disagree with the replayed witness.")
    return receipt, product, record
