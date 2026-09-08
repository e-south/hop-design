"""
--------------------------------------------------------------------------------
HOP Design
examples/basal-junction/search.py

Searches a payload-adjacent junction and exports exact results with an inspection matrix.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hop_design.construction as construction


def search_example(source: Path, output: Path) -> dict[str, object]:
    """Run a public local search without filling outstanding route materials."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Output already exists: {output}; choose another directory.")
    receipt = construction.discover_local_neighborhood(source)
    matrix = construction.project_basal_minimum_overhead_matrix(receipt)
    result = json.loads(receipt.json_bytes)
    request = result["discovery"]["request"]
    ends = {
        realization["future_release_action"]["requirement"]["cohesive_end_sequence"]
        for realization in result["realizations"]
    }
    receipt.write(output / "result")
    matrix.write(output / "matrix")
    return {
        "payload_nt": len(request["payload"]["payload"]["sequence"]),
        "completion": receipt.completion,
        "feasibility": receipt.feasibility,
        "witness_count": receipt.realization_count,
        "accessible_end_count": len(ends),
        "accessible_ends": sorted(ends),
        "result_id": receipt.result_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search a basal junction around an unchanged payload."
    )
    parser.add_argument("--request", type=Path, default=Path(__file__).with_name("request.yaml"))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        summary = search_example(args.request, args.out)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Payload: {summary['payload_nt']} nt, unchanged")
    print(f"Search: {summary['completion']} / {summary['feasibility']}")
    print(f"Accessible cohesive ends: {summary['accessible_end_count']}")
    print("Ends (5-prime to 3-prime): " + ", ".join(summary["accessible_ends"]))
    print(f"Local witnesses: {summary['witness_count']}")
    print(f"Full search matrix: {args.out / 'matrix' / 'projection.svg'}")
    print(f"Data: {args.out / 'matrix' / 'projection.csv'}")
    print("Local solutions only; complete adapter, primers, and route still require validation.")


if __name__ == "__main__":
    main()
