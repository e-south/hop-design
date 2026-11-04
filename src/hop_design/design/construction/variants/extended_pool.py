"""Compose verified snapshots for inspection; never splice molecular components."""

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..discovery.admission import CapturedDiscovery


def _prefixed(record: dict[str, Any], prefix: str, fields: tuple[str, ...]) -> dict[str, Any]:
    value = deepcopy(record)
    for field in fields:
        value[field] = f"{prefix}/{value[field]}"
    return value


def merge_captured_pools(
    root: Path,
    previous: CapturedDiscovery,
    additional: CapturedDiscovery,
    protected: ProtectedRoot,
    *,
    active_request: bytes | None = None,
) -> CapturedDiscovery:
    branches, options, receipts, planned = [], [], {}, []
    seen = set()
    for prefix, captured in (("previous", previous), ("additional", additional)):
        source, native, admitted, _ = captured
        shutil.copytree(source, root / prefix)
        plan = json.loads((source / "intent/summary.json").read_bytes())
        for entry in plan["branches"]:
            record = deepcopy(entry)
            record["coverage_record_id"] = (
                prefix + ":" + entry.get("coverage_record_id", entry["branch_id"])
            )
            planned.append(record)
        new_prefix = "more-" + sha256_digest(canonical_json_bytes(native))[7:19] + "-"
        for original in native["branches"]:
            branch = _prefixed(original, prefix, ("request", "report"))
            branch["coverage_record_id"] = (
                prefix + ":" + original.get("coverage_record_id", original["branch_id"])
            )
            if prefix == "additional":
                branch["label"] = new_prefix + branch["label"]
            for failure in branch["failures"]:
                failure["outcome"] = f"{prefix}/{failure['outcome']}"
            for exclusion in branch.get("parameter_exclusions", []):
                exclusion["preparation"] = f"{prefix}/{exclusion['preparation']}"
            branches.append(branch)
        for original in native["options"]:
            identity = original["materialized_realization_id"]
            if identity in seen:
                continue
            seen.add(identity)
            option = _prefixed(
                original, prefix, ("portrait", "closing_drawing", "product_stages", "preparation")
            )
            option["coverage_record_id"] = (
                prefix + ":" + original.get("coverage_record_id", original["branch_id"])
            )
            option["selection"] = {k: f"{prefix}/{v}" for k, v in option["selection"].items()}
            if prefix == "additional":
                option["label"] = new_prefix + option["label"]
                option["branch_label"] = new_prefix + option["branch_label"]
            receipts[option["label"]] = admitted[original["label"]]
            options.append(option)
    parent = previous[1]
    extra = additional[1]
    coverage = {
        key: parent["coverage"].get(key, 0) + extra["coverage"].get(key, 0)
        for key in (
            "permitted_branches",
            "evaluated_branches",
            "unexamined_branches",
            "evaluated_pairs",
            "unexamined_pairs",
        )
    }
    coverage.update(
        global_route_feasibility="not_assessed",
        count_scope="branch_evaluation_records",
        exploration_complete=bool(
            parent["coverage"].get("exploration_complete")
            and extra["coverage"].get("exploration_complete")
        ),
    )
    native = {
        **parent,
        "branches": branches,
        "options": options,
        "coverage": coverage,
        "producer": extra["producer"],
        "source_producers": [parent["producer"], extra["producer"]],
    }
    intent = root / "intent"
    intent.mkdir()
    if active_request is None:
        shutil.copyfile(previous[0] / "intent/request.json", intent / "request.json")
    else:
        (intent / "request.json").write_bytes(active_request)
        native["request_digest"] = sha256_digest(active_request)
    (intent / "summary.json").write_bytes(canonical_json_bytes({"branches": planned}))
    return root, native, receipts, protected
