"""
--------------------------------------------------------------------------------
HOP Design
scripts/benchmarks/local_discovery.py

Measures query retention, durable execution, and replay without scientific input changes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import cProfile
import json
import platform
import tempfile
import time
import tracemalloc
from pathlib import Path

from hop_design.construction import discover_local_neighborhood, discover_local_neighborhoods
from hop_design.serialization import sha256_digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--counts", nargs="+", type=int, default=[2, 16])
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    expected = discover_local_neighborhood(args.request).json_bytes
    profile = cProfile.Profile()
    observations = []
    with tempfile.TemporaryDirectory(prefix="hop-local-measurement-") as temporary:
        for count in args.counts:
            if count < 1:
                parser.error("counts must be positive")
            for repeat in range(3):
                output = Path(temporary) / f"{count}-{repeat}"
                for mode in ("retained_queries", "durable_queries", "resume_replay"):
                    tracemalloc.start()
                    started = time.perf_counter()
                    profile.enable()
                    if mode == "retained_queries":
                        results = [discover_local_neighborhood(args.request) for _ in range(count)]
                        assert all(result.json_bytes == expected for result in results)
                        del results
                    else:
                        receipt = discover_local_neighborhoods(
                            [args.request] * count,
                            output,
                            resume=mode == "resume_replay",
                            batch_size=4,
                        )
                        assert receipt.finished and receipt.completed_requests == count
                    profile.disable()
                    elapsed = time.perf_counter() - started
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    observations.append(
                        {
                            "queries": count,
                            "repeat": repeat,
                            "mode": mode,
                            "seconds": elapsed,
                            "peak_traced_bytes": peak,
                        }
                    )
                assert all(result.json_bytes == expected for result in receipt.iter_results())
    if args.profile:
        profile.dump_stats(args.profile)
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "canonical_result": sha256_digest(expected),
                "observations": observations,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
