"""Run the public 18-position scaffold task and retain the restricted alternative."""

import argparse
import json
from pathlib import Path

from hop_design import construction


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name("request.json")
    request = json.loads(source.read_bytes())
    construction.prepare_scaffold_discovery(source).write(output / "preview")
    discovery = construction.discover_scaffolds(source)
    options = discovery.write(output / "options")
    facts = json.loads(discovery.json_bytes)
    members = {}
    for loop in (3, 4, 6, 8):
        matches = [o for o in facts["options"] if o["geometry"]["loop_nt"] == loop]
        if len(matches) != 1:
            raise ValueError("This example requires exactly one preparation per requested loop.")
        members[f"loop{loop}"] = matches[0]["label"]
    selected = construction.select_scaffold_options(
        options,
        members=members,
        baseline="loop3",
        shared_properties=(
            "open_side_paired_positions",
            "loop_side_paired_bp",
            "non_loop_sequences",
            "regional_contacts",
            "regional_joins",
            "terminal_chemistry",
            "release_interfaces",
        ),
        compared_properties=("loop_nt",),
    )
    selected.write(output / "selected")
    request["preparation_changes"]["adapter_redesign"] = "preserve"
    restricted = output / "restricted-request.json"
    restricted.write_text(json.dumps(request, indent=2) + "\n")
    failure = construction.discover_scaffolds(restricted)
    failure.write(output / "restricted")
    if json.loads(failure.json_bytes)["options"]:
        raise ValueError("The restricted example must retain the scoped dimension failure.")
    (output / "observations.json").write_text(
        json.dumps(
            {
                "requested_open_side_positions": 18,
                "selected_members": members,
                "complete_preparations": len(facts["options"]),
                "manual_internal_geometry_edits": 0,
                "restricted_preparations": len(json.loads(failure.json_bytes)["options"]),
                "evidence_kind": "agent-software-check",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
