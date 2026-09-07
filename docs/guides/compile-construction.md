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

## Checkpoint independent local queries

For a finite collection of strict local-neighborhood requests, use the public
batch operation. Each request retains its own geometry, enzyme domain, search
limits, status, canonical result bytes, and realization identities.

```python
import hop_design.construction as construction

sources = ["foldback-top.yaml", "foldback-bottom.yaml"]
partial = construction.discover_local_neighborhoods(
    sources,
    "local-results",
    max_new_requests=1,
)
finished = construction.discover_local_neighborhoods(
    sources,
    "local-results",
    resume=True,
)
for result in finished.iter_results():
    print(result.completion, result.feasibility, result.result_id)
```

The first call is create-only. Resume requires the same normalized ordered
requests, package-content identity, and recorded Python/dependency versions.
Saved results pass full molecular replay before more queries execute. A changed
producer or corrupted authority fails; it is not silently recomputed or replaced.
Move the whole directory to transfer it. Source filenames and destination paths
are not part of its identity.

The directory contains a normalized `plan.json`, compressed canonical results
under `batches/`, and `complete.json` only after every request has returned.
Each immutable batch contains `results.jsonl.gz` and `inventory.json`. Batch
size may change on resume without rewriting completed files or changing result
identity. A `.pending-` directory left by a killed process is unpublished staging,
not an authority; resumption leaves it untouched and executes the unfinished
queries again.

Limits are 4,096 requests, 1–256 requests per write batch, a 64-MiB normalized
plan, and 64 MiB of decompressed canonical results per batch. A batch flushes
at either its byte or request limit. Each local request still uses the existing
bounded in-memory discovery engine. Checkpointing occurs **between requests**,
not inside one large search. Resumption avoids rediscovering unfinished work
from the beginning of the collection, but replay of saved results still costs
computation. Concurrent writers must use separate destinations; publication
refuses to overwrite another writer's batch.

`finished` means every request returned, including requests that were truncated
or stopped at a quota. It is not a combined molecular completeness claim.
Repeated or overlapping requests are not deduplicated and their realization
counts must not be summed as unique molecules without a separate comparison.

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
execution bounds, retained-overhead coverage, and enzyme chronology remain construction
evidence rather than design identity. PCR-bearing endpoints require basal
selection. Direct single-stranded design compilation is deferred because this
operation has no independent exact-basal input and does not invent one.

Compile only the endpoint-required local realizations against the matching
design when the scientific question concerns an explicit route rather than the
complete local Cartesian product:

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

For a direct `ssdna_hairpin`, omit `basal` and `basal_realization_id`. For a
PCR-bearing endpoint, both basal arguments are required. Every receipt must
derive from the exact local request in the construction source. The returned
receipt uses the ordinary portable construction authority and reports one
nominal and one examined combination. HOP evaluates the selection; it does not
choose it or reinterpret its deterministic ordinal as a score.

One replay-verified source partition may be bound to either endpoint form:

```python
selected = construction.compile_construction_from_local_realizations(
    "construction.yaml",
    design_bundle_path="design-bundle",
    foldback=verified_foldback_receipt,
    foldback_realization_id=selected_foldback_id,
    source_partition=verified_partition_receipt,
    source_partition_realization_id=selected_partition_id,
)
```

The selected partition must describe the same prepared source duplex, use the
same characterized enzyme definitions, and replay the route's concurrent nicks,
denatured fragments, inclusive selection, and required survivors. A selected
member remains exact even when its parent partition search was truncated. Once
selected, that partition is consumed and sealed by complete-route replay; a
caller does not need to restate its cuts, fragments, or survivor relation.

## Prepare the two authorities

Construction compilation requires two independent inputs:

1. a regular, nonsymlink JSON or YAML file with schema
   `hop.construction-source/v6`; and
2. a verified design-bundle directory produced by HOP.

The construction source declares the foldback request, an optional basal
request, the requested endpoint, how the source ssDNA and its preparation
primers are resolved, endpoint-dependent auxiliary materials, whole-route
constraints, and finite enumeration bounds. Its shape is:

