"""Measure the public discovery-to-preparation lifecycle with disposable outputs."""

from __future__ import annotations

import argparse
import cProfile
import gc
import json
import platform
import pstats
import resource
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path

from hop_design import api, construction
from hop_design.serialization import sha256_digest


def profile_breakdown(stats: dict) -> dict:
    """Report disjoint self time and separately named inclusive entry costs.

    Library/runtime work remains visible rather than being guessed into a
    molecular phase. Inclusive entry costs overlap and must not be added.
    """
    rules = (
        (
            "endpoint_constraints",
            (
                "kernel/construction/release_",
                "surveys/completion/interfaces.py",
                "surveys/completion/frame_admission.py",
            ),
        ),
        (
            "handle_completion",
            (
                "surveys/completion/",
                "kernel/construction/source_context.py",
                "kernel/construction/context_order.py",
            ),
        ),
        (
            "local_search",
            (
                "kernel/construction/foldback/",
                "kernel/construction/basal/",
                "kernel/construction/sequence_sets.py",
                "design/construction/foldback/",
                "design/construction/basal/",
                "design/construction/local_",
                "design/construction/basal_space",
                "surveys/partitions.py",
                "surveys/foldback_population.py",
                "surveys/basal_population.py",
            ),
        ),
        ("checkpoint", ("surveys/index.py", "intents/hairpin_history.py")),
        ("admission_replay", ("/admission.py", "/verification/", "/replay", "complete/bundle.py")),
        ("complete_compilation", ("design/construction/complete/", "kernel/construction/")),
        ("descriptors", ("navigation/molecular_descriptor.py", "navigation/landscape_source.py")),
        ("molecular_distances", ("navigation/similarity.py", "navigation/similarity_numeric.py")),
        ("layout_fitting", ("navigation/similarity_layout.py", "/umap/", "/pynndescent/")),
        ("presentation", ("hop_design/export/",)),
    )
    entries = {
        ("surveys/evaluate.py", "compile_continuation"): "complete_attempt",
        ("execution/candidate.py", "evaluate_candidate"): "hairpin_complete_attempt",
        ("complete/discovery.py", "_replay_construction_result"): "complete_replay",
        ("surveys/partitions.py", "get"): "local_partition",
        ("surveys/completion/binding.py", "bind_context_completion"): "handle_binding",
        (
            "kernel/construction/release_population.py",
            "admit_release_population",
        ): "endpoint_population",
        (
            "kernel/construction/release_pair_relation.py",
            "necessary_end_pairs",
        ): "end_pair_relation",
    }
    groups = {name: {"calls": 0, "self_seconds": 0.0} for name, _ in rules}
    groups["other_engine_and_runtime"] = {"calls": 0, "self_seconds": 0.0}
    entry_calls = {}
    for (filename, _line, function), (
        _primitive,
        calls,
        own,
        cumulative,
        _callers,
    ) in stats.items():
        name = next(
            (name for name, paths in rules if any(p in filename for p in paths)),
            "other_engine_and_runtime",
        )
        groups[name]["calls"] += calls
        groups[name]["self_seconds"] += own
        for (path, symbol), entry in entries.items():
            if filename.endswith(path) and function == symbol:
                entry_calls[entry] = {"calls": calls, "inclusive_seconds": cumulative}
    return {
        "self_seconds": sum(row["self_seconds"] for row in groups.values()),
        "groups": groups,
        "entry_calls": entry_calls,
        "scope": "Profiled self time is disjoint; inclusive entry times overlap. "
        "Zero calls mean this workload did not exercise that entry.",
    }


def run_once(request: Path, max_evaluations: int) -> dict:
    """Use a fresh discovery and remove its files even when a phase fails."""
    timings = {}

    def measure(name, operation):
        start = time.perf_counter()
        result = operation()
        timings[name] = time.perf_counter() - start
        return result

    with tempfile.TemporaryDirectory(prefix="hop-lifecycle-benchmark-") as temporary:
        root = Path(temporary)
        choices = measure(
            "discover",
            lambda: construction.discover_designs(
                request, root / "choices", max_evaluations=max_evaluations
            ),
        )
        answer = choices.query()
        loaded = measure("reopen", lambda: construction.load_design_choices(root / "choices"))
        assert loaded.query() == answer
        measure("query_20", lambda: [loaded.query() for _ in range(20)])
        selected = loaded.sample(seed=0)
        assert choices.sample(seed=0) == selected
        atlas = measure("atlas", lambda: loaded.atlas(selected))
        handoff = measure("retrieve", lambda: loaded.retrieve(selected, root / "preparation"))
        assert handoff.materialized_realization_ids == (selected["materialized_realization_id"],)
        artifacts = {
            str(path.relative_to(root / "preparation")): sha256_digest(path.read_bytes())
            for path in sorted((root / "preparation").rglob("*"))
            if path.is_file()
        }
        result = {
            "seconds": timings,
            "matching_preparations": answer["matching_preparations"],
            "coverage": answer["coverage"],
            "selection": selected,
            "atlas_sha256": sha256_digest(atlas.json_bytes),
            "handoff": artifacts,
            "temporary_files": sum(path.is_file() for path in root.rglob("*")),
        }
    result["temporary_directory_removed"] = not root.exists()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="A public construction intent JSON file.")
    parser.add_argument("--max-evaluations", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--allocations", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1 or args.max_evaluations < 1:
        parser.error("repeats and max-evaluations must be positive")
    profile = cProfile.Profile() if args.profile else None
    observations = []
    for _ in range(args.repeats):
        gc.collect()
        if args.allocations:
            tracemalloc.start()
        if profile:
            profile.enable()
        try:
            observation = run_once(args.request, args.max_evaluations)
        finally:
            if profile:
                profile.disable()
            if args.allocations:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
        if args.allocations:
            observation["traced_current_bytes"] = current
            observation["traced_peak_bytes"] = peak
        observations.append(observation)
    if profile:
        profile.dump_stats(args.profile)
    for observation in observations[1:]:
        for key in ("selection", "coverage", "atlas_sha256", "handoff"):
            assert observation[key] == observations[0][key], key
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "producer": api.runtime_identity(),
                "profiling_enabled": profile is not None,
                **(
                    {"profile_breakdown": profile_breakdown(pstats.Stats(profile).stats)}
                    if profile
                    else {}
                ),
                "allocations_enabled": args.allocations,
                "process_peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                * (1 if platform.system() == "Darwin" else 1024),
                "median_seconds": {
                    phase: statistics.median(item["seconds"][phase] for item in observations)
                    for phase in observations[0]["seconds"]
                },
                "observations": observations,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
