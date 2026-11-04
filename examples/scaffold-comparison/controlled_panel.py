"""Request retained scaffold controls, target missing members and reuse a prior source."""

import argparse
import copy
import json
from pathlib import Path

from hop_design import construction


def panel_request():
    value = json.loads(Path(__file__).with_name("grouped.json").read_bytes())
    value["schema"] = "hop.comparison-brief/v3"
    words = ("AAA", "ATA", "GAA", "TTC")
    value["discovery"]["product"]["foldback"]["geometry"].update(
        loop_lengths_nt=[3], loop_sequences=list(words)
    )
    value["required_members"] = [
        {
            "name": f"{word.lower()}-{method}",
            "loop_sequence": word,
            "release_enzyme_id": f"example:enzyme/{enzyme}@1",
        }
        for word in words
        for method, enzyme in (("bsai", "bsai-hfv2"), ("bsmbi", "bsmbi-v2"))
    ]
    value["groups"] = [
        {
            "name": word.lower(),
            "members": [f"{word.lower()}-bsai", f"{word.lower()}-bsmbi"],
            "product_relationship": "identical",
        }
        for word in words
    ]
    value["stage_controls"] = [
        {"property": prop, "stage": "endpoint", "scope": "set"}
        for prop in ("non_loop_sequences", "non_loop_pairing", "terminal_chemistry")
    ]
    return value


def execute(value, output, name):
    path = output / f"{name}.json"
    path.write_text(json.dumps(value, indent=2) + "\n")
    construction.prepare_scaffold_comparison(path).write(output / f"{name}-preview")
    packet = construction.execute_scaffold_comparison(path)
    packet.write(output / name)
    return json.loads(packet.json_bytes)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    panel = panel_request()
    result = execute(panel, output, "panel")
    assert result["status"] == "comparison_available"
    assert result["distinct_molecules"] == {"hairpin": 8, "endpoint": 4}
    assert all(c["status"] == "shared" for c in result["sets"][0]["stage_controls"])
    # This recipe explicitly selects the sole displayed set; discovery itself
    # returns alternatives without choosing a winner or weakening an obligation.
    assert len(result["sets"]) == 1
    construction.select_scaffold_comparison(
        output / "panel", set_label="set-0001", baseline="aaa-bsai"
    ).write(output / "panel-selected")

    tight = copy.deepcopy(panel)
    tight.update(purpose="distinct_substrates", groups=[], between_groups=None, stage_controls=[])
    tight["required_members"] = [{"name": "ttc", "loop_sequence": "TTC"}]
    tight["discovery"].update(max_branches=1, max_continuations_per_branch=1)
    tight["discovery"]["product"]["foldback"]["search"].update(
        stop="result_quota", result_quota=1, max_realizations=1
    )
    targeted = execute(tight, output, "required-ttc")
    assert {o["loop_sequence"] for o in targeted["options"]} == {"TTC"}
    assert targeted["coverage"]["exploration_complete"] is False

    redesign = copy.deepcopy(panel)
    redesign["stage_controls"] = []
    redesign["required_members"] = [
        m for m in panel["required_members"] if m["name"] == "aaa-bsmbi"
    ]
    reference = {
        "bundle_path": "panel-selected/members/aaa-bsai/construction",
        "selection_path": "panel-selected/members/aaa-bsai/portrait/selection.json",
    }
    redesign["groups"] = [
        {
            "name": "aaa",
            "members": ["aaa-bsmbi"],
            "product_relationship": "identical",
            "product_reference": {**reference, "stage": "endpoint"},
        }
    ]
    preserved = execute(redesign, output, "preserved-product")
    assert preserved["status"] == "comparison_available"
    redesign["reuse_prior_materials"] = {"reference": reference, "roles": ["source_ssdna"]}
    reused = execute(redesign, output, "reused-source")
    assert reused["sets"] == []
    assert reused["members"][0]["status"] == "missing_from_evaluated_pool"

    reusable = copy.deepcopy(redesign)
    reusable["required_members"] = [m for m in panel["required_members"] if m["name"] == "aaa-bsai"]
    reusable["groups"][0]["members"] = ["aaa-bsai"]
    same_method = execute(reusable, output, "reused-source-compatible")
    assert same_method["status"] == "comparison_available"
    construction.select_scaffold_comparison(
        output / "reused-source-compatible", set_label="set-0001", baseline="aaa-bsai"
    ).write(output / "reused-source-selected")
    (output / "observations.json").write_text(
        json.dumps(
            {
                "evidence_kind": "software-check",
                "panel_molecules": result["distinct_molecules"],
                "panel_stage_controls": result["sets"][0]["stage_controls"],
                "targeted_words": sorted({o["loop_sequence"] for o in targeted["options"]}),
                "targeted_coverage": targeted["coverage"],
                "product_preservation": preserved["status"],
                "source_reuse_method_change": reused["status"],
                "source_reuse_original_method": same_method["status"],
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out)
