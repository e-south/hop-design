"""Query, bounded extension and exact retrieval over an existing public molecular pool."""

import argparse
import json
from pathlib import Path

from hop_design import construction


def run(source: Path, output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False)
    pool = construction.load_scaffold_exploration(source)
    query = {
        "schema": "hop.scaffold-variant-query/v2",
        "result_digest": pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
        "parameters": [
            {"key": "self_paired_arm_bp", "minimum": 7, "maximum": 7},
            {"key": "loop_word", "values": ["TTTC"]},
        ],
    }
    choices = construction.query_scaffold_variants(pool, query)
    choices.write(output / "choices")
    extension = construction.evaluate_scaffold_parameters(
        pool, choices, max_branches=1, max_continuations_per_branch=1
    ).write(output / "extended")
    expanded = construction.load_scaffold_exploration(extension)
    query["result_digest"] = expanded.result_digest
    refreshed = construction.query_scaffold_variants(expanded, query)
    facts = json.loads(refreshed.json_bytes)
    assert len(facts["compatible_options"]) == 1
    selected = construction.select_scaffold_variants(
        extension, refreshed, members={"tttc": facts["compatible_options"][0]}, baseline="tttc"
    )
    selected.write(output / "selected")
    return {
        "parameters": facts["query"]["parameters"],
        "complete_preparations": len(facts["compatible_options"]),
        "preserved_context_preparations": len(facts["choice_space"]["paths"]),
        "set_id": json.loads(selected.json_bytes)["set_id"],
        "local_support_count": len(facts["choice_space"]["local_support"]),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), sort_keys=True))
