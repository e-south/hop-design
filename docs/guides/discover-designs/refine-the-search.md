# Refine a discovery search

Add the molecular requirements that matter, inspect matching recorded
preparations, or revise the construction permissions explicitly. Start with
[a discovery](../discover-designs.md#find-your-first-choices); examples that query
`designs` use that saved directory. New requests and exports need new output paths.

## Seek a useful contrast

Use `design discover --diversify loop_nt` to prioritize different loop sizes within
the same construction permissions. Repeat `--diversify` for joint dimensions.
Continue, select, inspect and retrieve through the same commands. Sticky ends
remain optional.

To change a permitted arm range or method, preview a small explicit revision with
`design revise`, then execute it into a new discovery. See
[scaffold alternatives and permission edits](../explore-scaffold-alternatives.md)
for CLI/API examples, supported dimensions and conflict recovery.

Start from your stem when seeking new constructions. Starting from an existing
oligo specification also carries its material restrictions into the search.
HOP's default insert context completes permitted auxiliary source bases as needed.
Inspect loop, basal, interface and method alternatives in the returned complete
choices. A diversity objective changes search priority, not the permissions.

See [search allocation](../../reference/interface-survey-search/execution-and-coverage.md#evaluate-and-resume)
for end-pair suggestions and preparation-preference precedence.

If you need to reuse an oligo, retain its exact material policy deliberately.
If you only need to preserve the experimental sequence, use the
[stem request](../discover-designs.md#find-your-first-choices).
Advanced contexts distinguish [fixed, constrained and derived materials](../../language/ontology/molecular-meaning-and-search.md#construction-search-and-its-molecular-meaning).
The resolved `intent/report.md` and `intent/request.json` show the effective
permissions. The same resolution is available through `resolve_design_request`
in Python and `design resolve` in the CLI.

## Refine only what matters to you

When additional source cuts remove only fragments outside the intended endpoint, an optional
[`source_cleanup` permission](../discover-source-partitions.md#permit-cleanup-during-design-discovery)
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

## Add scaffold requirements or filters

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

For exhaustive interface accounting, use the [interface survey](../survey-interfaces.md).
For an already exact construction request, use [construction compilation](../design-a-construction.md).

If the answer is empty or unfinished,
[interpret its reported scope](../discover-designs.md#when-no-preparation-is-recorded)
before continuing. Return to the [retrieval workflow](../discover-designs.md#inspect-one-route-and-retrieve-its-oligos)
after choosing a complete preparation.
