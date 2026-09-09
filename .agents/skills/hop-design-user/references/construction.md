# Payload-centered construction

Use this reference when one strict construction source and one separately
verified design bundle must produce exact, bounded construction-route
authorities and neutral scientific projections.

Read [the payload-centered construction API](../../../../docs/reference/python-api.md#payload-centered-construction)
and import only from `hop_design.construction`.

```python
from hop_design.construction import (
    compile_construction,
    load_verified_construction_bundle,
    project_complete_construction_summary,
)

compilation = compile_construction(
    "construction.yaml",
    design_bundle_path="build/design",
)
bundle_path = compilation.write("build/construction")
verified = load_verified_construction_bundle(bundle_path)
summary = project_complete_construction_summary(verified)
summary.write("build/construction-summary")
```

The source must use exact schema `hop.construction-source/v7`. It owns local
foldback and optional basal requests, the endpoint-specific materialization,
whole-route constraints, and finite enumeration policy. It cannot embed or
author the separate design authority, result IDs, realization IDs, projection
choices, output paths, timestamps, or environment records.

- Inspect `status`, `valid_realizations`, `examined_combinations`, and
  `nominal_combinations` before interpreting a receipt.
- Preserve `complete`, `infeasible`, and `truncated`; a missing realization is
  not automatically infeasible, and a truncated result is not definitive.
- Every route specifies source ssDNA and its duplex-materialization primers.
  A direct hairpin endpoint omits basal discovery and endpoint auxiliaries.
  PCR-bearing endpoints additionally require a matching basal request, adapter,
  and endpoint primers, each resolved under an explicit material policy.
- A selected source partition supplies concurrent cleanup nicks to PCR-bearing
  routes. It must preserve the same prepared source and exact joining strands.
- Write a `ConstructionCompilation` only to a new destination. Load it through
  `load_verified_construction_bundle()` at a later handoff boundary; there is
  no separate public construction verify verb.
- Use `project_foldback_feasibility()` for the verified foldback authority.
  Use `project_basal_feasibility()` only when the route contains a basal
  authority.
- Call `project_retained_overhead_frontier(..., family="foldback" | "basal")`
  to inspect accessibility across retained construction-sequence budgets.
- Use `project_complete_construction_summary()` for lossless route accounting.
- Call `project_construction_trajectory()` only with an explicit ID from
  `materialized_realization_ids`. Never auto-select a realization.
- A `ConstructionProjection` contains canonical JSON, SVG, and optional CSV
  bytes. Its create-only `write()` publishes a non-authoritative projection
  packet, not a second construction authority.

Construction compilation establishes deterministic digital discovery,
materialization, composition, verification, and projection under declared
inputs. It does not establish physical construction, destination
compatibility, QC, biological activity, yield, route performance, or an
optimized route.
