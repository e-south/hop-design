---
doc_id: hop-compile-construction-guide
title: Compile a payload-centered construction
intent: Search peripheral junctions, compile a construction, and inspect its required materials and molecular steps.
audience:
  - Python users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-09-08
doc_type: how-to
journey:
  - discover
  - verify
---

# Compile a payload-centered construction

Keep the payload fixed while checking whether selected foldback and basal
junctions can be completed into the requested hairpin or duplex. A construction
result includes required material sequences, processing steps, and reasons
why a proposed combination cannot satisfy the request.

Search and compilation use the Python API, `hop_design.construction`. The CLI
inspects saved results. This guide describes the source checkout, including
unreleased features; use [tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a8)
with the published wheel.

## Search a realistic junction

From the repository root, with Python 3.12–3.14 and `uv` installed:

```bash
uv sync --locked
uv run python examples/basal-junction/search.py --out build/basal-junction
```

The [worked example](../../examples/basal-junction/README.md) keeps a public
34-bp loxP substrate unchanged while searching Nt.BsmAI/BbsI placements and
all four-base cohesive ends. It writes exact local results and an SVG/CSV
matrix. An existing output directory is refused. This is local discovery,
not a completed hairpin route: adapter completion, primers, and the rest of
the source must still satisfy the requested endpoint.

Once you have compiled a complete construction bundle, list and inspect it:

```bash
uv run hop-design construction list CONSTRUCTION_BUNDLE
uv run hop-design construction inspect CONSTRUCTION_BUNDLE --ordinal ROUTE_NUMBER
```

Use the route number shown by the listing, not its position after sorting.
`--full-ids` reveals complete identities and group keys. For a durable reference,
`construction select CONSTRUCTION_BUNDLE --ordinal ROUTE_NUMBER --out selected.json`
stores the full result and realization identities, not the display number.

