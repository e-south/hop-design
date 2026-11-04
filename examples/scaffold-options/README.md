# Choose scaffolds before choosing preparations

These public requests share a 34-bp stem and permit four loop sizes across three
closing extensions. `hairpin.json` requests a direct hairpin endpoint;
`insert.json` requests a released duplex insert. Their open-side constructions
are different; they are not two aliquots of one preparation.

Run the [public workflow](../../docs/guides/explore-scaffolds.md). The three
operations are exploration, comparison discovery and explicit selection. The
same `comparison.json` carries molecular controls from discovery to retrieval.
It does not prescribe a winning background or relax a failed request.

Example, from the repository root:

```bash
uv run hop-design construction explore examples/scaffold-options/insert.json \
  --max-continuations 12 --out /tmp/hop-options
uv run hop-design construction option-sets /tmp/hop-options \
  examples/scaffold-options/comparison.json --out /tmp/hop-option-sets
uv run hop-design construction select-options /tmp/hop-options \
  --comparison examples/scaffold-options/comparison.json \
  --option option-0005-01 --option option-0006-01 \
  --option option-0007-01 --option option-0008-01 \
  --baseline option-0005-01 --out /tmp/hop-selected
```

Inspect the group report before choosing labels: these particular labels refer
to the recorded 9-bp background for this example. Another complete background
has 12-bp closing extensions. `report.pdf` in the selected packet shows the
chosen molecules, shared controls, changed materials and supported product stage.
Every preparation retains its unresolved experimental conditions.
