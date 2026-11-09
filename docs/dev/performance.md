# Performance and verification boundaries

Use these references to choose checks, measure a public workflow, or investigate
a measured bottleneck. Measure discovery, checking saved results, queries over
loaded results, atlas work and retrieval separately. A fast filter says little about the
cost of finding or verifying its input molecules.

## Start with a lifecycle measurement

Save a construction intent as `intent.json` using the
[discovery guide](../guides/discover-designs.md), then run from the
[source checkout](../guides/install.md#work-from-source). The request must return a
complete preparation for retrieval to be measured.

```bash
mkdir -p .artifacts
uv run --locked python scripts/benchmarks/design_lifecycle.py intent.json \
  --max-evaluations 4 --repeats 3 > .artifacts/lifecycle.json
```

The [lifecycle procedure](performance/measurement.md#run-the-public-lifecycle)
explains the output, profiling overhead, memory measures and comparison rules.

## Choose a reference for the task

| Task | Reference |
| --- | --- |
| Choose a local gate, understand CI or bound test workers | [Verification boundaries](performance/verification.md#choose-the-verification-boundary) |
| Measure lifecycle phases or understand proof reuse | [Measurement and authority reuse](performance/measurement.md#reuse-only-the-authority-already-established) |
| Investigate candidate generation, diversity allocation or resume costs | [Discovery and allocation](performance/discovery.md#discovery-and-allocation) |
| Investigate necessary end-pair projection or shared navigation | [Shared constraint screening](performance/shared-screening.md#shared-constraint-screening) |
| Investigate distance fitting, capture, opening or first inspection | [Molecular atlases](performance/atlas.md#fit-and-reopen-molecular-atlases) |
| Investigate hover, scene drawing, preview workers or browser memory | [Browser inspection](performance/inspection.md#browser-inspection) |