For complete construction, [define the inputs](#prepare-the-two-authorities),
[select local alternatives](#derive-a-design-from-selected-local-alternatives),
then [compile](#compile-and-write-the-authority) and
[inspect the result](#reopen-and-project). Checkpointing below is optional for
collections of independent queries; it is not required to compile one route.

## Derive a design from selected local alternatives

First compare the molecular choices that meet your requirements. Retained
sequence, noncanonical adapter pairs, and required enzymes are separate
properties, not a combined quality score.

Required enzymes include both immediate nicking and declared future release
capabilities. A local witness is not yet a usable whole route: the current
linear PCR-bearing route requires the basal nick on the source-return strand
(bottom in payload-forward coordinates). Its full adapter pairing, primer
bindings, and eventual release boundaries must also be satisfiable. If a
selected witness fails completion, inspect that reason before choosing another;
the failure does not invalidate every alternative in the local search.

```python
choices = construction.list_local_realizations(
    verified_basal_receipt,
    cohesive_end="CTCA",  # An exact end required by this example, not a default.
    max_noncanonical_pairs=0,
    sort_by=("retained_overhead_nt", "enzyme_count"),
)
for choice in choices:
    print(
        choice.realization_id,
        choice.geometry.nick_offset_nt,
        choice.retained_overhead_nt,
        choice.pairing_classes,
        choice.annealing_completion_nt,
    )
```

Choose a row for its molecular properties and retain its `realization_id` with
the originating receipt. The same listing works for foldback receipts; their
geometry exposes loop, arm, and junction offset. Basal-only filters are rejected
for foldbacks. Sorts are ascending in the stated priority and preserve ties in
source order. Omitting `sort_by` preserves the recorded order. No alternatives
are removed from the search result.

These are recorded witnesses. Filtering an existence search does not prove
that all unenumerated sequences fail your additional preferences. Check the
receipt's `completion`, `feasibility`, and original search scope before claiming
a minimum. A local choice still needs complete source, adapter, primer, and
processing checks; `annealing_completion_nt` names an outstanding local
adapter requirement, not a physical success estimate.

Pass the explicitly chosen family realization ids to design compilation:

```python
import hop_design.construction as construction

design = construction.compile_design_from_local_realizations(
    design_id="selected-route-design",
    payload_sequence="ATAACTTCGTATAGCATACATTATACGAAGTTAT",
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
member remains exact even when its parent partition search was truncated.
For PCR-bearing endpoints, HOP includes every selected cleanup nick before
checking actionable sites. The cleanup must contain the local junction nicks
and leave exactly the strands required for foldback and adapter joining.
The exported route includes the fragment sequences, end chemistry, and source
coordinates; no caller-side reconstruction is needed. A different source or
survivor set rejects that combination.

This composition supports one concurrent nick-only stage. Direct hairpin
endpoints can bind a matching partition but do not add cleanup operations;
multi-stage cleavage requires a separately supported route model.

### Check removal for a selected source

A modeled endpoint without a bound partition does not establish how unwanted
source fragments will be removed. After selecting a construction, ask HOP to
search removal programs on its exact prepared source:

```python
partition = construction.discover_construction_source_partition(
    selected,
    "removal-policy.yaml",
    materialized_realization_id=selected_route_id,
)
partition.write("source-removal")
```

`selected_route_id` must name an accepted realization in `selected`. HOP derives
the duplex sequence, terminal chemistry, payload coordinates, and required
surviving strands; do not copy those facts into the policy. The policy shape is:

```yaml
schema: hop.source-partition-policy/v1
enzyme_provisioning: <characterized catalog and provisioned strand-exposure enzymes>
fragment_policy:
  preferred_maximum_nt: <largest unwanted fragment permitted without relaxation>
  absolute_maximum_nt: <largest unwanted fragment permitted at all>
max_enzymes_per_program: <positive integer>
enumeration:
  max_search_nodes: <positive integer>
  max_realizations: <positive integer>
```

The angle-bracketed entries are caller choices, not runnable values or defaults.
Set both maxima equal for one fixed rule. These are exact sequence-length
predicates, not predictions of physical cleanup recovery.

Inspect the returned alternatives, explicitly select a partition realization,
and pass it to `compile_construction_from_local_realizations` as shown above.
That composition checks the entire route with the selected processing program.
An infeasible removal search leaves the original construction unchanged; a
truncated search does not establish that no removal program exists. HOP does
not silently add source sequence or relax the length rule.

## Prepare the two authorities

Construction compilation requires two independent inputs:

1. a regular, nonsymlink JSON or YAML file with schema
   `hop.construction-source/v7`; and
2. a verified design-bundle directory produced by HOP.

The construction source declares the foldback request, an optional basal
request, the requested endpoint, how the source ssDNA and its preparation
primers are resolved, endpoint-dependent auxiliary materials, whole-route
constraints, and finite enumeration bounds. Its shape is:

```yaml
schema: hop.construction-source/v7
foldback: <hop.local-neighborhood-request/v6 mapping>
basal: <hop.local-neighborhood-request/v6 mapping or null>
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

Angle-bracketed values above describe required mappings; they are not literal
values to copy. Start from a complete example source under `examples/` and
consult the [schema reference](../reference/schemas.md) for supported document types and limits.
The public API reads the source file directly; no study package or internal
model import is required. Keep the design bundle outside the source document.
YAML anchors, aliases, and merge
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

To limit imperfect pairing, set `geometry_domain.max_noncanonical_pairs` in a
basal request. It counts G:T/T:G wobble and other mismatches across the declared
proximal `pairing_constraints`. For example, `2` allows at most two noncanonical
pairs while the ligation-adjacent position still requires a match. Omission
applies no aggregate cap. This caller-selected bound is not a prediction of
ligation efficiency; it does not relax recognition-site fidelity or apply to
distal adapter completion. At displaced nicks the proximal window and final
cohesive-end footprint need not coincide.

Basal discovery is deliberately local. It establishes the payload-proximal
nick, the exact proximal adapter pairs, any position-level source and adapter
base domains, the minimum full annealing extent, mismatch warnings, retained
overhead, and—for a clone-ready endpoint—the Type IIS action required later.
The future release is an obligation, not a sticky end asserted in the current
adapter state. Its `cohesive_end_sequence` may pin exact DNA or declare an
[IUPAC design domain](../discovery/overview.md#search-a-basal-cohesive-end-or-pin-it-to-a-destination).
Basal discovery does not invent the remaining annealing bases,
finalize the complete adapter, or claim a PCR product. Complete composition
must satisfy those obligations against the realized source scaffold and exact
endpoint materials.

Pairing position zero is the adapter base beside the nick, not the base beside
the payload. A displaced nick leaves an intervening source-derived segment;
those positions do not count toward adapter annealing. The local PCR accounting
view includes that segment plus the constrained adapter positions. It does not
measure the length of the final restriction-released insert or the complete
adapter. Later cohesive-end obligations include any source-derived bases before
the adapter begins; only overlapping adapter positions carry that future role.

PCR composition retains the source-derived bases between the basal nick and
the payload, together with their original complementary partners. The adapter
joins at the nick; it does not replace those retained partners. The resulting
design includes this intervening duplex segment, and the route records its
pairing and source lineage through copying. A locally feasible nick still needs
compatible source primers, a complete adapter, and valid processing states.

For PCR-bearing composition, the adapter keeps the locally selected proximal
pairs, including any permitted mismatches. Undeclared distal positions pair
canonically with the adjacent invariant source flank. All adapter modes accept
`distal_pairing_constraints` using the same position, pair-class, and base-domain
fields as the local basal constraints. Positions are zero-based from the
adapter's ligation end, strictly ascending, and must lie beyond the local
segment but inside the required annealing span. For example:

```yaml
adapter:
  mode: constrain
  three_prime_handle_sequence: GATCTG
  distal_pairing_constraints:
    - position_from_ligation: 6
      allowed_class: wobble
```

This requires G:T or T:G at position 6; it is not permission to change the
source base. Derivation must resolve one exact adapter base per position.
An ambiguous choice raises an input error: narrow `allowed_adapter_bases` or
provide a fixed adapter. No arbitrary mismatch is selected. A fixed adapter
must satisfy the declared constraints and remain canonical at undeclared
distal positions. HOP appends a requested handle after the pairing segment;
a fixed material can instead contain overlapping pairing and primer-binding
spans. The trajectory records every literal pair, including permitted wobbles
and mismatches, without predicting annealing or ligation performance.

If the selected source lacks enough upstream sequence, that exact composition
is rejected. For PCR-bearing endpoints, a `fixed` source may supply a longer
upstream flank while preserving the entire local basal sequence, payload, and
foldback source. HOP maps both junctions into that exact source, derives primer
binding and full adapter annealing there, and checks additional actionable
enzyme sites. This applies in either foldback-source orientation; it does not
alter a local realization or count the added flank as local junction overhead.

Fixed-source replay evaluates that supplied completion only. To search upstream
sequence for a PCR-bearing endpoint, use a constrained source policy. This
fragment belongs under `composition.materialization.source_preparation`:

```yaml
source_ssdna:
  mode: constrain
  upstream_sequence_spec: MAAAGTCTGAC
  five_prime_end: hydroxyl
  three_prime_end: hydroxyl
```

The pattern precedes the unchanged basal source flank in the payload-forward
frame. HOP derives the physical source orientation from the foldback realization;
it does not ask the caller to reverse the pattern for a reverse-oriented foldback.
This synthetic pattern declares two upstream assignments, not two payloads.
Each assignment is checked for source and endpoint primer binding, complete
adapter pairing, and actionable enzyme sites. The resulting source material is
recorded as constrained, not caller-fixed.

Composition traverses foldback, basal, then upstream assignments in deterministic
A/C/G/T order. Its nominal denominator includes all three domains. The existing
`max_combinations` and `max_realizations` bounds stop this traversal; a stopped
prefix is truncated even if every examined sequence failed. Accepted alternatives
remain distinct within geometry groups. Summary JSON and CSV bind each examined
assignment through `source_context_sequence`.

The pattern supplies one finite, fixed-length domain. HOP does not choose an
unbounded extension length, generate a reusable handle without constraints, or
design cleanup-nick tiling through this policy. A selected partition still
certifies its exact supplied source. No fixed primer is rewritten, no annealing
length is silently reduced, and no melting temperature or recovery is predicted.

The future release requirement records `recognition_material`:

- `source_duplex` (default): the Type IIS recognition sequence must coexist
  with the nickase recognition sequence in the source. Both motifs constrain
  the same bases before enumeration. The source site maps to the requested
  endpoint through copying; its presence does not apply Type IIS cleavage in
  the earlier nicking stage.
- `endpoint_material`: a later material, such as a PCR-primer tail, supplies
  the recognition sequence. Local discovery establishes the requested cut
  geometry and proximal end-sequence constraints, not source-site coexistence.
  Complete endpoint evaluation must still find and verify the actual sites.

These choices define different sequence-design questions and enter request
and result identity. A source-encoded request cannot be satisfied by silently
introducing its recognition site through a primer instead.

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

## Claim boundary

Successful compilation establishes deterministic local discovery,
whole-route composition, endpoint materialization, design-encoding agreement,
and portable replay under the declared molecular model. It does not establish
laboratory construction, destination compatibility, QC, activity, yield,
empirical enzyme performance, or an optimized route.

See the [construction bundle layout](../reference/construction-bundle-layout.md),
[Python API](../reference/python-api.md#payload-centered-construction), and
[provenance contract](../provenance/overview.md).
