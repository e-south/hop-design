# Edit retained scaffold sequence

This example uses the public stem and material context described in
[scaffold options](../scaffold-options/README.md). It compares exact GAAA/TTTC
loops with shared surrounding sequence and retrieves both preparations.

```bash
uv run --locked python examples/molecular-editing/run.py /tmp/hop-molecular-edit
```

Open `alternatives/report.pdf` for the molecular comparison and
`selected/report.md` for the retrieved set. `selected/oligos.csv` gives exact
sequence and terminal chemistry; `oligo-uses.csv` retains each material role.
`timing.json` separates preview, evaluation and retrieval. Use a fresh output
directory for every execution.

To browse these admitted options in one molecular viewport:

```bash
uv run --locked hop-design construction edit-view /tmp/hop-molecular-edit/alternatives --evaluated --out /tmp/hop-molecular-view
```

For the bounded AAAA/AACA background-discovery example and separate admission,
query and retrieval measurements:

```bash
uv run --locked python examples/molecular-editing/conditional.py /tmp/hop-conditional
```

The [conditional guide](../../docs/guides/explore-conditional-variants.md) explains
neighborhood choices, preserved properties, stage identity and explicit selection.

See the [edit guide](../../docs/guides/edit-folded-sequences.md) for finite end
placements and the four-member [sequence family](sequence-family.json). The
base request has a two-branch budget. A three-distance comparison requires an
explicitly larger budget to examine all three; the tool does not silently enlarge it.

The Nb.BtsI entry is represented in the reverse-complement orientation of NEB's
GCAGTG (none/0) convention: CACTGC with a nick at reference boundary 0.
[NEB recognition/cleavage definition](https://www.neb.com/en-us/products/r0707-nbbtsi).
The example permits Nb.BsrDI by default; selecting another catalogued method is
an explicit edit, not a claim about laboratory stock or reaction compatibility.

Hairpins in this example are intermediates of a released duplex insert.
The drawn primary sequence and contacts are recorded architecture, not a folding
prediction. Exact construction and preparation records do not establish recovery,
destination compatibility or experimental function.

## Coupled construction envelope

`construction-envelope.json` fixes receiving end words while leaving foldback arm
and loop lengths and words free within explicit construction bounds. It permits
join displacements over the budget range, two basal nickases and joint end
placements; computation quotas remain separate from those molecular permissions. Run `construction
discover-scaffolds` with that request, then `construction edit-view --evaluated`.
The [parameter walkthrough](../../docs/guides/explore-conditional-variants.md#explore-the-construction-envelope)
explains brushing, local support, bounded coverage and explicit further evaluation.

`envelope.py RESULT NEW_OUTPUT` demonstrates an explicit permission revision:
retain a derived R target, open arm and loop domains, evaluate and save complete
choices. The preview records every changed field. The original evidence and
query preservation controls remain intact. Use the browser's domain chooser to
browse unobserved values, or the matching `parameter-values`, `revise-envelope`
and `evaluate-envelope` CLI operations.
