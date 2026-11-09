# From ssDNA to a hairpin and released insert

HOP helps you specify a source ssDNA, its conversion into a hairpin, and, when
requested, copying and cleavage into a duplex insert with defined sticky ends.
The deliverable is a checked molecular route with exact oligos and expected
products. Compatibility with receiving DNA and performance in the laboratory
require separate evidence.

This journey uses the current source checkout. [Install HOP](install.md) first;
use tagged documentation with a released wheel. The construction workflow uses
Python for search and compilation and the CLI for inspection and selection.
The CLI and Python share one product-request translator; there is no graphical
request editor or automatic design wizard.

## 1. Describe the product you need

Author the payload once, 5′→3′. HOP derives its paired arm. Choose how far the
route should proceed:

| Desired product | Request endpoint | Additional obligations |
| --- | --- | --- |
| Single-stranded hairpin | `ssdna_hairpin` | Source preparation, cleavage, strand selection and foldback joining |
| Copied hairpin duplex | `hairpin_pcr_duplex` | Adapter completion and endpoint primer bindings |
| Released duplex with sticky ends | `clone_ready_duplex` | Declared cleavage agent and both exact oriented ends |

The last schema label describes a destination-neutral restriction product.
It does not establish that an insert can be cloned into a particular vector.
Only request stages you need; an earlier endpoint must not inherit unnecessary
primer or release requirements.

For a released insert, specify the left and right words separately, each
5′→3′ on its own protruding strand, together with 5′/3′ overhang polarity,
release-site orientation, and each paired end-to-payload distance. These are
exact requirements on **one final product**, not two independently selectable
local search hits. Do not reverse-complement an end simply to make the two
strings look aligned on a page.

## 2. State what can change

Author `hop.product-request/v1` with `stem_arm`, `endpoint`, and, for a released
insert, both `ends`. Each end includes its word, overhang polarity, recognition
orientation and `payload_end_offset_bp`. The checked-in
[public request](../../examples/complete-construction/product-request.json)
is a runnable starting point.

`foldback` and `basal` each group `geometry`, `enzymes` and `search` for that
local job. `enzyme_catalog` is shared; each job keeps its own explicit allowed,
forbidden and reserved enzymes and role restrictions. `materialization` retains
fixed/constrained/derived policies. `release.basal_projection` declares which
product end is projected onto which local recognition material. The translator
copies that end requirement; do not repeat `future_release` in basal geometry.

```bash
# Preview the product request and its permitted construction choices.
uv run --locked hop-design construction prepare examples/complete-construction/product-request.json --out build/prepared-request
```

This writes `intent.md`, the authored `request.json`, `construction.json`, and
local `foldback.json`/`basal.json` inputs. It performs strict translation only;
feasibility, actual products and material sequences remain unresolved. The
complete example below runs discovery and explicitly continues its single
budgeted witness. Editing one product field never silently edits a material or
contact permission to force success.

| Your decision | What HOP needs |
| --- | --- |
| Which sequence must survive unchanged? | Payload and its boundaries |
| Which source or oligos must be reused? | Exact fixed materials, including terminal chemistry |
| Which materials may be designed? | Explicit `derive` or `constrain` policies where supported |
| Which enzymes are available? | Characterized actions and provisioned roles |
| Which contacts may be noncanonical? | Position-specific pairing permissions |
| How much surrounding DNA is acceptable? | Local geometry and final end-to-payload offsets |
| How far should the search go? | Finite sequence/geometry domains and execution bounds |

`fixed` means keep the exact material; `constrain` allows completion within
stated restrictions; `derive` authorizes the supported derivation. Neither mode
means “pick something that works experimentally.” HOP does not silently change
end words, relax pairing rules, choose reusable handles, or rank primers by
unmodeled thermodynamics. The [construction guide](compile-construction.md)
contains the full input contract and supported material policies.

Two end words can be entered independently while their realization remains
coupled. In a route where final ends descend from an earlier paired interface,
canonical pairing can link their bases. Fixing the source may fix one side;
allowing adapter redesign cannot necessarily change that source-derived side.
Changing a permitted contact or material creates a new request to evaluate.

## 3. Obtain a preparation and adapt its ends

To execute your authored request directly, explicitly permit continuation of
the sole recorded witness from each bounded local search:

```bash
# Execute the request to obtain complete preparations.
uv run --locked hop-design construction execute examples/complete-construction/product-request.json --design-id my-preparation --continuation sole-witness --out build/my-preparation
```