```yaml
schema: hop.construction-source/v6
foldback: <hop.local-neighborhood-request/v5 mapping>
basal: <hop.local-neighborhood-request/v5 mapping or null>
composition:
  endpoint: ssdna_hairpin | hairpin_pcr_duplex | clone_ready_duplex
  materialization:
    source_preparation:
      source_ssdna: <derive or fixed source-ssDNA policy>
      forward_primer: <derive, constrain, or fixed source-primer policy>
      reverse_primer: <derive, constrain, or fixed source-primer policy>
    endpoint_auxiliaries:
      adapter: <derive, constrain, or fixed adapter policy>
      forward_primer: <derive, constrain, or fixed endpoint-primer policy>
      reverse_primer: <derive, constrain, or fixed endpoint-primer policy>
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
validated before the copied duplex can seed downstream construction.

`endpoint_auxiliaries` is separate and is required only for PCR-bearing
endpoints after the ssDNA hairpin has formed. Each nested policy has one exact
meaning:

- `derive`: HOP derives the adapter from the selected basal pairing segment or
  a primer from the exact PCR template at one caller-authored annealing length;
- `constrain`: HOP appends one explicit caller-supplied adapter or primer handle
  and chooses the shortest valid primer annealing length inside the declared
  inclusive range; and
- `fixed`: the caller supplies one exact material and HOP verifies its sequence,
  annealing relation, and terminal chemistry.

The adapter always preserves the selected basal pairing segment. A derived or
constrained forward primer binds within the invariant source-side construction
prefix, and its reverse counterpart binds within the adapter. Neither may
anneal across the payload. HOP performs no Tm, yield, or empirical ranking, and
does not generate a reusable handle that the caller did not specify.

Basal discovery is deliberately local. It establishes the payload-proximal
nick, the exact proximal adapter pairs, any position-level source and adapter
base domains, the minimum full annealing extent, mismatch warnings, retained
overhead, and—for a clone-ready endpoint—the Type IIS action required later.
The future release is an obligation, not a sticky end asserted in the current
adapter state. Basal discovery does not invent the remaining annealing bases,
finalize the complete adapter, or claim a PCR product. Complete composition
must satisfy those obligations against the realized source scaffold and exact
endpoint materials.

Representative policy shapes are:

```yaml
endpoint_auxiliaries:
  adapter:
    mode: constrain
    three_prime_handle_sequence: <explicit reusable DNA handle>
  forward_primer:
    mode: derive
    annealing_length_nt: <positive integer>
    five_prime_end: hydroxyl
  reverse_primer:
    mode: constrain
    min_annealing_length_nt: <positive integer>
    max_annealing_length_nt: <positive integer>
    five_prime_handle_sequence: <explicit DNA handle or empty string>
    five_prime_end: hydroxyl
```

A constrained primer deterministically uses its minimum declared annealing
length when that length fits the invariant binding region. A fixed adapter uses
`material`; a fixed endpoint primer uses `primer`. Those mappings use the exact
construction-material and PCR-primer contracts rather than free-form sequence
strings. A direct `ssdna_hairpin` omits `endpoint_auxiliaries` entirely.

Endpoint obligations fail closed:

| Endpoint | Source preparation | Basal request | Endpoint adapter and primers | Type IIS end generation |
| --- | --- | --- | --- | --- |
| `ssdna_hairpin` | required | omitted | omitted | omitted |
| `hairpin_pcr_duplex` | required | required | required | omitted |
| `clone_ready_duplex` | required | required local boundary authority | required | required by the endpoint release request |

The foldback and basal requests, when both are present, must describe the same
payload space. The exact payload in the verified design must belong to that
space; compilation never repairs or substitutes a payload base.

The installed documentation smoke uses four checked-in sources:

- `examples/construction-exact.yaml` is an exact direct foldback request;
- `examples/construction-infeasible.yaml` exhausts an incompatible request;
- `examples/construction-expanded-domain.yaml` includes more than one declared
  foldback geometry and reports their absolute retained-overhead levels; and
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
their retained-overhead frontiers are available through the corresponding projection
operations. A basal projection rejects a construction with no basal authority.

The same verified authority is navigable without importing Python:

```bash
hop-design construction summary construction-bundle
hop-design construction list construction-bundle --group-by geometry
hop-design construction inspect construction-bundle REALIZATION_ID \
  --out construction-trajectory
hop-design construction select construction-bundle REALIZATION_ID \
  --out selected-route.json
hop-design construction inspect construction-bundle \
  --selection selected-route.json
```

Listing defaults to accepted routes grouped by achieved geometry in canonical
replay order. Explicit filters and sorts do not change the result authority.
`--limit` bounds displayed rows only; verified search status, accounting, and
membership remain intact. Canonical ordinal is not a rank. A selection is a
create-only reference bound to the verified source result and one accepted
materialized realization; it neither removes alternatives nor endorses a route.
See the [CLI reference](../reference/cli.md#construction-navigation) for the
complete option contract.

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
