"""Translate hairpin permissions into the existing exact product-request owner."""

from copy import deepcopy
from typing import Any

from hop_design.models.construction.product_request import ProductRequest
from hop_design.serialization import canonical_json_bytes


def hairpin_request(stem: str, product: str, permissions: dict[str, Any]) -> ProductRequest:
    source = deepcopy(permissions)
    source.update(
        schema="hop.product-request/v1",
        stem_arm=stem,
        endpoint="ssdna_hairpin" if product == "hairpin" else product,
        ends=None,
        release=None,
        enumeration={"pruning": "disabled", "max_combinations": 1, "max_realizations": 1},
    )
    for name in ("foldback", "basal"):
        job = source.get(name)
        if job is None:
            continue
        overhead = job.pop("max_retained_overhead_nt")
        job["search"] = {
            "max_retained_overhead_nt": overhead,
            "max_search_nodes": 1000,
            "max_realizations": 64,
            "scope": "existence",
            "stop": "result_quota",
            "result_quota": 64,
        }
        if name == "basal":
            annealing = job.pop("annealing_lengths_nt")
            if len(annealing) != 1:
                raise ValueError(
                    "Hairpin association requires one adapter annealing minimum in its context."
                )
            job["geometry"]["minimum_adapter_annealing_nt"] = annealing[0]
    return ProductRequest.model_validate_json(canonical_json_bytes(source))