The same Python operation is
`construction.execute_construction_request(path, design_id="my-preparation", continuation="sole-witness")`.
Write the returned receipt to a new directory. Read `report.md` and `summary.json`
first. An accepted preparation has `handoff/report.md` and `handoff/oligos.csv`.
No local witness, an unfinished search, and multiple choices are distinct
outcomes; the exact local results remain available. This policy continues one
recorded combination and does not rank alternatives or try a hidden relaxation.
The CLI returns success when it delivers an expected negative outcome; automation
must read `summary.json` for the molecular status. Malformed input returns an error.

The first report repeats the requested endpoint, oriented end words and paired
flank distances so an edited request stays visible beside its outcome.
`requested_ends` preserves the exact authored end requirements in the summary.
For a local stop, `rejection_reasons` and each family's `rejection_counts` expose
the recorded candidate failures. Counts describe the examined local candidates;
they do not prove that a particular edit is necessary or sufficient. A stopped
search remains unresolved even when every examined candidate was rejected.
Design IDs use 1–64 lowercase letters, digits, dots, underscores or hyphens and
start with a letter or digit. Invalid identities fail before discovery, including
for requests that would otherwise end in a local rejection.

For a direct hairpin request, omit downstream basal discovery, release and
endpoint auxiliaries, and explicitly declare `hairpin_basal_component` with
`left_arm` and `right_arm`, each 5′→3′ and equal in length. That exact terminal
component replaces the need for a prior insert design. Its sequence is an
authored constraint, not a parameter HOP chooses to make a request succeed.

Run the [complete public example](../../examples/complete-construction/README.md)
with the source version that ships it:

```bash
# Run the repository walkthrough from request to material handoff.
uv run --locked python examples/complete-construction/run.py --out build/public-journey
uv run --locked hop-design construction inspect build/public-journey/released/construction --ordinal 0 --end left
```

It uses the public 34-base loxP arm and characterized cleavage actions. Read
`build/public-journey/summary.json`, then the selected case's `handoff/report.md`,
`oligos.csv` and `projection.svg`. The example provides a separate hairpin
endpoint, a released insert with two authored ends, a fixed-source rejection,
and an explicit successful redesign. Each case retains its complete request
and verified construction authority. The producer content digest identifies
capabilities more precisely than the package version alone.

When more than one witness is recorded, inspect `construction local-choices`
and continue from the preserved request with explicit IDs:

```bash
# Continue the recorded request without changing its permissions.
uv run --locked hop-design construction continue build/my-preparation/inputs/request.json --design-id my-selected-preparation --foldback build/my-preparation/foldback/result.json --foldback-realization-id "$FOLDBACK_ID" --basal build/my-basal/result.json --basal-realization-id "$BASAL_ID" --out build/my-selected-preparation
```

The IDs above must come from the corresponding verified local results. If the
executor stopped before basal discovery, first run `construction discover-local`
on its saved `inputs/basal.json`; omit both basal arguments for a direct hairpin.
The original request supplies the terminal arms and material policies, so they
need not be retyped. Mismatched local requests or selections fail before output.
The lower-level compilation interfaces also remain available.

The hairpin preparation explicitly shortens a
primer to fit its non-payload context;
these primer lengths are not laboratory recommendations. Read the example's
coverage and experimental limits before adapting it.

Use a new output directory for each run. An ordinal identifies canonical replay
order within that exact result; it is not a recommendation. Persist a selected
route with `construction select ... --ordinal 0 --out selected-route.json`.
The [construction guide](compile-construction.md) covers the complete contracts.
The [local loxP survey](../../examples/basal-junction/README.md) answers a different
question: which ends have local support, without completing those routes.

## 4. Decide from the result

Inspect in this order: actual product and both oriented ends; payload retention;
required oligos and reuse; source-fragment removal; then detailed contacts,
primers, cuts, and search coverage. A complete route without a bound removal
program leaves that preparation condition unresolved.

To see the whole hairpin before reading the processing trace, use:

```bash
# Export a portrait of the selected construction.
uv run --locked hop-design construction portrait build/public-journey/hairpin/construction \
  --selection build/public-journey/hairpin/portrait/selection.json --out build/hairpin-choice
```

The drawing and `preparation/oligos.csv` refer to the same selected route.
For an insert-route portrait, the depicted joined hairpin is an intermediate;
the eventual release ends have their own stage label.

