---
doc_id: hop-compile-construction-guide
title: Compile a payload-centered construction
intent: Compile one strict construction source against a separate verified design authority and export neutral scientific projections.
audience:
  - Python users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-31
doc_type: how-to
journey:
  - discover
  - verify
---

# Compile a payload-centered construction

Use `hop_design.construction` when the question is:

> Which exact complete construction routes follow from these local molecular
> requests and this separately verified hairpin design?

This is a specialist file-oriented workflow. It does not change the shorter
substrate-space journey and does not select an experimentally preferred route.

## Derive a design from selected local alternatives

When local discovery precedes design compilation, select exact realization ids
explicitly and derive the matching design before complete composition:

```python
import hop_design.construction as construction

design = construction.compile_design_from_local_realizations(
    design_id="selected-route-design",
    payload_sequence="GACA",
    endpoint="hairpin_pcr_duplex",
    foldback=verified_foldback_receipt,
    foldback_realization_id=selected_foldback_id,
    basal=verified_basal_receipt,
    basal_realization_id=selected_basal_id,
)
design.write("design-bundle")
```

The operation verifies both receipts and compiles only the selected exact
molecular components. It does not rank alternatives. Search-result identity,
execution bounds, relaxation radius, and enzyme chronology remain construction
evidence rather than design identity. PCR-bearing endpoints require basal
selection. Direct single-stranded design compilation is deferred because this
operation has no independent exact-basal input and does not invent one.

Compile only that foldback-basal pair against the matching design when the
scientific question concerns the selected route rather than the complete local
Cartesian product:

```python
selected = construction.compile_construction_from_local_realizations(
    "construction.yaml",
    design_bundle_path="design-bundle",
    foldback=verified_foldback_receipt,
    foldback_realization_id=selected_foldback_id,
    basal=verified_basal_receipt,
    basal_realization_id=selected_basal_id,
)
```

Both receipts must derive from the exact local requests in the construction
source. The returned receipt uses the ordinary portable construction authority
and reports one nominal and one examined combination. HOP evaluates the pair;
it does not select it or reinterpret its deterministic ordinal as a score.

## Prepare the two authorities

Construction compilation requires two independent inputs:

1. a regular, nonsymlink JSON or YAML file with schema
   `hop.construction-source/v4`; and
2. a verified design-bundle directory produced by HOP.

The construction source declares the foldback request, an optional basal
request, the requested endpoint, how the source ssDNA and its preparation
primers are resolved, endpoint-dependent auxiliary materials, whole-route
constraints, and finite enumeration bounds. Its shape is:

```yaml
schema: hop.construction-source/v4
foldback: <hop.local-neighborhood-request/v3 mapping>
basal: <hop.local-neighborhood-request/v3 mapping or null>
composition:
  endpoint: ssdna_hairpin | hairpin_pcr_duplex | clone_ready_duplex
  materialization:
    source_preparation:
      source_ssdna: <derive or fixed source-ssDNA policy>
      forward_primer: <derive, constrain, or fixed source-primer policy>
      reverse_primer: <derive, constrain, or fixed source-primer policy>
    adapter: <exact endpoint adapter or null>
    hairpin_pcr_forward_primer: <exact endpoint primer or null>
    hairpin_pcr_reverse_primer: <exact endpoint primer or null>
  release: <exact oriented Type IIS endpoint release or null>
  whole_route_constraints: <intrinsic route constraints>
  enumeration:
    max_combinations: <positive integer>
    max_realizations: <positive integer>
```

Angle-bracketed values above describe required typed mappings; they are not
literal values to copy. Generate those mappings from the strict construction
models used by the owning study, serialize their external field names, and keep
the design bundle outside the source document. YAML anchors, aliases, and merge
keys are rejected. The source cannot author design, result, realization,
projection, output-path, timestamp, or environment identities.

Source preparation is an explicit modeled relation:

```text
source ssDNA + two source-preparation primers
    -> exact copied source duplex
```

