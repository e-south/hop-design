# Run the public lifecycle

Start with a request that returns a complete preparation. Measure discovery,
reopening, queries over loaded results, the molecular atlas and retrieval
separately. A fast filter says little about the cost of finding or verifying its
input molecules. In this guide, admission means checking a result before using
it; reopening a saved result requires file checks and deterministic replay. A warm
query reuses an already loaded result.

Save a construction intent as `intent.json`. The
[discovery guide](../../guides/discover-designs.md) describes its stem, product and
optional scaffold constraints. Run from the
[source checkout](../../guides/install.md#work-from-source):

```bash
# Record timing and memory for the same request in three fresh trials.
mkdir -p .artifacts
uv run --locked python scripts/benchmarks/design_lifecycle.py intent.json \
  --max-evaluations 4 --repeats 3 > .artifacts/lifecycle.json
```

The script checks repeatable selection, coverage, atlas content and handoff files.
Each trial uses a fresh temporary directory and removes it on success, failure or
interruption. Only the requested measurements remain. A request without a complete
preparation raises; it cannot produce a successful retrieval measurement.

The JSON records each phase's seconds, three-run medians, the executing producer
and process peak resident memory. Run before and after measurements in separate
processes with the same request, limits and environment. Source changes alter
producer-bound digests; use same-producer replay comparisons to establish artifact
equality and compare exact molecular identities across versions.

For diagnostics, add `--profile .artifacts/lifecycle.prof` or `--allocations`.
The profile output includes disjoint self-time groups and separately named
inclusive entry costs. Inclusive costs overlap; do not add them together or
interpret time spent in a validator as proof of which molecular phase caused it.
Profiling and allocation tracing add overhead, so measure latency separately.
Allocation tracing reports current and peak Python allocations per trial; resident
memory includes native allocations and is the high-water mark of the whole process.
Use `scripts/benchmarks/local_discovery.py` when the bottleneck is local enumeration.

## Reuse only the authority already established

| Boundary | Reuse allowed | Checks retained |
| --- | --- | --- |
| Bounded option generation | Identical successful local proofs within the call | Strict models, complete route, actual published files, all candidate outcomes |
| Saved discovery admission | Identical local proofs within the captured pool | File inventory, digest, producer, route and projection replay |
| Branch projection | Verified candidate receipts from that invocation | Binding to the selected preparation and branch |
| Candidate publication | Its fresh compilation, after staged admission | Actual published inventory, manifest and exact artifact bytes |
| Selected-set retrieval | Receipts from its one admitted snapshot | Membership, reference, material reuse and chemistry |
| Independent public load | No previous proof scope | Fresh admission and replay |

Local proof reuse is bounded to 64 entries and 8 MiB of canonical proof content.
The key includes the complete result, producer and replay policy. Changed inputs
must replay; failed results never enter the cache. Exiting or interrupting the call
discards the scope. No path, modification-time or process-wide verification cache
can stand in for these checks. See [reliability](../../../RELIABILITY.md).

The focused checks are `test_construction_bundle_replay_cost.py` for replay and
byte parity, `test_local_replay_scope.py` for cache lifetime and limits, and
`test_lifecycle_benchmark.py` for interrupted-run cleanup.
