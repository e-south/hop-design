"""Discover loop variants, preserve their surroundings and retrieve a controlled comparison."""

import argparse
import json
import statistics
import time
from pathlib import Path

from hop_design import construction


def run(output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False)
    request = json.loads(Path(__file__).with_name("request.json").read_bytes())
    request["product"]["foldback"]["geometry"].pop("loop_sequences", None)
    request["product"]["foldback"]["geometry"]["loop_lengths_nt"] = [4]
    request["product"]["foldback"]["search"]["scope"] = "all_realizations"
    request["max_continuations_per_branch"] = 8
    request["max_branches"] = 4
    base = output / "request.json"
    base.write_text(json.dumps(request, indent=2) + "\n")
    start = time.perf_counter()
    intent = construction.author_molecular_edit(
        base,
        end_placements=((0, 0), (6, 6)),
        basal_nick_enzyme_ids=("example:enzyme/nb.bsrdi@1", "example:enzyme/nb.btsi@1"),
    ).write(output / "intent")
    evaluated = construction.execute_molecular_edit(intent / "edit.json")
    options = evaluated.write(output / "alternatives")
    evaluation_seconds = time.perf_counter() - start
    native = json.loads(evaluated.json_bytes)
    start = time.perf_counter()
    pool = construction.load_scaffold_exploration(options)
    admission_seconds = time.perf_counter() - start
    request = {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    all_choices = construction.query_scaffold_variants(pool, request)
    all_choices.write(output / "all-choices")
    observed = json.loads(all_choices.json_bytes)
    loops = {v["sequences"][0]["sequence"]: v for v in observed["variants"]}

    def named(word: str, nickase: str) -> str:
        labels = [
            o["label"]
            for o in native["options"]
            if o["label"] in loops[word]["option_labels"]
            and o["target_facts"]["basal_nick_enzyme_id"] == nickase
        ]
        if len(labels) != 1:
            raise ValueError(
                "Review the evaluated pool: this example expects one exact preparation."
            )
        return labels[0]

    bsrdi = named("AAAA", "example:enzyme/nb.bsrdi@1")
    btsi = named("AAAA", "example:enzyme/nb.btsi@1")
    aaca = named("AACA", "example:enzyme/nb.btsi@1")
    controlled = {
        **request,
        "reference": bsrdi,
        "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
    }
    locked = construction.query_scaffold_variants(pool, controlled)
    locked.write(output / "bsrdi-background")
    assert aaca not in json.loads(locked.json_bytes)["compatible_options"]
    controlled["reference"] = btsi  # Explicit background change; never changed by a variant query.
    controlled["pins"] = [
        {
            "neighborhood": "loop",
            "variant_ids": [
                loops["AAAA"]["variant_id"],
                loops["AACA"]["variant_id"],
            ],
        }
    ]
    comparison = construction.query_scaffold_variants(pool, controlled)
    comparison.write(output / "btsi-comparison")
    comparison_summary = json.loads(comparison.json_bytes)
    assert set(comparison_summary["compatible_options"]) == {btsi, aaca}
    samples = []
    for _ in range(100):
        start = time.perf_counter()
        repeated = construction.query_scaffold_variants(pool, controlled)
        samples.append(time.perf_counter() - start)
        assert repeated.json_bytes == comparison.json_bytes
    construction.project_scaffold_variant(pool, comparison, option_label=aaca).write(
        output / "preview"
    )
    start = time.perf_counter()
    selected = construction.select_scaffold_variants(
        options, comparison, members={"aaaa": btsi, "aaca": aaca}, baseline="aaaa"
    )
    selected.write(output / "selected")
    retrieval_seconds = time.perf_counter() - start
    timing = {
        "evaluation_seconds": evaluation_seconds,
        "admission_seconds": admission_seconds,
        "warm_query_repeats": len(samples),
        "warm_query_median_ms": statistics.median(samples) * 1000,
        "warm_query_p95_ms": sorted(samples)[94] * 1000,
        "retrieval_seconds": retrieval_seconds,
    }
    (output / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")
    summary = {
        "complete_preparations": len(native["options"]),
        "examined_failures": len(observed["examined_failures"]),
        "coverage": observed["coverage"],
        "aaca_excluded_on_bsrdi_background": True,
        "controlled_members": ["AAAA", "AACA"],
        "set_id": json.loads(selected.json_bytes)["set_id"],
        "query_digest": comparison_summary["query_digest"],
        "producer": native["producer"],
    }
    (output / "observations.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    print(json.dumps(run(parser.parse_args().output), sort_keys=True))
