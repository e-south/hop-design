"""Keep a stopped family, explicitly choose a 4-nt loop, and retrieve the revision."""

import argparse
import json
from pathlib import Path

from hop_design import construction


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    base = json.loads(Path(__file__).with_name("product-request.json").read_text())
    base["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4]
    base["foldback"]["geometry"]["annealing_arm_lengths_bp"] = [7]
    base["foldback"]["search"].update(
        max_realizations=2, result_quota=2, max_retained_overhead_nt=21
    )
    request = {
        "schema": "hop.construction-family/v1",
        "base_request": base,
        "members": [{"name": "choices", "loop_side_paired_bp": 7}],
        "shared_properties": ["stem_sequence", "endpoint"],
        "bounds": {"max_members": 1, "max_total_search_nodes": 20000, "max_total_continuations": 1},
    }
    path = output / "family.json"
    path.write_text(json.dumps(request, indent=2) + "\n")
    construction.execute_construction_family(path, continuation="sole-witness").write(
        output / "original"
    )
    member = output / "original/members/choices/request.json"
    construction.prepare_construction_request(member).write(output / "prepared")
    selections = {}
    for local in ("foldback", "basal"):
        receipt = construction.discover_local_neighborhood(output / f"prepared/{local}.json")
        receipt.write(output / local)
        choices = construction.list_local_realizations(receipt)
        # This demonstration declares a 4-nt loop preference; never choose by enumeration order.
        eligible = [c for c in choices if local == "basal" or c.geometry.loop_length_nt == 4]
        if len(eligible) != 1:
            raise ValueError(
                "The declared demonstration choice is not unique; inspect the choices."
            )
        selections[local + "_path"] = output / f"{local}/result.json"
        selections[local + "_realization_id"] = eligible[0].realization_id
    construction.continue_construction_request(
        member, design_id="chosen-loop4", **selections
    ).write(output / "continued")
    construction.reconcile_construction_family(
        output / "original",
        source_member="choices",
        outcome_path=output / "continued",
        preferred_loop_nt=4,
    ).write(output / "revised")
    membership = {
        "schema": "hop.construction-set/v1",
        "baseline": "loop4",
        "members": [
            {
                "name": "loop4",
                "bundle_path": "revised/members/choices/outcome/construction",
                "selection_path": "revised/members/choices/choices/0/selection.json",
            }
        ],
        "shared_properties": ["stem_sequence", "endpoint"],
        "compared_properties": [],
    }
    selection = output / "set.json"
    selection.write_text(json.dumps(membership, indent=2) + "\n")
    construction.project_construction_family_report(
        output / "revised", selection=selection, baseline="choices"
    ).write(output / "comparison")
    print(
        f"Open {output / 'comparison/report.md'}; "
        "the original stopped request remains in revised/history/parent/."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out)
