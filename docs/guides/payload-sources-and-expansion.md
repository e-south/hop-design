# Payload sources and explicit expansion

Represent each payload as a `PayloadRecord`. Inline iterables,
FASTA, and CSV all produce the same strict record shape, so input acquisition
stays separate from design compilation.

Each record supplies one payload arm, the experimental sequence to preserve;
HOP derives its paired arm during compilation. A record may contain exact
A/C/G/T bases or IUPAC choices. Loading a record does not expand those choices
or search for a preparation.

## Inline records and duplicate policy

```python
# Load inline payload records with an explicit duplicate policy.
import hop_design as hop

records = (
    hop.PayloadRecord(record_id="exact-1", payload=hop.ExactPayload(sequence="ACGT")),
    hop.PayloadRecord(record_id="symbolic-1", payload=hop.DegeneratePayload(sequence="NRY")),
)
collection = hop.collect_payloads(
    records,
    duplicate_policy=hop.DuplicateSequencePolicy.FAIL,
)
```

Record IDs must always be unique. Duplicate sequences require one explicit
policy: `FAIL`, `DEDUPE`, or `KEEP`. The returned collection records that
decision for downstream provenance.

## FASTA and CSV

```python
# Read the same payload records from FASTA and CSV.
fasta_records = hop.load_fasta_payloads("payloads.fasta")
csv_records = hop.load_csv_payloads(
    "payloads.csv",
    id_column="payload_id",
    sequence_column="sequence",
)
```

FASTA uses the first whitespace-delimited header token as `record_id`. CSV
column names are caller-selected. Malformed rows, invalid DNA, empty inputs,
symlinks, and duplicate record IDs fail instead of being skipped. The local
eager readers enforce the named `DEFAULT_PAYLOAD_SOURCE_LIMITS` for bytes,
records, and total nucleotides. Supply a stricter `PayloadSourceLimits` when the
caller has a smaller budget.

## Explicit concrete expansion

```python
# Expand this DNA IUPAC record into exact members within the stated bound.
record = hop.PayloadRecord(
    record_id="variants",
    payload=hop.DegeneratePayload(sequence="NR"),
)
result = hop.expand_payload(record, max_variants=8)
```

For `NR`, `N` permits four bases and `R` permits two, giving eight exact variants.
HOP computes that count, or cardinality, first. Over-budget requests raise
`VariantBudgetExceededError(cardinality=..., max_variants=...)` before variant
records are allocated. Successful variants are exact, deterministically
ordered, and receive stable `-v0001`-style IDs. Expansion is never implicit in
`compile`.

## Compose a design space

`ResolvedDesignSpace` composes four independently typed axes: a
`PayloadCollection`, `FoldbackOption` records, `BasalOption` records, and
explicit `ReleaseOption` records. A no-release case is a named option with
`request=None`; it is not a hidden fallback.

These axes are sets of choices: payloads, loop-end components, open-end
components and release requirements. Planning combines one choice from each
set and checks the resulting design.

```python
# Compose the payload records with the chosen design context.
space = hop.ResolvedDesignSpace(
    space_id="example-space",
    payloads=collection,
    foldbacks=foldback_options,
    basals=basal_options,
    releases=(hop.ReleaseOption(option_id="no-release", request=None),),
    defaults_ref="example:defaults/resolved@1",
    catalog_ref="example:processing-catalog/synthetic@1",
    constraint_profile_ref="example:constraint-profile/explicit@1",
    design_derivation_ref="example:design-derivation/component-evaluation@1",
    per_design_constraints=hop.DesignLimits(max_candidates=1),
    limits=hop.DesignSpaceLimits(max_designs=64),
    duplicate_final_sequence_policy=hop.DuplicateDesignSequencePolicy.FAIL,
)
table = hop.plan_design_space(space)
```

HOP computes the full Cartesian cardinality before allocating rows and raises
`DesignSpaceBudgetExceededError` rather than truncating. The returned
renderer-free table carries one strict `ResolvedHopSpec` and `CheckReport` per
combination, its projected final sequence when feasible, and
feasible/infeasible/duplicate counts. Duplicate projected sequences either fail
or remain as fully retained rows under the explicit `KEEP` policy; HOP never
silently deduplicates. Compile only selected rows with `hop.compile(row.spec)`;
planning the space does not render or write bundles.

## Run the advanced payload-record example

The complete public example starts with three exact payloads, applies one
explicitly selected foldback/basal anatomy, plans the bounded three-design
space, writes one bundle per design, and independently replay-verifies every
bundle:

```bash
# Run the repository example and write its verified payload bundles.
uv run python examples/compile_payload_records.py \
  --out build/payload-records
```

This is the advanced forward path for exact payload records on selected anatomy:

```text
caller payloads + selected anatomy
    -> bounded design-space plan
    -> caller selection
    -> deterministic encodings
    -> replay-verified design bundles
```

Use this lower-level path when you already have explicit foldback and basal
anatomy. The example uses synthetic anatomy; supply your own selected components
or obtain them through bounded HOP discovery. For a simpler fixed-context
workflow, use [substrate spaces](substrate-spaces.md).

Historical migration can run in the opposite direction—decomposing a known
full hairpin sequence into explicit HOP components and requiring exact replay.
That is a parity and provenance exercise, not the normal authoring experience.
