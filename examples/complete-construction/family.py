"""Specify a finite scaffold family and retrieve one explicit comparative set."""

import argparse
import json
from pathlib import Path

from run import hairpin_request

from hop_design import construction


def run(output: Path, endpoint: str = "insert") -> None:
    output.mkdir(parents=True, exist_ok=False)
    base = json.loads(Path(__file__).with_name("product-request.json").read_text())
    if endpoint == "hairpin":
        base = hairpin_request(base)
    base["foldback"]["search"]["max_retained_overhead_nt"] = 21
    names = [f"loop{loop}" for loop in (3, 4, 5)]
    members = [
        {"name": name, "loop_side_paired_bp": 7, "loop_nt": loop}
        for name, loop in zip(names, (3, 4, 5), strict=True)
    ]
    members.append({"name": "short-primer", "loop_side_paired_bp": 6, "loop_nt": 3})
    shared = [
        "stem_sequence",
        "endpoint",
        "release_interfaces",
        "open_side_paired_positions",
        "terminal_chemistry",
        "non_loop_sequences",
        "regional_contacts",
        "regional_joins",
    ]
    (output / "base-request.json").write_text(json.dumps(base, indent=2) + "\n")
    request = {
        "schema": "hop.scaffold-comparison/v1",
        "base_request": "base-request.json",
        "product": base["endpoint"],
        "vary": members,
        "hold": shared,
        "geometry_permissions": {"loop_nt": [3, 4, 5], "loop_side_paired_bp": [6, 7]},
        "display_preferences": [{"dimension": "loop_nt", "direction": "ascending"}],
        "bounds": {"max_members": 4, "max_total_search_nodes": 80000, "max_total_continuations": 4},
    }
    request_path = output / "comparison.json"
    request_path.write_text(json.dumps(request, indent=2) + "\n")
    authored = construction.author_construction_family(request_path)
    authored.write(output / "authored")
    request_path = output / "family.json"
    request_path.write_bytes((output / "authored/family.json").read_bytes())
    construction.prepare_construction_family(request_path).write(output / "preview")
    family = construction.execute_construction_family(request_path, continuation="sole-witness")
    family.write(output / "executed")
    summary = json.loads(family.json_bytes)
    choices = {member["name"]: member["choices"] for member in summary["members"]}
    # The author's comparative question explicitly names these three members.
    # Display ordering is never a selection rule; each must have exactly one choice.
    if any(len(choices[name]) != 1 for name in names):
        raise ValueError("The authored comparative set needs one complete choice per named member.")
    membership = {
        "schema": "hop.construction-set/v1",
        "baseline": "loop3",
        "shared_properties": [*shared, "loop_side_paired_bp"],
        "compared_properties": ["loop_nt"],
        "members": [
            {
                "name": name,
                "bundle_path": f"executed/members/{name}/outcome/construction",
                "selection_path": "executed/" + choices[name][0]["selection"],
            }
            for name in names
        ],
    }
    set_path = output / "set.json"
    set_path.write_text(json.dumps(membership, indent=2) + "\n")
    construction.select_construction_set(set_path).write(output / "selected")
    construction.project_construction_family_report(
        output / "executed",
        selection=set_path,
        baseline="loop3",
        edits=(("short-primer", "loop3"),),
    ).write(output / "comparison")
    print(
        f"Open {output / 'comparison/report.pdf'}; retrieve preparations through "
        f"comparison/report.md."
    )
    print("Retrieve selected/oligos.csv with selected/oligo-uses.csv and each preparation report.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--endpoint", choices=("insert", "hairpin"), default="insert")
    args = parser.parse_args()
    run(args.out, args.endpoint)
