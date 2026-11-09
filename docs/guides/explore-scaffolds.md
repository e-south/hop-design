# Explore complete scaffolds

When desired open-side dimensions should drive preparation changes, start with
the [product-first workflow](discover-product-scaffolds.md). Its
`hop.scaffold-discovery/v1` request separates desired scaffold properties from
adapter-redesign permission and previews conflicting declarations. The
single-request operations below remain the inner complete-options workflow.

Start with a product request: the stem, desired product state, allowed scaffold
geometry and permitted preparation methods. HOP can evaluate complete alternatives
before you choose a local construction. Exploration leaves every requirement intact.

The public example expands the closing region to loops of 3, 4, 6 and 8 nt and
loop-side extensions of 6, 9 and 12 bp. It retains the existing insert interface
and preparation permissions. From the repository root:

```bash
# Explore complete scaffolds from the repository request.
uv run hop-design construction explore examples/scaffold-options/insert.json \
  --max-continuations 12 --out /tmp/hop-options
```

Open `report.pdf` for whole molecules and countable closing-region enlargements.
`report.md` links each visible option label to its exact preparation, and retains
failed examined combinations. No option is chosen automatically. The pictures
show hairpin intermediates for an insert request; the supported continuation is
shown separately. Use `examples/scaffold-options/hairpin.json` for direct hairpin
endpoints.

## Define a useful comparison

`comparison.json` in the example asks for one member at each loop count, with
surrounding sequence, region-local contacts and joins, terminal chemistry, both
extensions and product interfaces shared. It requests a molecular comparison,
not a causal biological conclusion.

```bash
# Assess which recorded options can satisfy the comparison.
uv run hop-design construction option-sets /tmp/hop-options \
  examples/scaffold-options/comparison.json --out /tmp/hop-option-sets
```

The resulting report shows complete and incomplete shared backgrounds. Each
complete background lists the option labels that can supply each requested
member. Distinct preparations remain distinct choices even when their displayed
geometry agrees. No reference scaffold is required in advance.

The public envelope provides a complete loop series on both 9-bp and 12-bp
closing extensions. The 6-bp background lacks a completed 3-nt-loop preparation:
the examined source preparation supplies 13 nt where its reverse primer needs
14 nt. That is a failure of this examined continuation, not global impossibility.

## Retrieve explicit choices

Use the labels in the report, choose one label per requested member, and state
the baseline used for comparison. Retrieval checks the original molecular records
and shared controls, then writes a portable set with individual preparations,
whole-molecule figures, comparisons and consolidated oligo specifications.

Reuse the comparison intent instead of entering its controls again:

```bash
# Retrieve only the explicitly selected options.
uv run hop-design construction select-options /tmp/hop-options \
  --comparison examples/scaffold-options/comparison.json \
  --option option-0005-01 --option option-0006-01 \
  --option option-0007-01 --option option-0008-01 \
  --baseline option-0005-01 --out /tmp/hop-selected
```

These example labels choose the 9-bp background. Selection requires exactly one
molecule for each requested member and verifies every shared property. Omit
`--comparison` when retrieving a single label. For a custom set, use repeated
`--shared PROPERTY` and `--compare PROPERTY` instead of a comparison file.

The selected set's `set.json` can be passed to `construction select-set` after
moving the directory. It does not depend on the original options path.

## Interpret coverage

A continuation budget counts examined local pairs, including rejected ones.
Ordering is the saved foldback witness order, then saved basal witness order.
The direct-hairpin path has no basal witness search. Increasing only the budget
examines a longer prefix without changing earlier product or preparation identities.

Products obtained and comparison obtained are separate questions. In this
example, a six-pair prefix supplies all four loop sizes but no complete group
under the declared shared controls. Eight pairs supply one common background;
twelve supply two. A one-pair prefix yields no complete molecule and leaves
11 recorded pairs unexamined. Increase the explicit budget before interpreting
that stopped prefix as a reason to change molecular requirements.

Even when every recorded pair is examined, a local quota or search-node limit
may leave other candidates unexplored. Reports preserve each local termination
and each complete continuation's accounting. No claim of global route exhaustion,
minimal preparation, laboratory performance or destination compatibility follows.

## Scope

This workflow explores the existing molecular domain; it adds no new chemistry.
Open-side dimensions may be inspected and compared when complete records support
them, but they are not a new independent family authoring control. Exposed sticky
ends on a hairpin are not implied by a later released-insert interface. Each
preparation retains its unresolved reaction and separation conditions.
