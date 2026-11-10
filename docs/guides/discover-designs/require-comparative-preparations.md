# Require comparative preparations

Require every member of a loop comparison or experimental stem family, then
select and retrieve a compatible set. A list of permitted values alone allows
alternatives; it does not require all of them.

Use the [Python setup](../discover-designs.md#use-the-same-objects-in-python)
and import `discover_designs` from `hop_design.construction` for the loop
example. Its first block creates `choices`, `reference`, `query` and
`comparison`; keep those objects for the selection block. Each output path must
be new. The family example instead loads its own saved `family` discovery.

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
the existing `design retrieve` command. See the [command reference](../../reference/cli.md).

## Require several experimental stems

Use an explicit family request when every expansion of an IUPAC stem is required.
The [one-N example](../../../examples/stem-family-intent.json) previews four exact
stems with the same construction permissions. End words remain optional. Run
this repository example from a [source checkout](../install.md#work-from-source).

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

For a single product, return to [discovery and retrieval](../discover-designs.md).
To change permitted scaffolds or methods, [refine the search](refine-the-search.md).
