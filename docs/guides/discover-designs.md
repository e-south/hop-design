# Discover complete designs around your stem

Start with the stem you need and the product you want. HOP searches the permitted
construction flanks and returns complete preparations. Sticky ends are optional:
you can explore what is obtainable before deciding which ends suit your next step.

[Install HOP](install.md), then run the examples below. Each output path must
be new so an earlier result is never overwritten.

After finding useful choices, [save a preparation collection](share-atlas-edition.md)
to share their exact molecules, figures and materials without repeating search.

## Find your first choices

Replace the example stem with one exact A/C/G/T arm, written 5′→3′ from the
basal (open) end toward the loop. Omit the loop and complementary arm; HOP
derives the complement. For required members from an IUPAC stem, use a
[family request](#require-several-experimental-stems).

This example requests a released duplex insert:

```bash
# Preserve this stem and search for complete constructions.
hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product released_insert \
  --out designs --format text
```

The default context supplies enzyme, geometry and material permissions. You can
inspect these before adding optional constraints. Read
`designs/intent/report.md` for the context and `designs/intent/request.json` for
its effective settings. To inspect those settings before searching, use the same
flags with `design resolve --out intent`.

The answer lists complete preparations, their loop and end features, and next
commands. It leaves selection to you. `--format text` keeps the summary readable.
`--format json` includes the full parameter domains and coverage. The default is
text on a terminal and JSON when piped.

Finding your first options does not wait for an exhaustive end-pair survey. In the
browser, search coverage and permissions are available beneath the opening answer.

## Inspect the linked figures

The inspector shows a hairpin above its parameter plot. Shaded connectors link
loop size, added pairing, basal contacts, tails and later insert ends to their
axes. Hover to compare preparations and pin one to inspect its route. Fixed
requirements remain visible beside the plot.

```bash
# Open the recorded choices without starting another search.
hop-design design view designs --out browser-view
```

Open the printed local address. Select a supported path to inspect its molecular
route. Filtering only narrows the recorded pool. To search further, run
`design continue` explicitly and reload the view. Selection carries through to
preparation retrieval without copying record coordinates.

## Inspect one route and retrieve its oligos

Continue only if discovery has recorded a complete preparation. Otherwise,
[interpret the result](#when-no-preparation-is-recorded) before sampling.
Select one preparation with a reproducible seed and use that same selection for
both figures and materials.

```bash
# Record one reproducible selection. Every export below uses that same preparation.
hop-design design sample designs --seed 1 --out selection.json

# Export its linked parameter figure, molecular route and exact oligos.
hop-design design figure designs --selection selection.json --out choice-figure
hop-design design atlas designs --selection selection.json --out molecular-route
hop-design design retrieve designs --selection selection.json --out preparation
```

`choice-figure/figure.pdf` shows the supported paths. `molecular-route/projection.svg`
shows the selected construction at nucleotide resolution. Its print export includes
readable pages. Open `preparation/preparation/report.md` for the selected construction and
`preparation/preparation/oligos.csv` for its exact source, adapter, primers and
chemistry. Sampling chooses from recorded preparations. Use `design select --help`
to choose an exact preparation yourself.

For ordering or importing oligos, retain `sequence_5prime`, `five_prime_end` and
`three_prime_end` together. One CSV row can serve multiple roles. `oligos.fasta`
contains sequences only; terminal chemistry remains in `oligos.csv`.

The selected route reports added DNA in the requested product, distinct oligo
orders, shared roles and terminal modifications. These facts also appear beside
the molecule in the browser and in `molecular-route/construction-cost.json`.
Added-region coordinates locate the retained sequence on the endpoint. Local
flank lengths are not summed to estimate whole-product overhead.

The handoff lists remaining preparation conditions, including purification and
destination compatibility.

## Use the same objects in Python

[Add HOP to your Python project](install.md#use-python), then run `uv run python`.

```python
# Use the same request and selection through Python.
from hop_design.construction import discover_designs, load_design_choices

choices = discover_designs(
    {"stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT", "product": "released_insert"},
    "python-designs",
)
answer = choices.explain()  # Product facts, applicable parameters and next actions.
if answer["matching_preparations"]:
    selected = choices.sample(seed=1)
    choices.figure(selection=selected).write("python-choice-figure")
    choices.atlas(selected).write("python-molecular-route")
    choices.retrieve(selected, "python-preparation")
else:
    print(answer["headline"], answer["guidance"])
    if "continue_search" in answer["actions"]:
        print("Continue with choices.find_more(max_evaluations=64).")

# Reopen a relocated result, or retain this object for repeated fast queries.
saved = load_design_choices("python-designs")
matching = saved.query({"parameters": [{"key": "loop_nt", "values": [4]}]})
```

Move the whole discovery directory and reopen it with its original HOP/Python
producer environment. To inspect a fixed collection independently of that
producer, [capture it before changing environments](share-atlas-edition.md).

`choices.resolution` exposes the original intention, context, effective request and
origin of each group of settings. `choices.find_more(max_evaluations=64)` explicitly
advances discovery and returns a new snapshot. The original snapshot stays
unchanged.

## Browser controls

Click a labeled molecular feature to read its definition and current value.
**Color by** changes its display; **Filter to** narrows recorded preparations
without changing search permissions. See the
[browser controls](../reference/view-contracts.md#browser-controls) for keyboard
navigation, zoom and route inspection.

## Compose a compact figure

Choose the coordinates that explain your comparison without filtering out any
preparations. Repeat `--axis` in the desired drawing order:

```bash
# Show only these axes while retaining every recorded preparation.
hop-design design figure designs --selection selection.json \
  --axis left_gap --axis right_gap --axis foldback_arm_bp --axis loop_nt \
  --out compact-choice-figure
# Creates compact-choice-figure/figure.pdf and its coordinate data.
```

Display axes change figure composition, not requirements, coverage or selection.
See the [parameter reference](../reference/molecular-parameters.md#compose-a-parameter-figure)
for Python recipes, saved views and exported coordinate data.

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
HOP's default insert context completes permitted auxiliary source bases as needed.
Inspect loop, basal, interface and method alternatives in the returned complete
choices. A diversity objective changes search priority, not the permissions.

See [search allocation](../reference/interface-survey-search.md#evaluate-and-resume)
for end-pair suggestions and preparation-preference precedence.

If you need to reuse an oligo, retain its exact material policy deliberately.
If you only need to preserve the experimental sequence, use the stem request above.
Advanced contexts distinguish [fixed, constrained and derived materials](../language/ontology.md#construction-search-and-its-molecular-meaning).
The resolved `intent/report.md` and `intent/request.json` show the effective
permissions. The same resolution is available through `resolve_design_request`
in Python and `design resolve` in the CLI.

## Refine only what matters to you

When additional source cuts remove only fragments outside the intended endpoint, an optional
[`source_cleanup` permission](discover-source-partitions.md#permit-cleanup-during-design-discovery)
lets HOP verify removal with the selected source nickases. The retained strands
and complete route must still pass verification.

Add an exact left end, an exact right end, or both when you have that requirement:

```bash
# Require the requested cloning ends without changing the stem.
hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product released_insert --left AGTC --right AACC \
  --out requested-ends
```

In a saved request, `"ends": {"left": ["AGTC", "AACC"]}` permits either left
word while leaving the right side open. Lists on both sides explicitly permit
their Cartesian combinations. Joint pair rosters are not accepted by this entry
contract. Use separate requests to preserve a specific pair relationship.

Specified words remain hard constraints when no preparation is found.

### When no preparation is recorded

An empty answer can mean unfinished search, a filter with no recorded match, or
exclusion within the saved context. Read its reported scope before choosing the
next action.

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
# Continue unfinished work under its recorded permissions.
hop-design design continue designs --evaluations 64 --format text
```

An ordinary batch limit returns the current choices. A sequence-domain, pending-work
or checkpoint-storage limit stops the command with an explicit error. Python raises
`ValueError` with the same reason. Previously committed preparations remain readable
with `design query` or `load_design_choices`. Unfinished targets remain unresolved.
Review the execution resources before retrying, rather than looping on an unchanged
limit. The simple insert workflow currently caps its checkpoint at 1 GiB. The
lower-level survey API exposes `max_checkpoint_bytes` for explicitly budgeted runs.

### Add scaffold requirements or filters

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
The resolver intersects requirements with the context and reports conflicts.
It does not require you to duplicate a loop-size change in several declarations.

To inspect recorded preparations with a 4-nt loop, save `filters.json`:

```json
{"parameters": [{"key": "loop_nt", "values": [4]}]}
```

```bash
# Inspect recorded preparations with the saved filter.
hop-design design query designs --query filters.json --format text
```

This filter changes neither permissions nor search coverage. A released-end
coordinate is inapplicable to a hairpin endpoint. HOP reports that distinction
instead of returning a misleading empty list. Source-copying and foldback
measurements remain available when they occur along the requested route.

Use the displayed enzyme name in a filter, just as in the original request:

```json
{"parameters": [{"key": "release_method", "values": ["BsaI-HFv2"]}]}
```

HOP resolves names to catalog IDs for querying, selection and export. The returned
`query` shows that resolved meaning. `submitted_query` retains your input. If a
name identifies several permitted entries, use the exact catalog ID named in the
error. Equivalent measurements must agree: a 6-bp foldback arm and a 7-bp loop-side
extension describe conflicting requirements for this construction. HOP identifies
the conflict before filtering. Further search cannot resolve it.

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
# Request a hairpin endpoint.
hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product hairpin --evaluations 64 --first-choices 1 --out hairpins
hop-design design continue hairpins --evaluations 4 --format text
```

`--first-choices` stops after the requested number of new complete preparations or
the evaluation limit, whichever comes first. It selects no molecule. The result
records both the requested effort and the examined prefix, including failed
attempts. Continuation writes an immutable page containing only new attempts.
The pages form a checked, contiguous history. Earlier selections remain
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
# Preserve the scaffold while assessing the requested loop alternatives.
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
used to find that reference stay in its selection. They do not prevent exploring
another loop. The original stem, construction permissions and discovery remain
unchanged. Add parameter filters to the returned query when needed. Its `changes`
report separates molecular neighborhoods from changed material roles.

Inspect `comparison["sets"]`, then explicitly select a set and its named baseline.
For this example, the available set is `set-0001`:

```python
# Preserve the scaffold while assessing the requested loop alternatives.
selected = choices.select_set(comparison, set_label="set-0001", baseline="gaaa")
choices.retrieve(selected, "loop-preparations")
for name, member in selected["members"].items():
    choices.figure(selection=member).write(f"{name}-choices")
    choices.atlas(member).write(f"{name}-route")
```

Allowing two words in a filter permits either. `required_members` asks for both.
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
`oligos.csv` consolidates exact sequences and terminal chemistry. `oligo-uses.csv`
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
Nt.Bpu10I, Nb.BsrDI and BsaI-HFv2 methods. Complete-route checks determine which
combinations work within these permissions. Saved requests retain their resolved
permissions. The earlier `linear-source/v1` context remains explicitly selectable
with its original subsets. Loading it does not fill in omitted lengths.

The context also declares primer-length limits, canonical basal pairing, a source
handle domain and an exact synthetic adapter handle. They affect which options
are obtainable. Inspect `designs/intent/context.json`, then save an edited copy
and pass `--context my-context.json` when different permissions or materials are
needed. The saved result carries that context, so later inspection does not depend
on its original file location.

A release method must be permitted for end generation in both the basal region
and the release step. Resolution names these two fields if their permissions
conflict. It does not broaden either set automatically.

Execution limits are separate. `--evaluations` controls the amount of work in a
batch. Python callers can provide the explicit `effort` mapping for local search
limits. Larger quotas search further. They cannot repair a contradictory molecular
requirement.

For exhaustive interface accounting, use the [interface survey](survey-interfaces.md).
For an already exact construction request, use [construction compilation](design-a-construction.md).

## Require several experimental stems

Use an explicit family request when every expansion of an IUPAC stem is required.
The [one-N example](../../examples/stem-family-intent.json) previews four exact
stems with the same construction permissions. End words remain optional. Run
this repository example from a [source checkout](install.md#work-from-source).

```bash
# Require several experimental stems.
uv run --locked hop-design design resolve --request examples/stem-family-intent.json --out family-preview
uv run --locked hop-design design discover --request examples/stem-family-intent.json --evaluations 256 --out family --format text
uv run --locked hop-design design query family --member member-0001 --format text
uv run --locked hop-design design view family --member member-0001 --out member-view
```

`max_members` bounds expansion before search. `max_total_evaluations` bounds the
work reserved by family discovery and continuation. `--evaluations` is shared
across the required members, not multiplied by their count. Unexamined or missing
members stay in the roster. A later `design continue family` must fit the remaining
bound. An interrupted batch retains its member records and reserved work. Inspect
those records before starting a revised family.

Each member has ordinary choices, figures and a preparation. Select one from each
member, then verify the complete membership and shared requirements:

```python
# Select one compatible preparation per required stem.
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
This family specifies separate exact preparations. One experimental member can
have several scaffold options and preparations, which are counted separately.
