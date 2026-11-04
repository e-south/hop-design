"""Recover a controlled loop series from complete but mismatched preparations."""

import argparse
import json
from pathlib import Path

from hop_design import construction


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    base = json.loads(Path(__file__).with_name("product-request.json").read_text())
    base["foldback"]["geometry"].update(loop_lengths_nt=[3, 4], annealing_arm_lengths_bp=[7, 8])
    base["foldback"]["search"].update(
        max_realizations=8, result_quota=8, max_retained_overhead_nt=21
    )
    shared = [
        "stem_sequence",
        "endpoint",
        "release_interfaces",
        "open_side_paired_positions",
        "loop_side_paired_bp",
        "terminal_chemistry",
        "non_loop_sequences",
        "regional_contacts",
        "regional_joins",
    ]
    request = {
        "schema": "hop.construction-family/v1",
        "base_request": base,
        "members": [{"name": "loop3", "loop_nt": 3}, {"name": "loop4", "loop_nt": 4}],
        "shared_properties": shared,
        "bounds": {"max_members": 2, "max_total_search_nodes": 40000, "max_total_continuations": 2},
    }
    path = output / "family.json"
    path.write_text(json.dumps(request, indent=2) + "\n")
    construction.prepare_construction_family(path).write(output / "preview")
    current = construction.execute_construction_family(path, continuation="sole-witness").write(
        output / "original"
    )
    # Declare the initial preparations explicitly: different extensions prevent the comparison.
    for name, extension in (("loop3", 7), ("loop4", 8)):
        member = current / "members" / name / "request.json"
        inputs = construction.prepare_construction_request(member).write(
            output / (name + "-inputs")
        )
        selections = {}
        for local in ("foldback", "basal"):
            receipt = construction.discover_local_neighborhood(inputs / (local + ".json"))
            directory = receipt.write(output / (name + "-" + local))
            choices = [
                c
                for c in construction.list_local_realizations(receipt)
                if local == "basal" or c.geometry.annealing_arm_length_bp == extension
            ]
            if len(choices) != 1:
                raise ValueError("Demonstration choice is not unique; inspect local choices.")
            selections[local + "_path"] = directory / "result.json"
            selections[local + "_realization_id"] = choices[0].realization_id
        outcome = construction.continue_construction_request(
            member, design_id="initial-" + name, **selections
        ).write(output / (name + "-outcome"))
        current = construction.reconcile_construction_family(
            current, source_member=name, outcome_path=outcome
        ).write(output / ("initial-" + name))
    construction.project_construction_family_report(current, baseline="loop3").write(
        output / "before"
    )
    matched = construction.match_construction_family(
        current, reference_member="loop3", reference_choice=0, max_continuations=2
    )
    matched.write(output / "matching")
    result = json.loads(matched.json_bytes)
    eligible = [
        (candidate, choice)
        for candidate in result["members"][0]["candidates"]
        for choice in candidate["choices"]
        if choice["compatible"]
    ]
    if len(eligible) != 1:
        raise ValueError(
            "Inspect matching choices; this example requires one compatible alternative."
        )
    candidate, choice = eligible[0]
    # The caller now selects that exact compatible preparation. Matching itself selected nothing.
    revised = construction.reconcile_construction_family(
        current,
        source_member="loop4",
        outcome_path=output / "matching/candidates/loop4" / str(candidate["ordinal"]) / "outcome",
    ).write(output / "revised")
    membership = {
        "schema": "hop.construction-set/v1",
        "baseline": "loop3",
        "shared_properties": shared,
        "compared_properties": ["loop_nt"],
        "members": [
            {"name": name, **{key: "matching/" + value for key, value in selection.items()}}
            for name, selection in (
                ("loop3", result["reference"]["selection"]),
                ("loop4", choice["selection"]),
            )
        ],
    }
    selection = output / "set.json"
    selection.write_text(json.dumps(membership, indent=2) + "\n")
    construction.select_construction_set(selection).write(output / "selected")
    construction.project_construction_family_report(
        revised, selection=selection, baseline="loop3"
    ).write(output / "comparison")
    print(f"Compare before/report.pdf with {output / 'comparison/report.pdf'}.")
    print(f"Inspect {output / 'matching/report.md'}; retrieve selected/report.md.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out)
