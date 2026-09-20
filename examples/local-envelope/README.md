---
doc_id: hop-local-envelope-example
title: Enumerate two local construction regions
intent: Teach independent coordinate budgets, exact coverage, and caller-owned selection.
audience:
  - new construction users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-09-19
doc_type: tutorial
---

# Enumerate two local construction regions

A fixed payload still permits many construction sequences. This example derives
local lengths from geometry, enumerates those possibilities under explicit
budgets, and retains the exact HOP results. It reuses the public loxP payload
and characterized enzymes in the [basal-junction example](../basal-junction/README.md).
Its small catalog is a stated teaching context, not a claim about all enzymes.

From the repository root:

```bash
uv run python examples/local-envelope/search.py \
  --basal-budget 4 --foldback-budget 10 --out build/local-envelope
```

The command writes `summary.csv`, `summary.json`, and ten independently
replayable request/result pairs. The small example exhausts its scope. It finds
basal solutions but no foldback solution in this catalog and envelope. A
zero after complete search has meaning; choosing different constraints solely
to make every panel colorful would erase that lesson.

## What varies

Basal coordinates are nick displacement **n** and paired gap **e** between the
future end and payload. An end of length **k** occupies source coordinates
`[-e-k, -e)`; the nick is at `-n`. The minimal canonical contact covering the
relevant interval is `W=max(1,e+k-n)`. This example searches all n/e pairs whose
local span `L=n+W=max(n+1,e+k)` fits the supplied basal budget, both nick
strands, and both release orientations. It preserves the input end domain;
the supplied request asks for every four-base 5′ end. The full association
requirement is explicitly null. Neither L nor W is a complete adapter length
or a thermodynamic stability rule.

Foldback coordinates are added paired arm **A**, unpaired cap **C**, and
displacement **D**. This example searches every supported integer A/C pair
under retained non-payload path `H=2A+C`, and D from zero through A. The
post-nick self-paired arm **R=A-D** is derived. The current model starts at
A=3 bp and C=3 nt; these are model floors, not experimentally established
universal minima. All allowed nicking enzymes from the supplied catalog are
eligible for the foldback role.

The two budgets measure different objects. H counts retained nucleotides;
the basal budget bounds a local source-coordinate interval. Neither measures
total precursor, primer, or reagent cost. Recognition sites and cleavage
positions are separate: each oriented enzyme definition fixes its own cut
offsets. Recognition length is not automatically extra construction cost.

## Enlarge the envelope without changing the answer in advance

Choose an increasing sequence of budgets before examining the outcome. Pass
each pair to the same command with a fresh output directory. The supplied
4/10 pair is a fast computational exercise, not a recommended biological
length. Larger budgets include more possibilities and can take much longer.
The input request's node and realization limits still apply; this script does
not silently raise them or resume a partially completed invocation.

`observed_witness_count` counts returned HOP realizations. For a truncated
query it is only a lower bound. It is not a count of distinct projected
sequences, a survival fraction, or a laboratory success probability. A plot
must state its counted object, aggregate hidden dimensions explicitly, and
deduplicate equivalent witnesses before claiming a sequence-state count.
Do not divide witnesses by `4^length`: paired positions, latent geometry, and
action aliases make that comparison invalid without a matching identity.

Two-dimensional n/e and A/C plots can summarize these results. Each point
represents all explicitly searched hidden choices, not one sequence. Keep
unfinished search, exhausted absence, and outside-budget geometry distinct.
If every point has a solution, binary dots are uninformative; inspect exact
counts or another scientifically defined quantity rather than inventing a
cutoff. Selection happens after enumeration and requires a named caller rule.

The script accepts an unpartitioned basal request with source-duplex recognition
and a right 5′ endpoint. It rejects other coordinate conventions before writing
output rather than applying this interval formula to a different strand model.

## Keep end optionality and complete construction distinct

Exact end identities remain in the basal results and may be inspected
separately from the enumeration landscape. Here the source sequence can vary.
An end union across those sources is not a claim that one fixed source can
produce every end. A positional N pattern is valid only when its Cartesian
product exactly equals the observed set; correlated sets need exact identities.

Local admission leaves full association, materials, complete composition, and
experimental performance unresolved. Use the
[construction guide](../../docs/guides/compile-construction.md) when those
obligations become the research question.
