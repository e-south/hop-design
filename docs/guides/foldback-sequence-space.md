---
doc_id: hop-foldback-sequence-space
title: Enumerate exact foldback sequence populations
intent: Count bounded local configurations and recover exact molecular members.
audience: [Python users, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-09-20
doc_type: how-to
journey: [discover, verify]
---

# Enumerate exact foldback sequence populations

For a fixed payload, ask which local foldback configurations satisfy the modeled
cleavage, release, pairing, and joining constraints. The complementary arm is
derived. The independent sequence has A arm bases followed by C cap bases;
retained non-payload length is H = 2A + C. Displacement D is measured from the
payload boundary, and the post-nick self-paired arm has R = A − D base pairs.

Use [the synthetic request](../../examples/foldback-sequence-space.yaml) to search
both nick strands, D = 0–3, and every supported geometry through H = 10 nt:

```python
import json
from hop_design import construction

space = construction.discover_foldback_sequence_space("examples/foldback-sequence-space.yaml")
result_path = space.write("foldback-populations") / "result.json"
verified = construction.load_verified_foldback_sequence_space(result_path)
result = json.loads(verified.json_bytes)
print(verified.candidate_count, verified.admitted_count)

case = next(case for case in result["cases"] if case["sequences"]["cardinality"])
```

The example has 16 exact geometry/strand cases and 163,840 raw configurations.
It admits 190 distinct configurations. Exhaustive full molecular discovery
independently checks every admitted member, including the empty cases. The
enzyme definition is a synthetic fixture, not a reagent recommendation.

## Enzyme roles and alternative preparations

Foldback closure and final cloning-end generation are separate operations.
The foldback solver represents two ways to establish the strand ends needed
for closure:

| Foldback program | Source of the foldback-side terminus | Material consequence |
| --- | --- | --- |
| `single_cleavage` | The source already ends at the required boundary; a nick controls the opposite strand. | The recorded source terminus must carry the required 5′ phosphate. |
| `sequential_terminus_plus_nick` | A duplex cut defines the terminus before nicking; sequence beyond that boundary is removed. | The cut supplies the phosphate-bearing terminus; the extra cleavage step and transient source DNA remain part of the preparation. |

The current sequential solver requires coincident cuts on the two strands at
that boundary: a blunt terminus. It reports `unsupported-staggered-terminus`
for staggered cuts. That is a boundary of this modeled route, not a conclusion
that other termini cannot be used experimentally. Ordinary blunt cutters can
therefore be relevant here even though they cannot generate the requested
cloning sticky ends. Type IIS classification alone does not establish an
enzyme's role; recognition, cut geometry and the actual substrate do.

Only caller-permitted programs are searched. A new supported program may
prepare a sequence already admitted by another program. Keep the program
alternatives and distinct sequence configurations separate; adding enzyme
names does not necessarily add molecular diversity. A caller-supplied cut
definition also does not establish that all necessary biochemical conditions
have been represented or satisfied.

## What is counted

One case fixes the exact payload, A, C, D, and nick strand. It starts with
4^(A+C) independent sequence choices. Each provisioned program applies its
recognition placement and ordered molecular constraints. The result records
the placement-compatible count, placement exclusion if any, and exact admitted
set for every program. Their union counts a configuration once even when
several enzymes support it. No permitted program means an exhausted empty
admitted set, with the raw population still present.

`sequences` is a canonical decision diagram, not a sample or an independence
approximation. Each decision has A/C/G/T branches; shared downstream decisions
compactly retain correlations. The program sets and their union can recover
every admitted member. A JSON reader can inspect the schema without importing
internal HOP models.

An embedded `hop.sequence-set/v1` object records `length_nt`, `decisions`,
`root`, and `cardinality`. Terminal 0 rejects and terminal 1 admits every
remaining suffix. Decision rows have implicit IDs starting at 2 and contain
`position_nt` plus four `branches` in A/C/G/T order. Child decisions appear
before their parents; positions increase along every path. Positions skipped
by a path are unconstrained. These sets encode the independent arm-then-cap
word, never a second independently authored complementary arm. Structural
validity and cardinality alone do not establish molecular admission; use the
public result loader for that verification.

Exact and IUPAC payload requests use the same operation. An IUPAC request
records separate exact payload cases; the result does not assert that every
payload member is compatible merely because one case has solutions.

## Bounds and geometry

`max_retained_overhead_nt` is an inclusive scientific search ceiling. Empty
arm/cap lists enumerate all lengths satisfying the declared floors and this
ceiling; explicit lists restrict the domain. `junction_offsets_nt` is an
explicit finite D domain. The current geometry contract has minimum arm and
cap lengths of three. These model-domain floors do not establish thermodynamic
or experimental viability. The retained path excludes transient construction
and auxiliary materials, so minimizing H does not establish minimum total cost.

`limits` bounds execution separately: exact cases, examined programs, decisions
and operations per set builder, recognition windows per program, and serialized
decisions across the whole result. Exhaustion raises; it never becomes a
completed empty set. A returned receipt covers the entire declared domain.
Requests are limited to 1 MB and portable results to 64 MiB. The current
retained-path execution ceiling is 256 nt.

## Recover a selected member

Each serialized case includes a content-bound `case_id` for its exact payload
and coordinates. Use that identifier and a zero-based lexicographic rank, then
choose an examined program that supports that sequence:

```python
member = json.loads(
    verified.member_json(
        case_id=case["case_id"],
        rank=0,
        program_index=0,
    )
)
```

`member_json` repeats ordinary molecular realization for that source and
program. An unsupported member/program combination raises. Rank is an address,
not an optimization score. The returned local realization retains recognition
spans, cut coordinates, fragment and strand states, pairing, ligation, and
material obligations. Complete material selection and experimental success
remain separate questions.
