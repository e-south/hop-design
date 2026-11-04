"""Define, inspect and explicitly retrieve a stage-aware molecular comparison."""

import argparse
import json
from pathlib import Path

from hop_design import construction


def run(case: str, output: Path, *, set_label: str | None, baseline: str | None) -> None:
    if (set_label is None) != (baseline is None):
        raise ValueError("Selection requires both --set and --baseline.")
    output.mkdir(parents=True, exist_ok=False)
    request = Path(__file__).with_name(f"{case}.json")
    construction.prepare_scaffold_comparison(request).write(output / "preview")
    packet = construction.execute_scaffold_comparison(request)
    result = packet.write(output / "comparison")
    if set_label is not None and baseline is not None:
        selected = construction.select_scaffold_comparison(
            result, set_label=set_label, baseline=baseline
        )
        selected.write(output / "selected")
    facts = json.loads(packet.json_bytes)
    (output / "observations.json").write_text(
        json.dumps(
            {
                "evidence_kind": "software-check",
                "case": case,
                "outcome": facts["status"],
                "distinct_molecules": facts["distinct_molecules"],
                "available_sets": [s["label"] for s in facts["sets"]],
                "explicit_selection": set_label,
                "required_members": [m["name"] for m in facts["members"]],
                "examined_failures": len(facts["examined_failures"]),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=("crossed", "methods", "hairpin", "grouped", "loop-sequences"),
        required=True,
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--set", dest="set_label")
    parser.add_argument("--baseline")
    args = parser.parse_args()
    run(args.case, args.out, set_label=args.set_label, baseline=args.baseline)
