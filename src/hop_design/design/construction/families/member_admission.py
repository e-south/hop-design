"""Verify one family member against its exact authored request and selected witnesses."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hop_design.design.construction.local_public import (
    LocalNeighborhoodDiscovery,
    load_verified_local_neighborhood,
)
from hop_design.design.construction.product_request import prepare_construction_request
from hop_design.design.construction.public import (
    VerifiedConstructionBundle,
    load_verified_construction_bundle,
)
from hop_design.design.source_documents import DEFAULT_RESULT_MAX_BYTES, load_source_mapping
from hop_design.serialization import canonical_json_bytes

from ..design_authority import compile_design_from_local_realizations
from ..execution.context import LocalSelection, describe_request_context
from ..execution.coverage import describe_local_coverage, describe_local_stop
from ..execution.outcome import describe_complete_outcome
from ..local_choices import list_local_realizations


@dataclass(frozen=True)
class AdmittedMember:
    name: str
    preview: dict[str, Any]
    outcome: dict[str, Any]
    receipt: VerifiedConstructionBundle | None


def _equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"Family {label} disagrees with the recorded request or verified result.")


def admit_member(
    root: Path,
    name: str,
    local_preview: dict[str, Any],
    expected_inputs: dict[str, bytes],
    *,
    producer: dict[str, Any],
    continuation: str = "sole-witness",
    external_design_id: bool = False,
    local_receipts: dict[str, LocalNeighborhoodDiscovery] | None = None,
) -> AdmittedMember:
    if continuation not in {"sole-witness", "explicit-selection"}:
        raise ValueError("Unknown member continuation policy.")
    for leaf in ("request.json", "construction.json"):
        _equal((root / leaf).read_bytes(), expected_inputs[leaf], leaf)
    prepared = prepare_construction_request(root / "request.json")
    outcome_root = root / "outcome"
    _equal(
        (outcome_root / "inputs/request.json").read_bytes(),
        prepared.request_json_bytes,
        "input request",
    )
    _equal(
        (outcome_root / "inputs/construction.json").read_bytes(),
        prepared.source_json_bytes,
        "input source",
    )
    source, component, expected, _ = describe_request_context(prepared, continuation=continuation)
    expected["producer"] = producer
    coverage = {}
    locals_ = {}
    stopped = False
    for family in ("foldback", "basal"):
        if source[family] is None:
            continue
        path = outcome_root / family / "result.json"
        if local_receipts is not None and family in local_receipts:
            local = local_receipts[family]
            # The enclosing admission has replayed this authority. Bind every
            # candidate's captured bytes to it; never trust a matching identifier.
            _equal(
                canonical_json_bytes(load_source_mapping(path, max_bytes=DEFAULT_RESULT_MAX_BYTES)),
                local.json_bytes,
                f"{name} {family} local authority",
            )
        else:
            local = load_verified_local_neighborhood(path)
        local_source = json.loads(local.json_bytes)
        container = local_source["neighborhood" if family == "foldback" else "discovery"]
        _equal(container["request"], source[family], f"{name} {family} request")
        locals_[family] = local
        coverage[family] = describe_local_coverage(local, family)
        stop = describe_local_stop(coverage[family], family)
        if stop is not None and continuation == "sole-witness":
            expected.update(stop)
            stopped = True
            break
    expected["local_coverage"] = coverage
    receipt = None
    if not stopped:
        receipt = load_verified_construction_bundle(outcome_root / "construction")
        result = receipt._verified_source().result
        selected_ids = (
            load_source_mapping(outcome_root / "summary.json").get(
                "selected_local_realizations", {}
            )
            if continuation == "explicit-selection"
            else {
                f: list_local_realizations(local)[0].realization_id for f, local in locals_.items()
            }
        )
        if set(selected_ids) != set(locals_):
            raise ValueError("Explicit continuation must identify each required local witness.")
        if continuation == "explicit-selection":
            expected["selected_local_realizations"] = selected_ids
        for family in locals_:
            if selected_ids[family] not in {
                c.realization_id for c in list_local_realizations(locals_[family])
            }:
                raise ValueError("Selected local witness does not belong to its recorded request.")
            authority = getattr(result, f"{family}_authority")
            _equal(canonical_json_bytes(authority), locals_[family].json_bytes, "local authority")
            _equal(
                getattr(result.request, f"selected_{family}_realization_id"),
                selected_ids[family],
                "selected local pair",
            )
        actual_composition = result.request.model_dump(mode="json", by_alias=True)
        for key, value in source["composition"].items():
            _equal(actual_composition[key], value, f"{name} {key}")
        selected_local: LocalSelection = {
            "foldback": locals_["foldback"],
            "foldback_realization_id": selected_ids["foldback"],
        }
        if "basal" in locals_:
            selected_local["basal"] = locals_["basal"]
            selected_local["basal_realization_id"] = selected_ids["basal"]
        design = compile_design_from_local_realizations(
            design_id=(
                result.request.design.spec.design_id
                if continuation == "explicit-selection" or external_design_id
                else "family-" + name
            ),
            payload_sequence=source["foldback"]["payload"]["payload"]["sequence"],
            endpoint=source["composition"]["endpoint"],
            hairpin_basal_arms=None
            if component is None
            else (component["left_arm"], component["right_arm"]),
            **selected_local,
        )
        _equal(design.spec, result.request.design.spec, f"{name} design specification")
        expected.update(describe_complete_outcome(receipt))
    _equal(load_source_mapping(outcome_root / "summary.json"), expected, f"{name} outcome")
    return AdmittedMember(name, local_preview, expected, receipt)
