"""Require both loops, inspect a selected preparation, then retrieve the controlled set."""

import argparse
import json
import statistics
import time
from pathlib import Path

from hop_design import construction


def run(source: Path, output: Path, selected_set: str | None) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    pool = construction.load_scaffold_exploration(source)
    admission = time.perf_counter() - started
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    choices.write(output / "choices")
    query = json.loads(choices.json_bytes)
    request = {
        "result_digest": pool.result_digest,
        "query_digest": query["query_digest"],
        "required_members": [
            {"name": "aaaa", "loop_sequence": "AAAA"},
            {"name": "aaca", "loop_sequence": "AACA"},
        ],
        "shared_properties": ["release_interfaces"],
        "stage_controls": [{"stage": "hairpin", "property": "non_loop_sequences", "scope": "set"}],
        "max_group_evaluations": 256,
        "max_sets": 16,
    }
    comparison = construction.compare_scaffold_variants(pool, choices, request)
    comparison.write(output / "comparison")
    result = json.loads(comparison.json_bytes)
    observations = {
        "available_sets": result["sets"],
        "group_coverage": result["group_coverage"],
        "selected_set": selected_set,
        "admission_seconds": admission,
    }
    if selected_set is not None:
        matched = [s for s in result["sets"] if s["label"] == selected_set]
        if len(matched) != 1:
            raise ValueError("Choose a displayed compatible set explicitly.")
        label = matched[0]["members"]["aaca"]
        loop = next(v for v in query["variants"] if label in v["option_labels"])
        pinned = construction.query_scaffold_variants(
            pool,
            {
                **query["query"],
                "reference": label,
                "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
                "pins": [{"neighborhood": "loop", "variant_ids": [loop["variant_id"]]}],
            },
        )
        pinned.write(output / "pinned")
        inspection = {
            "result_digest": pool.result_digest,
            "query_digest": json.loads(pinned.json_bytes)["query_digest"],
            "option_label": label,
            "state": "hairpin",
        }
        start = time.perf_counter()
        hairpin = construction.inspect_scaffold_variant(pool, pinned, inspection)
        first_ms = (time.perf_counter() - start) * 1000
        molecular = json.loads(hairpin.json_bytes)["molecular_state"]
        focus = next(b["address"] for b in molecular["bases"] if b["neighborhood"] == "stem")
        stages = []
        for ordinal, state in enumerate(molecular["available_states"]):
            view = construction.inspect_scaffold_variant(
                pool,
                pinned,
                {
                    **inspection,
                    "state": state["state_id"],
                    "focus": focus,
                },
            )
            view.write(output / "states" / f"{ordinal:02d}-{state['phase']}")
            assert json.loads(view.json_bytes)["query_digest"] == inspection["query_digest"]
            stages.append(state["phase"])
        samples = []
        for _ in range(30):
            start = time.perf_counter()
            repeated = construction.inspect_scaffold_variant(
                pool, pinned, {**inspection, "state": "endpoint"}
            )
            samples.append((time.perf_counter() - start) * 1000)
            assert json.loads(repeated.json_bytes)["option_label"] == label
        assert (
            construction.query_scaffold_variants(
                pool, json.loads(pinned.json_bytes)["query"]
            ).json_bytes
            == pinned.json_bytes
        )
        start = time.perf_counter()
        chosen = construction.select_scaffold_variant_comparison(
            source, comparison, set_label=selected_set, baseline="aaaa"
        )
        chosen.write(output / "selected")
        observations.update(
            inspected_preparation=label,
            recorded_states=stages,
            first_projection_ms=first_ms,
            warm_projection_median_ms=statistics.median(samples),
            warm_projection_p95_ms=sorted(samples)[28],
            warm_projection_samples_ms=samples,
            retrieval_seconds=time.perf_counter() - start,
            set_id=json.loads(chosen.json_bytes)["set_id"],
        )
    (output / "observations.json").write_text(json.dumps(observations, indent=2) + "\n")
    return observations


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--select-set", help="Explicit set label after inspecting comparison/summary.json."
    )
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, args.select_set), sort_keys=True))
