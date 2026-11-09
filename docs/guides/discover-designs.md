# Discover complete designs around your stem

Start with the stem you need and the product you want. HOP searches the permitted
construction flanks and returns complete preparations. Sticky ends are optional:
you can explore what is obtainable before deciding which ends suit your next step.

The **supplied stem**, or payload, is the paired region to preserve. The
**scaffold** is the loop, added pairing and other construction sequence around it.
A **preparation** combines exact materials with the ordered steps, or **route**,
that produce the requested molecule. Several preparations can make the same product.

[Install HOP](install.md), then run the examples below. Each output path must
be new so an earlier result is never overwritten.

After finding useful choices, [save a preparation collection](share-atlas-edition.md)
to share their exact molecules, figures and materials without repeating search.

## Find your first choices

Replace the example stem with one exact A/C/G/T arm, written 5′→3′ from the
basal (open) end toward the loop. Omit the loop and complementary arm; HOP
derives the complement. For required members from an IUPAC stem, use a
[family request](discover-designs/require-comparative-preparations.md#require-several-experimental-stems).

This example requests a released duplex insert:

```bash
# Preserve this stem and search for complete constructions.
hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product released_insert \
  --out designs --format text
```

The default **context** declares the available enzymes, allowed lengths and
positions, and which source, adapter and primer bases may be designed or reused.
You can inspect these before adding optional constraints. Read
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

The inspector shows a hairpin above its parameter plot. Each path connects the
values for one complete preparation. Shaded connectors link
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

The selected route's report lists added DNA in the requested product, distinct
oligo orders, shared roles and terminal modifications. These facts also appear beside
the molecule in the browser and in `molecular-route/construction-cost.json`.
Added-region coordinates locate the retained sequence on the endpoint. Local
flank lengths are not summed to estimate whole-product overhead.

The handoff lists remaining preparation conditions, including purification and
destination compatibility.

## Use the same objects in Python

[Add HOP to your Python project](install.md#use-python), then run `uv run python`.

```python
# Use the same request and selection through Python.
from hop_design.construction import discover_designs

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
```

### Inspect saved choices

Replace `python-designs` below with your existing discovery directory.

```python
# Reopen a saved result for read-only filtering.
from hop_design.construction import load_design_choices

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
[browser controls](../reference/view-contracts/complete-preparation-views.md#browser-controls) for keyboard
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

## When no preparation is recorded

An empty answer can mean unfinished search, a filter with no recorded match, or
exclusion within the saved context. **Filtering** inspects already recorded
preparations; **discovery** evaluates new possibilities under the request's
permissions. Read the reported scope before choosing the next action.

- **No recorded match:** refine a filter to inspect other recorded choices. If
  relevant search remains, evaluate another batch explicitly.
- **Excluded within the saved context:** continuing unchanged will not help.
  Inspect the method, geometry and material permissions in the saved intent, then
  make an explicit revised request in a new directory. The AGTC/AACC
  [requested-end example](discover-designs/refine-the-search.md#refine-only-what-matters-to-you)
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

## Refine or require a set

[Refine the search](discover-designs/refine-the-search.md) when you need exact ends,
scaffold or method requirements, a different construction context, or a useful
contrast. Filtering recorded preparations and changing search permissions are
separate operations.

[Require comparative preparations](discover-designs/require-comparative-preparations.md)
to request loop alternatives with shared surroundings or one preparation for
every experimental stem. Permitting alternatives does not require every member.
