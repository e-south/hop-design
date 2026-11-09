# Payload-centered construction

For a supplied stem and intended product, start with the
[design discovery guide](../../../../docs/guides/discover-designs.md). End words
are optional. It discovers
complete preparations and reuses one selection for views and oligo retrieval.
The lower-level workflow below is for an already authored construction source.

Use this reference to derive complete routes from one strict construction source
and one separately verified design bundle, then inspect views and tables from
the verified result. The source declares the search and material requirements;
the design bundle records the required sequence anatomy.

Read [the payload-centered construction API](../../../../docs/reference/python-api/construction/routes.md#payload-centered-construction)
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

The source must use exact schema `hop.construction-source/v8`. It owns local
foldback and optional basal requests, the endpoint-specific materialization,
whole-route constraints, and finite enumeration policy. It cannot embed or
author the separate design authority, result IDs, realization IDs, projection
choices, output paths, timestamps, or environment records.

For an explicitly selected direct hairpin, `construction compile-local-design`
accepts `--endpoint ssdna_hairpin` together with both `--hairpin-left-arm` and
`--hairpin-right-arm`. Each arm is exact DNA written in its own 5'-to-3'
direction; HOP validates their pairing. Supply the chosen foldback result and
realization ID and omit basal discovery options. These arm options are rejected
for PCR-bearing endpoints, which retain their basal discovery selection. The
resulting design bundle can be passed to `construction compile-selected` with
the same exact foldback selection and direct-hairpin construction source.

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
  `load_verified_construction_bundle()` at a later handoff boundary, or use
  `hop-design construction verify-complete BUNDLE` for the same replay in the CLI.
- Use `project_foldback_feasibility()` for the verified foldback authority.
  Use `project_basal_feasibility()` only when the route contains a basal
  authority.
- Call `project_retained_overhead_frontier(..., family="foldback" | "basal")`
  to inspect accessibility across retained construction-sequence budgets.
- Use `project_complete_construction_summary()` for lossless route accounting.
- Call `project_construction_trajectory()` only with an explicit ID from
  `materialized_realization_ids`. Never auto-select a realization.
- A `ConstructionProjection` contains canonical JSON, SVG, and optional CSV
  bytes. Its create-only `write()` saves those views as a projection packet;
  the verified construction result remains their authority.

Report the declared inputs, exact endpoint, complete materials, route status,
and verification result. The caller selects a preparation and checks its
products against the intended destination.
