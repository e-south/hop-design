"""Preview a supported loop without changing permissions or selecting a preparation."""

import argparse
import json
import statistics
import time
from pathlib import Path

from hop_design import construction


def run(source: Path, output: Path, word: str, state: str, option: str | None) -> dict:
    if output.exists():
        raise FileExistsError(output)
    started = time.perf_counter()
    pool = construction.load_scaffold_exploration(source)
    admission = time.perf_counter() - started
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    summary = json.loads(choices.json_bytes)
    matches = [v for v in summary["variants"] if [s["sequence"] for s in v["sequences"]] == [word]]
    if len(matches) != 1:
        raise ValueError("Name one observed loop word from this saved pool.")
    request = {
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "variant_id": matches[0]["variant_id"],
        "state": state,
        "option_label": option,
    }
    samples = []
    first = None
    for _ in range(30):
        start = time.perf_counter()
        preview = construction.preview_scaffold_variant(pool, choices, request)
        samples.append((time.perf_counter() - start) * 1000)
        if first is None:
            first = preview.json_bytes
        assert preview.json_bytes == first
    assert (
        construction.query_scaffold_variants(pool, summary["query"]).json_bytes
        == choices.json_bytes
    )
    choices.write(output / "choices")
    preview.write(output / "preview")
    observations = {
        "status": json.loads(preview.json_bytes)["status"],
        "query_unchanged": True,
        "admission_seconds": admission,
        "samples_ms": samples,
        "median_ms": statistics.median(samples),
        "p95_ms": sorted(samples)[28],
    }
    (output / "observations.json").write_text(json.dumps(observations, indent=2) + "\n")
    return observations


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--word", required=True)
    parser.add_argument("--state", default="hairpin")
    parser.add_argument("--option")
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, args.word, args.state, args.option), indent=2))
