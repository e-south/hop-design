# Enumerate exact basal sequence populations

HOP evaluates the complete source before counting distinct sequences in a local
basal window. Different enzymes or outside source contexts can support the same
local configuration; they do not multiply its count.

The [example request](../../examples/basal-sequence-space.yaml) reuses the public
loxP payload and catalog from the [basal example](../../examples/basal-junction/README.md).
It fixes nick displacement n=0 and paired gap e=0 and searches all four-base ends.
The canonical contact W=max(1,e+k−n)=4 is derived from this geometry. It is not a
complete adapter length or a stability threshold. Full association remains
explicitly unresolved.

```python
# Count exact basal assignments under the requested geometry and pairing constraints.
import json
from hop_design import construction

space = construction.discover_basal_sequence_space("examples/basal-sequence-space.yaml")
result_path = space.write("basal-populations") / "result.json"
verified = construction.load_verified_basal_sequence_space(result_path)
result = json.loads(verified.json_bytes)
print(verified.candidate_count, verified.admitted_count)
```

The example has two nick-strand cases, 512 raw local configurations, and four
admitted configurations. Its small catalog is a teaching context, not a claim
about every enzyme. Source-duplex recognition and enzyme-defined cut offsets
remain explicit.

## Counted object and constraints

One case fixes exact payload, nick coordinate and strand, pairing window, and
future-end domain. A source word contains W paired-source bases followed by n
bases up to the payload boundary. Its raw population is 4^(n+W). Exact end
identities and enzyme programs constrain that population rather than multiplying
its denominator. The local window must cover the future-end footprint.

Each program retains its exact target, placement-compatible source count,
placement exclusion when applicable, admitted full-source set, and local set.
Molecular admission checks intended and unintended actionable sites on the whole
source. A recognition site crossing the plotted window's edge still matters.
Projection removes outside context only after admission. The local union counts
each sequence once.

These are exact sets that preserve correlations, not samples or products of
positional frequencies. The common [sequence-set encoding](foldback-sequence-space.md#what-is-counted)
supports cardinality, membership, and lexicographic recovery. Empty cases retain
their raw denominator. No permitted program means exhausted absence within the
stated catalog. IUPAC payloads produce separate exact cases, without asserting
that every payload member is compatible.

Canonical pairing is an explicit capability of this compact operation. Other
pair permissions raise; detailed local discovery supports the broader pairing
contract.

## Separate scientific bounds from computation

`max_retained_overhead_nt` bounds the declared local source span n+W, not total
precursor, adapter, primer, or reagent cost. For an n/e landscape, derive W for
each coordinate and choose increasing budgets before inspecting results. The
[two-neighborhood example](../../examples/local-envelope/README.md) explains that
geometry without retaining an inherited exemplar length.

`limits` independently bounds cases, examined programs, decisions and operations
per builder, recognition windows per program, and total serialized decisions.
Exhaustion raises without a complete result; it never becomes molecular absence.
Local spans and full-source sets are supported through 256 nt. Requests are
limited to 1 MB and portable results to 64 MiB. These are execution capabilities,
not biological thresholds.

## Recover an exact molecular example

Select a case, a zero-based lexicographic word rank, and an examined program that
supports that word. For the example:

```python
# Recover one exact assignment from a nonempty sequence set.
case = next(case for case in result["cases"] if case["sequences"]["cardinality"])
program_index = next(i for i, p in enumerate(case["programs"]) if p["sequences"]["cardinality"])
member = json.loads(
    verified.member_json(case_id=case["case_id"], rank=0, program_index=program_index)
)
```

HOP constrains that program's admitted source set to the selected local word,
recovers its first exact source, derives the canonical adapter and required
recognition context, then performs ordinary molecular realization. Unsupported
word/program combinations raise. Rank is an address, not an optimization score.

Local existence does not establish full materials, association, thermodynamic
stability, or experimental recovery. Cohesive-end optionality can be studied
separately by projecting admitted words onto the end footprint. A union across
varying sources does not mean one fixed source can produce every end.
