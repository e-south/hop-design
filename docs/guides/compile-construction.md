---
doc_id: hop-compile-construction-guide
title: Compile a payload-centered construction
intent: Search peripheral junctions, compile a construction, and inspect its required materials and molecular steps.
audience:
  - Python users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-10-06
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

This lower-level search and compilation path uses `hop_design.construction`.
The CLI also supports product-first discovery and comparison execution through
the linked user guides, and inspects the saved authorities shown here.
This guide describes the source checkout, including
unreleased features; use [tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a8)
with the published wheel.

For product choices, sticky-end orientation, reuse permissions and a runnable
hairpin and released-insert example, start with the [construction journey](design-a-construction.md).

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

To interpret a collection of local searches, see the
[bounded-neighborhood teaching example](../reference/view-contracts.md#teaching-example-two-bounded-local-neighborhoods).
It separates search coordinates, physical measurements, local existence, and
exhaustive alternative coverage before choosing an exemplar.

Once you have compiled a complete construction bundle, list and inspect it:

```bash
uv run hop-design construction list CONSTRUCTION_BUNDLE
uv run hop-design construction inspect CONSTRUCTION_BUNDLE --ordinal ROUTE_NUMBER
```

Use the route number shown by the listing, not its position after sorting.
Inspection leads with the achieved product and paired flank distances, then
exact materials and preparation conditions. It shows whether source-fragment
removal is specified and reports the
actual released ends, each read 5′→3′ on its protruding strand. Compare both
ends with any required interface; a sequence match alone is not a check of
destination compatibility or laboratory performance.
`--full-ids` reveals complete identities and group keys. For a durable reference,
`construction select CONSTRUCTION_BUNDLE --ordinal ROUTE_NUMBER --out selected.json`
stores the full result and realization identities, not the display number.

For complete construction, [define the inputs](#prepare-the-two-authorities),
[select local alternatives](#derive-a-design-from-selected-local-alternatives),
then [compile](#compile-and-write-the-authority) and
[inspect the result](#reopen-and-project). Checkpointing below is optional for
collections of independent queries; it is not required to compile one route.

## Compare completed choices

After changing a constraint and compiling another result, compare the selected
routes before deciding which materials to use:

```bash
uv run hop-design construction compare LEFT_BUNDLE RIGHT_BUNDLE \
  --left-ordinal LEFT_ROUTE_NUMBER --right-ordinal RIGHT_ROUTE_NUMBER
```

Use numbers from `construction list` for each respective bundle. The two bundle
paths may be the same. The report starts with changed and preserved external
material roles, comparing sequence plus terminal chemistry. This is a comparison
with an explicit reference; a single handoff has no change baseline.
The Markdown report compares required oligos and end
chemistry, retained encoding sequence, processing order, fragment-removal
information, PCR strand lengths, and actual endpoint strands and cohesive ends. Full result and
realization identities appear at the end for traceability. Neither input is
changed, and no search is rerun.

For loaded receipts and explicitly selected realization identities, the Python
equivalent is:

```python
report = construction.compare_constructions(
    left_receipt,
    right_receipt,
    left_realization_id=left_id,
    right_realization_id=right_id,
)
print(report)
```

“Same” applies to the displayed property, not to every molecular interaction or
experimental performance. Processing-order equality does not establish equal
cut or binding coordinates; inspect either route for those details. A selected
route can be resolved even when its originating search is truncated. The
reported coverage belongs to the composition result; it does not describe a
separate upstream scaffold-generation search. Comparison introduces no
preference score.

## Derive a design from selected local alternatives

[Select local junctions](select-construction-junctions.md) to bind verified foldback,
basal and optional source-partition receipts to one explicit design. This is the
advanced selection path; product-first discovery performs complete continuation
before asking for a preparation choice.

## Prepare the two authorities

Compilation takes a strict construction-source file and a separately verified
design bundle. The [source and material-policy reference](../reference/construction-source.md)
defines the exact schema, endpoint obligations, source completion, adapter
pairing, primers and release constraints. Keep the design bundle outside the
source document; HOP verifies their agreement during compilation.

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
    trajectory.write(
        "construction-trajectory",
        selection_reason="Uses the required enzymes and endpoint.",
    )
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
  --out construction-trajectory --reason "Uses the required enzymes and endpoint."
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

A selected trajectory also exposes `trajectory.inspection_text`, the concise
text used by `construction inspect`. Other projection kinds reject this property.
The inspection and oligo exports share one reader for external material uses;
role counts and distinct sequence-and-chemistry counts remain separate. CLI
adapters consume this text without reconstructing material policy from JSON.

For a released duplex, ask where a requested end comes from:

```bash
hop-design construction inspect construction-bundle \
  --selection selected-route.json --end right --base-index 0
```

The equivalent API call is `trajectory.inspect_end("right", base_index=0)`;
omit the index to inspect every base in that end. Zero means the first base in
the end's own 5′→3′ word, regardless of where the strand appears on a page.
Rows bind that base to its recorded material role, coordinate and base, with
material-use identity and chemistry below. Identical oligos can have distinct
roles; a prepared source duplex is a modeled material, not an additional order.
Release cuts use the pre-release primary-strand coordinate axis. Full upstream
source-preparation lineage and earlier contacts remain in `projection.json`;
this focused view does not yet traverse them or propose a repair.

For a selected trajectory, start with `report.md`. It summarizes the payload,
endpoint, caller-stated selection reason, retained sequence, enzymes, molecular
steps, and unresolved preparation conditions. `oligos.csv` lists each distinct
external oligo with its roles, sequence, length, and required end chemistry;
The route list counts distinct auxiliary oligos, excluding the source oligo;
`--sort auxiliary-count` uses that same count. Reusing an identical sequence
with identical terminal chemistry in several roles does not add another oligo.
`oligos.fasta` contains the same sequences. Keep the CSV with the FASTA because
FASTA does not encode modifications. Produced duplexes are not extra orders.
The exact `projection.json` and `projection.svg` remain available for inspection.

The optional reason is explanatory text, not a verified preference or a score;
it does not change the result or selection identity. Without it, the report says
no preference was supplied. A blank reason is rejected. This handoff specifies
sequences and operations, not reaction conditions, yields, or experimental success.

## Checkpoint independent local queries

[Checkpoint a collection](checkpoint-local-queries.md) when running many independent
local requests. This optional path preserves completed queries and verifies their
producer on resumption; it does not resume within a partly evaluated local query.

## Claim boundary

Successful compilation establishes deterministic local discovery,
whole-route composition, endpoint materialization, design-encoding agreement,
and portable replay under the declared molecular model. It does not establish
laboratory construction, destination compatibility, QC, activity, yield,
empirical enzyme performance, or an optimized route.

See the [construction bundle layout](../reference/construction-bundle-layout.md),
[Python API](../reference/python-api.md#payload-centered-construction), and
[provenance contract](../provenance/overview.md).

The independently requested `adapter_ligated_hairpin` endpoint requires basal
authority and `materialization.adapter_ligation`, and excludes downstream PCR
auxiliaries and release. See [the product-first comparison workflow](specify-a-comparison.md#obtain-a-hairpin-itself).
