"""Partial local witnesses from already replayed discovery packets, never whole products."""

import json
from pathlib import Path
from typing import Any


def local_support(root: Path, native: dict[str, Any]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for branch in native["branches"]:
        folder = (root / branch["report"]).parent
        for family in ("foldback", "basal"):
            path = folder / "locals" / family / "result.json"
            if not path.exists():
                continue  # Direct hairpin preparations have no basal local packet.
            for item in json.loads(path.read_bytes())["realizations"]:
                identity = item[f"{family}_realization_id"]
                if identity in records:
                    if branch["branch_id"] not in records[identity]["branch_ids"]:
                        records[identity]["branch_ids"].append(branch["branch_id"])
                    continue
                geometry = item["local_realization"]["achieved_geometry"]
                if family == "foldback":
                    arm, displacement = (
                        geometry["annealing_arm_length_bp"],
                        geometry["junction_offset_nt"],
                    )
                    values = {
                        "foldback_arm_bp": arm,
                        "join_offset_nt": displacement,
                        "self_paired_arm_bp": arm - displacement,
                        "loop_nt": geometry["loop_length_nt"],
                        "loop_word": item["loop_sequence"],
                        "foldback_strand": geometry["nick_strand"],
                        "foldback_method": item["foldback_nick"]["enzyme_id"],
                    }
                else:
                    values = {
                        "basal_nick_offset_nt": geometry["nick_offset_nt"],
                        "basal_strand": geometry["nick_strand"],
                        "basal_method": item["basal_nick"]["enzyme_id"],
                    }
                    for pair in item["projection"]["pairing_state"]["pairs"]:
                        position = pair["position_from_ligation"]
                        for key, field in (
                            ("source_base", "source_base"),
                            ("adapter_base", "adapter_base"),
                            ("pair_class", "pair_class"),
                        ):
                            values[f"basal_{key}_{position}"] = pair[field]
                records[identity] = {
                    "local_realization_id": identity,
                    "branch_ids": [branch["branch_id"]],
                    "scope": f"{family}_local_only",
                    "values": values,
                    "complete_preparation_status": "not_established_by_local_record",
                    "source": path.relative_to(root).as_posix(),
                }
    return list(records.values())
