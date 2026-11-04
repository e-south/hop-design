---
doc_id: hop-select-construction-junctions
title: Select local junctions for a complete construction
intent: Bind verified local receipts and optional fragment-removal evidence to one explicit construction.
audience: [Python users, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-06
doc_type: how-to
journey: [discover, compile]
---

# Select local junctions for a complete construction

Use this lower-level path when you need to choose exact local realization identities.
For complete options before selection, use [product-first discovery](discover-product-scaffolds.md).
The examples below assume verified local receipts from the [construction guide](compile-construction.md#search-a-realistic-junction).
Import the public facade with `import hop_design.construction as construction`.

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

For a PCR-bearing candidate rejected before an endpoint is materialized, select
its zero-based `ordinal` from the summary's combination dispositions instead:

```python
partition = construction.discover_construction_source_partition(
    examined,
    "removal-policy.yaml",
    combination_ordinal=chosen_ordinal,
)
```

Supply exactly one selection: an accepted realization ID or an examined
combination ordinal. HOP replays that candidate's source preparation and local
survivor requirements. This permits a cleanup program to account for additional
source nicks; it does not accept the rejected construction or waive adapter,
primer, payload, or endpoint requirements. Recompile with the selected partition
to check the complete route. Unexamined ordinals, incompatible basal strands,
and failed source preparation are rejected. The ordinal identifies a candidate
within this exact result, not a preference or a portable ranking.
