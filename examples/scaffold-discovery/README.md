# Request a scaffold before choosing its preparation

This example requests 18 open-side paired positions across four loop sizes,
permits adapter redesign and retrieves the named preparations. The public
[input provenance](../scaffold-options/README.md) remains unchanged. The
example uses the same publicly sourced stem and enzyme definitions, with a
9-bp loop-side extension.

The requested endpoint is a released duplex insert. The comparison stage is
the joined hairpin intermediate; downstream sticky ends do not appear on that
hairpin. The report distinguishes complete preparations from exact molecules at either
comparison stage. Geometry alone is insufficient to merge two products.

Run from the repository root with the matching source candidate:

```bash
uv run --locked python examples/scaffold-discovery/run.py /tmp/hop-scaffold-discovery
```

Choose a new output directory. The recipe writes a preview, complete options,
a named selected set and the separate failed request with preparation changes
disallowed. Open `selected/report.pdf` and `restricted/report.pdf`; retrieve
member-specific preparations from `selected/members/` and the consolidated
`oligos.csv` / `oligo-uses.csv` tables.

The same operations are available separately:

```bash
hop-design construction preview-scaffolds examples/scaffold-discovery/request.json --out /tmp/scaffold-preview
hop-design construction discover-scaffolds examples/scaffold-discovery/request.json --out /tmp/scaffold-options
hop-design construction select-scaffolds /tmp/scaffold-options --member loop3=branch-0001-option-0001-01 --baseline loop3 --out /tmp/scaffold-selected
```

The explicit label in the last command belongs to this example's packet. Inspect
your own report before selecting; HOP assigns no default winner.

Edit `scaffold.open_side_paired_positions` to specify the desired molecule.
`preparation_changes.adapter_redesign` permits corresponding preparation
candidates; it does not replace a fixed material declaration or relax another
hard requirement. The preview names conflicts and the declarations to edit.
`max_branches` and `max_continuations_per_branch` bound separate search layers.

For permitted methods, use `methods.json` with the same preview/discovery commands.
It permits BsaI-HFv2, BsmBI-v2 and BbsI-HF as separate strict release branches.
The definitions come from the [manufacturer recognition and cleavage catalogue](https://www.neb.com/en-us/tools-and-resources/selection-charts/alphabetized-list-of-recognition-specificities).
The bounded example returns four complete preparations for each of the first two
methods and four rejected BbsI continuations. Inspect those recorded outcomes
before selecting a preparation.

To compare open-side architectures, change the requested range to 17–24 and
`max_branches` to 8. Four loop cases then each offer eight different hairpins
leading to an identical released product. Set `comparison_stage` to `endpoint`
for that grouping; keep `hairpin` when comparing intermediate substrates.
The report highlights the whole hairpins, changed pairing positions, common
released product and changed material roles. Named selections preserve all exact
preparations. See the [workflow and request contract](../../docs/guides/discover-product-scaffolds.md)
and [implementation decision](../../docs/architecture/decisions/0043-product-driven-scaffold-discovery.md).

## Terminal forms of an actual hairpin

`terminal-form.json` is a version 2 discovery request for the adapter-ligated
hairpin endpoint. Its 5-prime and 3-prime terminal requirements are 6 and 14 nt.
The sequence provenance is the same as above. No downstream copying or release
is requested.

```bash
uv run --locked python examples/scaffold-discovery/terminal_forms.py /tmp/hop-terminal-forms
```

The recipe changes only the high-level terminal requirements to request 6/14,
6/8, 6/0 and 0/0. It verifies one complete preparation for each form, then
explicitly selects all four for this prescribed comparison. Open
`selected/report.pdf`: whole hairpins, countable terminal bases and changed
material roles share one plate. `selected/set.json` regenerates the comparison
and preparations after relocation.

In this example only the adapter changes; the fully paired terminus adds six
open-side paired positions. Ordinary discovery still returns alternatives without
choosing a preparation. Read the [terminal request contract](../../docs/guides/discover-product-scaffolds.md#request-the-terminal-form-of-a-hairpin)
before adapting its sequence and redesign permissions.

## Joint receiving-end alternatives

`receiving_ends.py --out NEW.json` writes the bounded three-pair example described
in [the receiving-end walkthrough](../../docs/guides/discover-product-scaffolds.md#explore-declared-receiving-end-pairs).
Words, polarity, orientation and placements stay together. The resulting v6
request uses the same preview, discovery, conditional browsing and retrieval APIs.
