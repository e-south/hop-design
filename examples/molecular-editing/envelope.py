"""Preview and evaluate an explicit move beyond a previously chosen geometry/word domain."""

import argparse
import hashlib
import json
from pathlib import Path

from hop_design import construction


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    pool = construction.load_scaffold_exploration(args.result)
    choices = construction.query_scaffold_variants(
        pool,
        {
            "schema": "hop.scaffold-variant-query/v2",
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "closing",
            "parameters": [
                {"key": "self_paired_arm_bp", "values": [9]},
                {"key": "join_offset_nt", "values": [2]},
                {"key": "loop_word", "values": ["AAAA"]},
                {"key": "left_gap", "values": [6]},
                {"key": "right_gap", "values": [6]},
            ],
        },
    )
    choices.write(args.output / "requested")
    preview = construction.preview_scaffold_envelope_revision(
        pool,
        choices,
        {
            "schema": "hop.scaffold-envelope-revision/v1",
            "changes": [
                {"path": "product.foldback.geometry.annealing_arm_lengths_bp", "value": []},
                {"path": "product.foldback.geometry.loop_lengths_nt", "value": []},
                {"path": "product.foldback.geometry.loop_sequences", "value": None},
                {"path": "parameters", "value": []},
            ],
        },
    )
    preview.write(args.output / "preview")
    result = construction.evaluate_scaffold_envelope_revision(
        pool,
        preview,
        max_branches=4,
        max_continuations_per_branch=4,
    )
    result_path = result.write(args.output / "evaluated")
    expanded = construction.load_scaffold_exploration(result_path)
    query = json.loads(choices.json_bytes)["query"]
    query["result_digest"] = expanded.result_digest
    refreshed = construction.query_scaffold_variants(expanded, query)
    refreshed.write(args.output / "choices")
    facts = json.loads(refreshed.json_bytes)
    if not facts["compatible_options"]:
        raise RuntimeError("This public example did not obtain its requested complete scaffold.")
    print(
        json.dumps(
            {
                "complete_preparations": len(facts["compatible_options"]),
                "preview_sha256": hashlib.sha256(preview.json_bytes).hexdigest(),
                "evaluation_sha256": hashlib.sha256(result.json_bytes).hexdigest(),
                "choices_sha256": hashlib.sha256(refreshed.json_bytes).hexdigest(),
                "retrieval": "Select an explicit compatible option from choices/summary.json.",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