The source ssDNA is the first external route material. The copied duplex is a
derived route state, not another material for the caller to provide. Source
primer annealing is resolved outside the payload and its terminal chemistry is
validated before the copied duplex can seed downstream construction. The
`hairpin_pcr_forward_primer` and `hairpin_pcr_reverse_primer` fields are
different materials: they are required only for PCR-bearing endpoints after
the ssDNA hairpin has formed.

Endpoint obligations fail closed:

| Endpoint | Source preparation | Basal request | Endpoint adapter and primers | Type IIS end generation |
| --- | --- | --- | --- | --- |
| `ssdna_hairpin` | required | omitted | omitted | omitted |
| `hairpin_pcr_duplex` | required | required | required | omitted |
| `clone_ready_duplex` | required | required PCR-intermediate authority | required | required by the endpoint release request |

The foldback and basal requests, when both are present, must describe the same
payload space. The exact payload in the verified design must belong to that
space; compilation never repairs or substitutes a payload base.

The installed documentation smoke uses four checked-in sources:

- `examples/construction-exact.yaml` is an exact direct foldback request;
- `examples/construction-infeasible.yaml` exhausts an incompatible request;
- `examples/construction-relaxed.yaml` reaches a realization in the first
  allowed relaxation shell; and
- `examples/construction-composed-pcr.yaml` combines verified foldback and
  basal neighborhoods into a PCR-bearing complete route.

They share `examples/construction-exact-design.yaml` only as a deterministic
documentation fixture. They are not paper inputs, enzyme recommendations, or
experimental evidence.

## Compile and write the authority

```python
from pathlib import Path

import hop_design.construction as construction

compilation = construction.compile_construction(
    "construction.yaml",
    design_bundle_path="design-bundle",
)

print(compilation.status)
print(compilation.endpoint)
print(compilation.valid_realizations)
print(compilation.examined_combinations, compilation.nominal_combinations)

bundle_path = compilation.write(Path("construction-bundle"))
```

The returned `ConstructionCompilation` is an opaque receipt. It exposes scalar
identity and exact accounting, not mutable result or manifest models. Writing
is atomic and create-only: an existing destination is rejected, and a failed
write leaves no committed bundle.

`status` has exact discovery meaning:

- `complete`: the declared search was exhausted and at least one complete
  realization was accepted;
- `infeasible`: the declared search was exhausted and no complete realization
  was accepted;
- `truncated`: an explicit local or composition bound prevented a definitive
  conclusion.

Truncation is not infeasibility, and canonical order is not a score.

## Reopen and project

```python
verified = construction.load_verified_construction_bundle(bundle_path)

summary = construction.project_complete_construction_summary(verified)
summary.write("construction-summary")


def write_selected_trajectory(*, realization_id: str) -> None:
    if realization_id not in verified.materialized_realization_ids:
        raise ValueError("Select an accepted materialized realization identity.")
    trajectory = construction.project_construction_trajectory(
        verified,
        materialized_realization_id=realization_id,
    )
    trajectory.write("construction-trajectory")
```

The summary preserves every examined composition disposition and lossless
grouping. A trajectory requires an explicitly supplied accepted realization
identity; HOP does not choose an exemplar. Foldback and basal feasibility plus
their relaxation frontiers are available through the corresponding projection
operations. A basal projection rejects a construction with no basal authority.

Each `ConstructionProjection` contains canonical JSON, deterministic SVG, and
CSV when the projection defines a table. Projection directories are also
atomic and create-only. They are reversible, non-authoritative views over the
verified construction result; they do not replace the bundle.

## Claim boundary

Successful compilation establishes deterministic local discovery,
whole-route composition, endpoint materialization, design-encoding agreement,
and portable replay under the declared molecular model. It does not establish
laboratory construction, destination compatibility, QC, activity, yield,
empirical enzyme performance, or an optimized route.

See the [construction bundle layout](../reference/construction-bundle-layout.md),
[Python API](../reference/python-api.md#payload-centered-construction), and
[provenance contract](../provenance/overview.md).
