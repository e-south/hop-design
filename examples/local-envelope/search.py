"""
--------------------------------------------------------------------------------
HOP Design
examples/local-envelope/search.py

Enumerates independent local geometry budgets around a caller-supplied public payload.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path

import yaml

import hop_design.construction as construction


def _requests(base, *, basal_budget, foldback_budget):
    end = base["geometry_domain"]["future_release"]["cohesive_end_sequence"]
    if type(basal_budget) is not int or basal_budget < len(end):
        raise ValueError("The basal coordinate budget must contain the requested end")
    if type(foldback_budget) is not int or foldback_budget < 9:
        raise ValueError("The foldback budget must contain the model's 3-bp arm and 3-nt cap")
    for n in range(basal_budget):
        for e in range(basal_budget - len(end) + 1):
            for orientation in ("forward", "reverse"):
                request = copy.deepcopy(base)
                window = max(1, e + len(end) - n)
                request["geometry_domain"].update(
                    nick_strand="any",
                    nick_offsets_nt=[n],
                    minimum_adapter_annealing_nt=None,
                    pairing_constraints=[
                        {"position_from_ligation": i, "allowed_class": "match"}
                        for i in range(window)
                    ],
                )
                request["geometry_domain"]["future_release"].update(
                    orientation=orientation, payload_end_offset_bp=e
                )
                request["search"].update(max_retained_overhead_nt=basal_budget)
                yield {"family": "basal", "n": n, "e": e, "orientation": orientation}, request
    for arm in range(3, (foldback_budget - 3) // 2 + 1):
        for cap in range(3, foldback_budget - 2 * arm + 1):
            request = copy.deepcopy(base)
            request.update(family="foldback", endpoint="ssdna_hairpin")
            request["geometry_domain"] = {
                "family": "foldback",
                "nick_strand": "any",
                "annealing_arm_lengths_bp": [arm],
                "loop_lengths_nt": [cap],
                "junction_offsets_nt": list(range(arm + 1)),
                "minimum_annealing_arm_length_bp": 3,
                "minimum_loop_length_nt": 3,
            }
            provisioning = request["enzyme_provisioning"]
            nicks = [
                enzyme["enzyme_id"]
                for enzyme in provisioning["catalog"]["enzymes"]
                if enzyme["enzyme_class"] == "nickase"
                and enzyme["enzyme_id"] in provisioning["allowed_enzyme_ids"]
            ]
            provisioning["allowed_enzyme_ids"] = nicks
            provisioning["role_restrictions"] = [
                {"role": "foldback_nick", "allowed_enzyme_ids": nicks}
            ]
            request["search"].update(max_retained_overhead_nt=foldback_budget)
            yield {"family": "foldback", "A": arm, "C": cap}, request


def search_example(source: Path, output: Path, *, basal_budget: int, foldback_budget: int):
    """Retain every exact request and result; report incomplete coverage explicitly."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Output already exists: {output}")
    base = yaml.safe_load(source.read_text())
    if base["family"] != "basal":
        raise ValueError("Use a basal request to declare payload, catalog, and endpoint")
    release = base["geometry_domain"]["future_release"]
    if (
        release["recognition_material"] != "source_duplex"
        or release["product_end"] != "right"
        or release["overhang_end"] != "five_prime"
        or base["search"].get("sequence_partition") is not None
    ):
        raise ValueError(
            "This coordinate example requires an unpartitioned source-duplex right 5-prime end"
        )
    base["search"].update(scope="all_realizations", stop="exhaustive")
    requests = list(_requests(base, basal_budget=basal_budget, foldback_budget=foldback_budget))
    output.mkdir(parents=True)
    rows = []
    for ordinal, (geometry, request) in enumerate(requests):
        directory = output / f"{ordinal:04d}"
        directory.mkdir()
        source_path = directory / "request.json"
        source_path.write_text(json.dumps(request, indent=2) + "\n")
        receipt = construction.discover_local_neighborhood(source_path)
        receipt.write(directory / "result")
        rows.append(
            {
                **geometry,
                "completion": receipt.completion,
                "feasibility": receipt.feasibility,
                "observed_witness_count": receipt.realization_count,
                "result": f"{ordinal:04d}/result/result.json",
            }
        )
    (output / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    with (output / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(dict.fromkeys(key for row in rows for key in row))
        )
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Enumerate local geometry under explicit budgets.")
    parser.add_argument(
        "--request", type=Path, default=Path(__file__).parents[1] / "basal-junction/request.yaml"
    )
    parser.add_argument("--basal-budget", type=int, required=True)
    parser.add_argument("--foldback-budget", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = search_example(
        args.request, args.out, basal_budget=args.basal_budget, foldback_budget=args.foldback_budget
    )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
