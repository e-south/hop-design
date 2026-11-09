---
doc_id: hop-guide-discover-designs
title: Discover complete designs around your stem
intent: Reach complete molecular choices, inspect a selected route, and retrieve its oligos without prescribing sticky ends.
audience: [users, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-11-09
doc_type: tutorial
journey: [discover, verify, integrate]
---

# Discover complete designs around your stem

Start with the stem you need and the product you want. HOP searches the permitted
construction flanks and returns complete preparations. Sticky ends are optional:
you can explore what is obtainable before deciding which ends suit your next step.

The commands below use the current source candidate. Follow the
[installation guide](install.md) to select that version.

After finding useful choices, [capture an atlas edition](share-atlas-edition.md)
to share their exact molecules, figures and materials without repeating search.

## Find your first choices

This example preserves one supplied stem arm and requests a released duplex insert:

```bash
uv run hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product released_insert \
  --out designs --format text
```

No end word or enzyme catalog is required. The versioned construction context
supplies visible method, geometry and material permissions. Read
`designs/intent/report.md` for the context and `designs/intent/request.json` for
its effective settings. To inspect those settings before searching, use the same
flags with `design resolve --out intent`.

The answer lists complete preparations, their loop and end features, and commands
for inspection or selection. No molecule is selected automatically. `--format text`
keeps this summary readable in a terminal or notebook. Use `--format json` for the
full machine-readable result, including parameter domains and coverage. Without
an explicit format, terminal output is text and piped output remains JSON.

Finding your first options does not wait for an exhaustive end-pair survey. In the
browser, search coverage and permissions are available beneath the opening answer.

## Inspect the linked figures

The teaching panel places one selected hairpin above the parameter plot. Shaded
connectors link its features to the axes: loop size, loop-side extension, basal
pairing, tails and the projected coordinates of later insert ends. The drawing
and plot fit together; detailed processing remains in the route below. You can
explore these features before deciding which to constrain. Fixed
requirements remain visible beside the plot; they do not consume extra axes.
Construction details remain in the exported parameter guide and API explanation.

```bash
uv run hop-design design view designs --out browser-view
```

Open the printed local address. Select a supported path to inspect its molecular
route. Filtering only narrows the recorded pool. To search further, run
`design continue` explicitly and reload the view. Selection carries through to
preparation retrieval without copying record coordinates.

## Inspect one route and retrieve its oligos

Select one recorded preparation with a reproducible seed, then use that same
selection for both figures and the material handoff:

```bash
uv run hop-design design sample designs --seed 1 --out selection.json
uv run hop-design design figure designs --selection selection.json --out choice-figure
uv run hop-design design atlas designs --selection selection.json --out molecular-route
uv run hop-design design retrieve designs --selection selection.json --out preparation
```

`choice-figure/figure.pdf` shows the supported paths. `molecular-route/projection.svg`
shows the selected construction at nucleotide resolution; its print export includes
readable pages. Open `preparation/preparation/report.md` for the selected construction and
`preparation/preparation/oligos.csv` for its exact source, adapter, primers and chemistry. Sampling chooses from recorded preparations; it does not rank
them by experimental performance. Use `design select --help` to choose an exact
preparation yourself.

The selected route reports added DNA in the requested product, distinct oligo
orders, shared roles and terminal modifications. These facts also appear beside
the molecule in the browser and in `molecular-route/construction-cost.json`.
Added-region coordinates locate the retained sequence on the endpoint; local
flank lengths are not summed to estimate whole-product overhead.

These are modeled preparations. The handoff identifies remaining experimental
conditions, including purification and destination compatibility.

## Use the same objects in Python

Use the same source environment for these examples (`uv run python`).

```python
from hop_design.construction import discover_designs, load_design_choices

choices = discover_designs(
    {"stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT", "product": "released_insert"},
    "python-designs",
)
answer = choices.explain()  # Product facts, applicable parameters and next actions.
selected = choices.sample(seed=1)
choices.figure(selection=selected).write("python-choice-figure")
choices.atlas(selected).write("python-molecular-route")
choices.retrieve(selected, "python-preparation")

# Reopen a relocated result, or retain this object for repeated fast queries.
saved = load_design_choices("python-designs")
matching = saved.query({"parameters": [{"key": "loop_nt", "values": [4]}]})
```

`choices.resolution` exposes the original intention, context, effective request and
origin of each group of settings. `choices.find_more(max_evaluations=64)` explicitly
advances discovery and returns a new snapshot; the original snapshot stays
unchanged.

## Browser controls

The browser keeps the choice plot and selected molecular route together. On a
pinned hairpin, click a labeled feature, such as the loop or added pairing, to
read its definition and current value. **Color by** shows that feature across the
existing map; **Filter to** narrows complete preparations to the displayed value.
Neither action changes the search permissions. Escape closes the feature without
closing the inspector, and keyboard focus offers the same actions.
Paths shared by several preparations open a chooser. Materials, fixed properties
and search coverage sit below the figures; the same facts remain in static exports. Tab enters
an axis or molecular region; arrow keys inspect its values or bases. Enter applies
a choice. At fit scale, scrolling moves the page; pinch or Ctrl-wheel zooms into
the molecule, after which scrolling pans it. **Fit route**, Home or 0 restores the
whole route. These camera operations leave the query and selection unchanged.

## Compose a compact figure

Choose the coordinates that explain your comparison without filtering out any
preparations. Repeat `--axis` in the desired drawing order:

```bash
uv run hop-design design figure designs --selection selection.json \
  --axis left_gap --axis right_gap --axis foldback_arm_bp --axis loop_nt \
  --out compact-choice-figure
```

The same operation is available through
`choices.figure(selection=selected, display_axes=("left_gap", "right_gap", "foldback_arm_bp", "loop_nt"))`.
Use `choices.parameters(query=query)` or
`hop-design design parameters designs --query query.json` to read a feature's
meaning, active constraints and available operations. For example, loop size has
permitted lengths; self-paired arm length follows from the arm and join position.
Left and right end gaps are revised together. A frozen atlas can be filtered,
while permission changes belong to its discovery request. Reading this guide to
the features does not run a search or verify preserved surroundings.

Requested constant coordinates remain visible. Unavailable,
inapplicable, repeated or noncanonical keys produce an error.

`display-projection.json` records displayed and omitted axes. `choices.json` and
`domains.csv` retain the complete coordinate data; paths that coincide in the
drawing retain all their preparation identities. This changes figure composition,
not requirements, search or selection. It also applies to
the linked trace of a selected similarity or family figure. The exact route and oligo
handoff continue to use the same selection.
For an export-only recipe, pass the recorded axes again. To keep that composition
when reopening the browser or reproducing a figure, save it with the selection:

```python
view = choices.view(
    selected,
    presentation={
        "landscape": "parameters",
        "display_axes": ["left_gap", "right_gap", "foldback_arm_bp", "loop_nt"],
    },
)
choices.figure(selection=view).write("compact-choice-figure")
```

The saved view retains the ordered axes. Browser hover, pinning and export use
that same recipe; older saved views retain their original display defaults.

## Seek a useful contrast

Use `design discover --diversify loop_nt` to prioritize different loop sizes within
the same construction permissions. Repeat `--diversify` for joint dimensions.
Continue, select, inspect and retrieve through the same commands. Sticky ends
remain optional.

To change a permitted arm range or method, preview a small explicit revision with
`design revise`, then execute it into a new discovery. See
[scaffold alternatives and permission edits](explore-scaffold-alternatives.md)
for CLI/API examples, supported dimensions and conflict recovery.

Start from your stem when seeking new constructions. Starting from an existing
oligo specification also carries its material restrictions into the search.
HOP's default insert context completes permitted auxiliary source bases as needed;
it does not use different auxiliary PCR handles as evidence of scaffold breadth.
Inspect loop, basal, interface and method alternatives in the returned complete
choices. A diversity objective changes search priority, not the permissions.

When that objective includes cloning ends or end gaps, HOP first suggests end pairs
from the permitted basal pairing relationships. It tries those pairs before the
ordinary coverage order, while keeping every other permitted pair reachable.
A suggestion still needs a complete preparation to establish support. An explicit
preparation preference takes precedence; missing or unfinished suggestions do not
establish that other pairs are impossible.

If you need to reuse an oligo, retain its exact material policy deliberately.
If you only need to preserve the experimental sequence, use the stem request above.
Advanced contexts distinguish [fixed, constrained and derived materials](../language/ontology.md#construction-search-and-its-molecular-meaning).
The resolved `intent/report.md` and `intent/request.json` show the effective
permissions; the same resolution is available through `resolve_design_request`
in Python and `design resolve` in the CLI.

## Refine only what matters to you

When additional source cuts remove only fragments outside the intended endpoint, an optional
[`source_cleanup` permission](discover-source-partitions.md#permit-cleanup-during-design-discovery)
lets HOP verify removal with the selected source nickases. The retained strands
and complete route must still pass verification.

Add an exact left end, an exact right end, or both when you have that requirement:

```bash
uv run hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product released_insert --left AGTC --right AACC \
  --out requested-ends
```

In a saved request, `"ends": {"left": ["AGTC", "AACC"]}` permits either left
word while leaving the right side open. Lists on both sides explicitly permit
their Cartesian combinations. Joint pair rosters are not accepted by this entry
contract; use separate requests to preserve a specific pair relationship.

Specified words are hard constraints. HOP keeps them when no preparation is found.
Read the result before deciding what to do next:

- **No recorded match:** refine a filter to inspect other recorded choices. If
  relevant search remains, evaluate another batch explicitly.
- **Excluded within the saved context:** continuing unchanged will not help.
  Inspect the method, geometry and material permissions in the saved intent, then
  make an explicit revised request in a new directory. The AGTC/AACC example above
  demonstrates this outcome under the default context.
- **Permission conflict:** the error identifies the requested property, permitted
  values and declaration to edit. More search cannot reconcile that contradiction.

For an unfinished insert search, use:

```bash
uv run hop-design design continue designs --evaluations 64 --format text
```

An ordinary batch limit returns the current choices. A sequence-domain, pending-work
or checkpoint-storage limit stops the command with an explicit error; Python raises
`ValueError` with the same reason. Previously committed preparations remain readable
with `design query` or `load_design_choices`. Unfinished targets remain unresolved.
Review the execution resources before retrying, rather than looping on an unchanged
limit. The simple insert workflow currently caps its checkpoint at 1 GiB; the
lower-level survey API exposes `max_checkpoint_bytes` for explicitly budgeted runs.

For scaffold or method requirements, save a concise JSON or YAML request:

```json
{
  "stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT",
  "product": "released_insert",
  "scaffold": {"loop_nt": {"minimum": 4, "maximum": 6}},
  "methods": {"release": ["BsaI-HFv2"]}
}
```

Pass it with `design discover --request intent.json --out designs-with-controls`.
The resolver intersects requirements with the context and reports conflicts;
it does not require you to duplicate a loop-size change in several declarations.

To inspect recorded preparations with a 4-nt loop, save `filters.json`:

```json
{"parameters": [{"key": "loop_nt", "values": [4]}]}
```

```bash
uv run hop-design design query designs --query filters.json --format text
```

This filter changes neither permissions nor search coverage. A released-end
coordinate is inapplicable to a hairpin endpoint; HOP reports that distinction
instead of returning a misleading empty list. Source-copying and foldback
measurements remain available when they occur along the requested route.

Use the displayed enzyme name in a filter, just as in the original request:

```json
{"parameters": [{"key": "release_method", "values": ["BsaI-HFv2"]}]}
```

HOP resolves names to catalog IDs for querying, selection and export. The returned
`query` shows that resolved meaning; `submitted_query` retains your input. If a
name identifies several permitted entries, use the exact catalog ID named in the
error. Equivalent measurements must agree: a 6-bp foldback arm and a 7-bp loop-side
extension describe conflicting requirements for this construction. HOP identifies
the conflict before filtering; further search cannot resolve it.

The browser's CLI block uses the actual discovery directory and a saved copy of
the applied query. Run those commands from a fresh output directory while the
browser's files remain available. Selection, route and preparation exports use
that same query. The block offers further search only when the result supports it.

## Request a hairpin endpoint

Use `--product hairpin` for a direct hairpin or
`--product adapter_ligated_hairpin` for the supported adapter-ligated endpoint.
Both use the same discover, query, select, atlas and retrieve operations. Neither
requires sticky ends or insert release.

The direct-hairpin context declares exact 10-base basal arms. The adapter-hairpin
context declares source and adapter handles and one association minimum. Inspect
those permissions before choosing a preparation. A displayed intermediate in an
insert route is different from requesting either hairpin endpoint.

Start with the first complete choice within your execution budget:

```bash
uv run hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product hairpin --evaluations 64 --first-choices 1 --out hairpins
uv run hop-design design continue hairpins --evaluations 4 --format text
```

`--first-choices` stops after the requested number of new complete preparations or
the evaluation limit, whichever comes first. It selects no molecule. The result
records both the requested effort and the examined prefix, including failed
attempts. Continuation writes an immutable page containing only new attempts.
The pages form a checked, contiguous history; earlier selections remain
retrievable from the same directory.

The Python equivalent is `discover_designs(..., first_choices=1)`, followed by
`choices.find_more(max_evaluations=4)`. Retain the returned object for fast filtering.
Each hairpin call examines at most 64 pairs, but continuation can traverse the
larger recorded local-pair space. Local search limits remain separate: exhausting
the recorded pairs does not establish that an upstream truncated search is complete.
First-choice stopping applies to the two hairpin endpoints. Insert discovery
retains its existing resumable evaluation batches.

## Compare loops while holding the scaffold

Use the same choices object to hold a selected molecule's surroundings and
require a deliberate set. This example permits two loop words and two arm lengths:

```python
choices = discover_designs(
    {
        "stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT",
        "product": "hairpin",
        "loop_words": ["GAAA", "TTTC"],
        "scaffold": {"loop_side_paired_bp": {"minimum": 7, "maximum": 8}},
    },
    "loop-designs",
    max_evaluations=4,
)
reference = choices.sample(seed=0)
query = choices.preserve(reference, stage="hairpin", except_neighborhood="loop")
matching = choices.query(query)
comparison = choices.compare(
    {
        "stage": "hairpin",
        "required_members": [
            {"name": "gaaa", "loop_sequence": "GAAA"},
            {"name": "tttc", "loop_sequence": "TTTC"},
        ],
        "max_group_evaluations": 16,
    },
    query=query,
)
```

`preserve` creates a new refinement from the exact reference molecule. Filters
used to find that reference stay in its selection; they do not prevent exploring
another loop. The original stem, construction permissions and discovery remain
unchanged. Add parameter filters to the returned query when needed. Its `changes`
report separates molecular neighborhoods from changed material roles.

Inspect `comparison["sets"]`, then explicitly select a set and its named baseline.
For this example, the available set is `set-0001`:

```python
selected = choices.select_set(comparison, set_label="set-0001", baseline="gaaa")
choices.retrieve(selected, "loop-preparations")
for name, member in selected["members"].items():
    choices.figure(selection=member).write(f"{name}-choices")
    choices.atlas(member).write(f"{name}-route")
```

Allowing two words in a filter permits either; `required_members` asks for both.
An absent member, incompatible shared controls and an unfinished group assessment
have separate results. No comparison starts another search or selects a set.
These operations also apply to released-insert choices. Use `stage="endpoint"`
to preserve the released product's surroundings, or `stage="hairpin"` to preserve
the intermediate. Differences discarded during processing do not violate an
endpoint control. The first molecular comparison replays the saved witnesses;
later filters reuse those admitted facts.

Insert selections retain the query and reference alongside the native preparation
record. Saved selections and selected sets remain retrievable after more
evaluations are appended. A new comparison uses the current snapshot.

For an insert set, start with the retrieved `report.md`: it names the comparison
stage, requested contrast, reference, shared controls and changed material roles.
`oligos.csv` consolidates exact sequences and terminal chemistry; `oligo-uses.csv`
retains every member and role. Each member links directly to its nucleotide
teaching view, full route and preparation conditions. `comparison.json` holds the
exact hairpin and insert differences, including unresolved base correspondence.

The CLI equivalents are `design preserve`, `design compare` and `design select-set`.
Saved refinements work with the existing `--query` option, and set selections use
the existing `design retrieve` command. See the [command reference](../reference/cli.md).

## Control the construction context

The default insert context, `linear-source/v2`, permits 3–8-nt loops, 6–12-bp
foldback arms, 0–2-nt join displacements, every minimum adapter annealing length
from 14 through 24 nt, and every left/right sticky-end-to-stem spacing from 0
through 6 bp (49 pairs). It includes the characterized
Nt.Bpu10I, Nb.BsrDI and BsaI-HFv2 methods. These are permissions, not promises that
every combination can be constructed. Saved requests retain their resolved
permissions. The earlier `linear-source/v1` context remains explicitly selectable
with its original subsets; loading it does not fill in omitted lengths.

The context also declares primer-length limits, canonical basal pairing, a source
handle domain and an exact synthetic adapter handle. They affect which options
are obtainable. Inspect `designs/intent/context.json`, then save an edited copy
and pass `--context my-context.json` when different permissions or materials are
needed. The saved result carries that context, so later inspection does not depend
on its original file location.

A release method must be permitted for end generation in both the basal region
and the release step. Resolution names these two fields if their permissions
conflict; it does not broaden either set automatically.

Execution limits are separate. `--evaluations` controls the amount of work in a
batch. Python callers can provide the explicit `effort` mapping for local search
limits. Larger quotas search further; they cannot repair a contradictory molecular
requirement.

For exhaustive interface accounting, use the [interface survey](survey-interfaces.md).
For an already exact construction request, use [construction compilation](design-a-construction.md).

## Require several experimental stems

Use an explicit family request when every expansion of an IUPAC stem is required.
The [one-N example](../../examples/stem-family-intent.json) previews four exact
stems with the same construction permissions. End words remain optional.

```bash
uv run hop-design design resolve --request examples/stem-family-intent.json --out family-preview
uv run hop-design design discover --request examples/stem-family-intent.json --evaluations 256 --out family --format text
uv run hop-design design query family --member member-0001 --format text
uv run hop-design design view family --member member-0001 --out member-view
```

`max_members` bounds expansion before search. `max_total_evaluations` bounds the
work reserved by family discovery and continuation; `--evaluations` is shared
across the required members, not multiplied by their count. Unexamined or missing
members stay in the roster. A later `design continue family` must fit the remaining
bound. An interrupted batch retains its member records and reserved work; inspect
those records before starting a revised family.

Each member has ordinary choices, figures and a preparation. Select one from each
member, then verify the complete membership and shared requirements:

```python
from hop_design import construction

family = construction.load_design_choices("family")
roster = family.query()
# Choose a supported common interface or other properties after inspecting the pool.
query = {"parameters": [{"key": "left_end_word", "values": ["AAAA"]}]}
members = {
    member["name"]: family.member(member["name"]).sample(seed=1, query=query)
    for member in roster["members"]
}
selection = family.select_members(members, baseline="member-0001")
family.retrieve(selection, "family-preparations")
```

Sampling each stem independently does not ensure common flanks. Selection checks
`non_stem_sequences` on the hairpin regions outside both supplied stem arms, plus
the requested material reuse. If those checks disagree, inspect other recorded
options before selecting again. Retrieval consolidates exact orders in
`oligos.csv`, with member and role assignments in `oligo-uses.csv`.

The CLI uses the same selection: save the member-to-selection mapping as JSON,
run `design select-members family --members membership.json --baseline member-0001
--out family-selection.json`, then use `design retrieve` with that selection.
This family specifies separate exact preparations; it does not establish a pooled
synthesis or processing protocol. One experimental member can have several scaffold
options and preparations, which are counted separately.
