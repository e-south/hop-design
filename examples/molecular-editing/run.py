"""Loop edit, complete alternatives and explicit portable selection through the public API."""

import argparse
import json
import time
from pathlib import Path

from hop_design import construction


def run(output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False)
    request = Path(__file__).with_name("request.json")
    start = time.perf_counter()
    preview = construction.author_molecular_edit(request, loop_sequences=("GAAA", "TTTC"))
    intent = preview.write(output / "intent")
    preview_seconds = time.perf_counter() - start
    start = time.perf_counter()
    evaluated = construction.execute_molecular_edit(intent / "edit.json")
    alternatives = evaluated.write(output / "alternatives")
    evaluate_seconds = time.perf_counter() - start
    summary = json.loads(evaluated.json_bytes)
    members = {}
    for word in ("GAAA", "TTTC"):
        matches = [
            o["label"] for o in summary["options"] if o["target_facts"]["loop_sequence"] == word
        ]
        if len(matches) != 1:
            raise ValueError(f"Review the alternatives: expected one complete {word} example.")
        members[word.lower()] = matches[0]
    start = time.perf_counter()
    pool = construction.load_scaffold_exploration(alternatives)
    choices = construction.query_scaffold_variants(
        pool,
        {
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
            "reference": members["gaaa"],
            "controls": [
                {"stage": "hairpin", "property": prop}
                for prop in ("non_loop_sequences", "non_loop_pairing", "terminal_chemistry")
            ],
        },
    )
    choices.write(output / "choices")
    construction.project_scaffold_variant(pool, choices, option_label=members["tttc"]).write(
        output / "preview"
    )
    selected = construction.select_scaffold_variants(
        alternatives, choices, members=members, baseline="gaaa"
    )
    selected.write(output / "selected")
    selection_seconds = time.perf_counter() - start
    (output / "timing.json").write_text(
        json.dumps(
            {
                "preview_seconds": preview_seconds,
                "evaluation_seconds": evaluate_seconds,
                "retrieval_seconds": selection_seconds,
            },
            indent=2,
        )
        + "\n"
    )
    return {
        "complete_options": len(summary["options"]),
        "loops": list(members),
        "set_id": json.loads(selected.json_bytes)["set_id"],
        "shared_surroundings": True,
        "conditional_query_digest": json.loads(choices.json_bytes)["query_digest"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    print(json.dumps(run(parser.parse_args().output), sort_keys=True))