Optional `whole_route_constraints.hairpin_scaffold` requirements describe that
joined molecule. Equal boundaries request an exact value; otherwise both ends
of the range are inclusive:

```json
{
  "open_side_paired_positions": {"minimum": 17, "maximum": 17},
  "loop_side_paired_bp": {"minimum": 5, "maximum": 6},
  "loop_nt": {"minimum": 3, "maximum": 5}
}
```

Place this object under `whole_route_constraints.hairpin_scaffold` in the
product request. Omit a dimension to leave it unconstrained. HOP intersects
loop and loop-side requirements with the authored foldback domain, then checks
all specified dimensions on the complete joined state. The open-side count
includes the explicitly recorded noncanonical contacts, which remain labeled;
it is neither source length nor final released-end spacing. An out-of-range
candidate is rejected with requested and observed values and cannot be selected.
An empty intersection is a contradictory request, not molecular impossibility.

These are hard requirements, not display preferences. They do not enlarge the
search budget, discover every possible geometry, or choose a best preparation.
A failed sole-witness continuation does not rule out unexamined alternatives.

For a released insert, use `construction inspect ... --end left` or `--end right`
to connect an end word to its exact material origins and release cuts. Add
`--base-index 0` to inspect its first base, read 5′→3′ on that end's own strand.
The Python equivalent is `trajectory.inspect_end("right", base_index=0)`.
This question-focused view keeps full route detail available in the same
trajectory JSON. A PCR-only endpoint has no released ends and rejects this query.

| Result you see | Decision it supports |
| --- | --- |
| Accepted complete route | Inspect exact products/materials against the request; compare alternatives |
| Rejected combination | Read its recorded rejection reason before changing a constraint |
| Infeasible bounded search | No solution in that declared, exhausted problem; not proof against every route |
| Truncated search | Unexamined alternatives remain; an accepted witness may still be usable |
| Invalid input or corrupt bundle | Correct the input or restore the authority; do not treat it as biological infeasibility |

Use `construction compare` for two explicitly selected routes after changing a
requirement. Source reuse, required oligo count, input length, and retained
non-payload DNA are different properties. A shorter source is not necessarily
a smaller final insert. Enumeration order is not a recommendation.

The [mental model](../start/mental-model.md), [terms](../language/ontology.md),
and [search interpretation](../discovery/overview.md) explain these distinctions.

## Preview a coupled edit before searching

Use `construction prepare edited-request.json --compare-to original-request.json
--out build/edited-preview` to inspect both requested ends, the source contact
footprint, expanded pairing permissions and the authored minimum adapter
association. The report and `preview.json` show changes without predicting
feasibility. `request.json` preserves the exact edited intent.

For the supported single bottom-strand nick and right-end projection,
`basal.end_footprint_pairing` can be authored as:

```json
{"reference": "left_end_source_contacts", "proximal": "match", "within": "any"}
```

This explicitly permits any contact class in the left end's source footprint
and requires matching contacts toward ligation. Moving the end moves this
permission window through the same coordinate model used by construction.
Absolute `basal.geometry.pairing_constraints` may be empty when using this
rule, or contain additional base restrictions and outside-window constraints.
Overlapping permissions intersect: `any` with `match` requires a match, whereas
`wobble` with `match` is a conflict. The PCR-bearing route also requires a match
at the ligation-proximal position, including when a zero-gap end footprint
includes that position. The preview shows these effective permissions while
preserving the authored request. Disjoint classes still reject the request.
The noncanonical-pair cap and minimum annealing length stay explicit.
Recognition-site ownership may be `source_duplex` or `endpoint_material`:
it does not change where the left end overlaps source-adapter contacts.
The latter permission does not create a recognition site; the complete
construction must supply and verify it in the material being digested.
Other strand or nonunique nick frames reject this shorthand.
Literal coordinates remain available for every previously supported request.

The footprint is the overlap with adapter-contact positions, not the entire
receiving end. In a uniquely mapped source frame it can be empty: no end bases
then receive local noncanonical allowances, and the proximal contact still must
match. The complete release requirement retains the requested end word, polarity,
orientation and placement. A missing or nonunique source frame remains an
invalid relative pairing declaration; it is not an empty overlap.

An end footprint is a sequence origin, a permission is an allowed contact, and
an actual contact is an evaluated route property. After the preview, run the
edited request to learn which complete preparation, if any, it supports.

For a deliberate comparative set, use [Specify and retrieve scaffold families](compare-scaffold-families.md).
