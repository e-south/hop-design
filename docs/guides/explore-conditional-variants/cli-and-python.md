# Inspect conditional variants through CLI and Python

Use the saved `/tmp/hop-conditional/alternatives` result created by the
[conditional example](../explore-conditional-variants.md), from the same
[source checkout](../install.md#work-from-source) and locked environment.
The first section creates the query packet and the Python `pool` and `choices`
objects used by the later inspection and selection operations.

In generic CLI forms, `RESULT` is that saved result and `CHOICES` is its exported
query packet. Use a reported `VARIANT_ID` and preparation `OPTION`; every `NEW`
output directory must be new. Keep the query bound to its result digest. In the
inline Python selection call, `result` means the loaded `pool`.

## The same choice model through CLI and Python

```bash
# Query conditional choices from the recorded result.
uv run --locked hop-design construction variants /tmp/hop-conditional/alternatives --stage hairpin --focus loop --out /tmp/hop-choices
```

The packet contains `query.json`, `summary.json` and a short report. A query has
an exact `result_digest`, `stage`, `focus`, optional fixed `reference`, `pins`,
`controls` and `surroundings`. Supported neighborhoods are `loop`, `closing`, `assembly`, `stem`
and `interfaces`. A variant describes the observed regional sequence, pairing
contacts and relevant termini; it names supporting complete options.

For an explicit control, use `--reference OPTION` and repeat
`--preserve hairpin:non_loop_sequences` or another stage/property pair. To reuse
or refine exact selections, pass `--query query.json` instead of those flags.
Each pin has one `neighborhood` and an array of allowed `variant_ids` taken from
the admitted result. Values within a pin are alternatives; different pins must
all hold together. A replacement query omits **only the focused pin** when listing
its alternatives. `compatible_options` still enforces every active pin.

```python
# Use the same recorded result and choice model through Python.
import json
from hop_design import construction

pool = construction.load_scaffold_exploration("/tmp/hop-conditional/alternatives")
choices = construction.query_scaffold_variants(
    pool,
    {
        "result_digest": pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
    },
)
print(json.loads(choices.json_bytes)["variants"])
```

Keep `pool` in memory for repeated queries. Admission replays the captured result
once. Queries use immutable facts without search, replay or report generation.
Reports are created on export; molecular drawings are separate projections.
Retrieval re-admits the source and re-derives the query before selecting:

```text
uv run --locked hop-design construction select-variants RESULT CHOICES --member NAME=OPTION --baseline NAME --out NEW
```

Repeat `--member` to specify the set. Python uses
`select_scaffold_variants(result, choices, members={name: option_label}, baseline=name)`.
Passing valid labels cannot bypass active pins or controls. A selection includes
`exploration-query.json` and `exploration-selection.json`, preserving the result,
reference and query identities. The portable set contains the molecular records;
the query records the selection criteria.

## Preview a local variant through CLI/API

Run the public browsing example against the same saved result:

```bash
# Preview one alternative without committing a new selection.
uv run --locked python examples/molecular-editing/browsing.py /tmp/hop-conditional/alternatives /tmp/hop-browsing --word AAAC --state cleaved_duplex
```

Read `preview/summary.json`. `preparation_choice_required` lists exact candidates;
rerun into a new directory with `--option` and a displayed candidate label. The
variant, constraints and processing phase remain explicit. `--state` accepts a
semantic phase, `all`, `hairpin`, `endpoint`, `source_material`, or an exact state ID.
A missing or ambiguous phase returns a named outcome with no substitute drawing.

```text
uv run --locked hop-design construction preview-variant RESULT CHOICES --variant VARIANT_ID --state cleaved_duplex --out NEW
```

Add `--option OPTION` to resolve a preparation explicitly. Optional `--focus`
contains an exact molecular address and requires `--focus-option` naming its
originating preparation. Across preparations, focus transfers only through a
unique recorded material identity and coordinate by default. `--focus-mode comparison`
also permits an unambiguous, region-bound comparison position when its material
ancestry changes. The response distinguishes `comparison_position` from
`shared_material`; neither changes a molecular record. Unresolved correspondence
clears the position with an explanation. Sequence similarity alone is insufficient.

Use `--view-from previous.json` to request transition correspondence. That file
contains `option_label` and `state` for the preceding drawing. The Python request
has the same `view_from` object and `focus_mode` field. `transition.links` separates
`retained`, `copied` and `comparison` relationships; unmapped addresses and notices
remain explicit. Animation interpolates between the recorded states.

Nicked and associated fragment drawings align recorded pairings while preserving
covalent breaks. Rounded translucent spans mark recorded enzyme recognition
footprints throughout the recorded route, independently of active cuts. Their
presence can be complete, partial, not yet present, removed or unresolved. A
footprint traces bases from a recorded recognition span; it does not establish
that the displayed substrate is cleavable. Active operation outlines and dashed
strand-specific cuts remain stage-bound: pre-cleavage marks are planned;
post-cleavage nick marks are applied.
Released insert views show achieved end-to-stem gaps separately from recognition
sites.

## Export the complete atlas

```text
uv run --locked hop-design construction atlas RESULT CHOICES --option OPTION --out NEW
```

The browser and `preview-variant` CLI default to `all`; Python preview requests
retain their `hairpin` default, so pass `"state": "all"` explicitly. An all-state
response supplies `inspection.atlas` and `atlas_transitions`. The separate
`inspect_scaffold_atlas(pool, choices, request)` operation takes result/query
digests and one `option_label`, plus an optional exact `focus`. It exports the
same `projection.svg`, captured `request.json` and exact atlas record. Occurrences
are preparation/state/strand/index tuples. Recorded ancestry and verified
cross-variant correspondence remain distinct relations.

The atlas aligns the supplied stem across states and marks changed inputs beside
their recorded uses. Primer arrows annotate recorded binding spans; an input
that binds a derived complementary template is identified explicitly rather than
drawn as a separate annealed state. Unpaired handles use schematic 45° branches;
noncanonical contacts retain their distinct pairing marks. Every base remains in
the vector scene, although overview text requires zoom for nucleotide reading.

## Read the complete route

The atlas places the early processing stages down two columns, then centers the
hairpin-PCR duplex and released insert below them. Follow the numbered stages
down the left column, continue at the top of the right column, then read the
full-width finish. A direct hairpin route ends at its recorded hairpin state.

Unpaired handles bend away from the stem, then continue parallel to it. The
five-spacing bend is a drawing convention. Denatured fragments retain their
precursor registration with a small displacement; the drawing does not add
pairing contacts. Stage titles, enzyme names and termini use larger text while
nucleotide spacing remains unchanged.

`projection.svg` is the interactive overview. `projection.pdf` and `pages/` use
seven-inch pages with bases at least 8 pt, annotations at least 9 pt and labeled
continuations for wide scenes. Every base keeps its original molecular address;
view breaks are not cuts. Print at 100%. `print-layout.json` records the panel
boundaries and base ranges. Exact sequence and material
comparisons, when requested, are in `comparison.svg` and the packet summary.
The route retains their base highlights and correspondence warning.

For browser selection and the example's controlled comparison, return to
[conditional exploration](../explore-conditional-variants.md). To evaluate more
possibilities, [inspect the construction envelope](construction-envelope.md).
