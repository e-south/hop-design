---
doc_id: hop-discovery-and-selection
title: Discovery and selection
intent: Explain bounded geometry discovery, symbolic domains, and caller-owned choice.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-29
doc_type: explanation
journey:
  - discover
---

# Discovery and selection

HOP keeps four operations distinct:

1. **Evaluate** a fully declared component.
2. **Discover** sequence-and-cut compatible candidates inside explicit domains.
3. **Select** a candidate using caller-owned experimental or procurement policy.
4. **Compile** selected components or a named method into replayable artifacts.

Discovery does not silently perform selection.

## Payload-centered local construction discovery

A local construction request fixes the final payload, route family, requested
endpoint, and one foldback or basal target. Exact targets are examined before
enabled relaxation shells. Each realization preserves both the requested
geometry and achieved geometry, so a nearby compatible result cannot be
mistaken for an exact match.

Relaxation is a declared bounded neighborhood, not an optimization. HOP does
not score a shell, infer a preferred geometry, or claim that the first returned
realization is best. Its status reports what the bounded search established:

- `complete`: the declared stopping rule was satisfied without firing a bound,
  every entered shell is complete, and at least one compatible local
  realization was found. `through_radius` exhausts every declared radius;
  `first_feasible_shell` may stop after the first complete feasible shell;
- `infeasible`: the stopping rule exhausted every shell it requires without a
  compatible realization; or
- `truncated`: a named bound fired before the stopping rule was satisfied. Its
  final entered shell may be partial, or a later required shell may remain
  unentered.

Shell accounting records examined candidates, accepted realizations,
rejections, and observed failure categories. A partial shell may appear only
in a truncated result. A local construction projection renders the same typed
result as neutral JSON, CSV, or SVG without selecting a realization or
recomputing molecular state. Local feasibility does not establish physical
construction, a complete route, quality control, or biological activity.

## Foldback geometry

A nick-placement target declares the desired nick boundary and strand, the
paired-tract length, and the turn nucleotides available to hold a recognition
site. HOP can search exact and nearby boundaries, then materialize precursor
sequences within caller-authored IUPAC templates.

Recognition-motif length is not automatically an added-nucleotide cost. Motif
positions may overlap the paired tract or the declared turn. The relevant
measure is how far a placed footprint extends beyond sequence already available
to the design, reported through required precursor and turn lengths.

Current released-foldback discovery evaluates one caller-declared paired-tract
length and turn length at a time. It does not prove that the returned geometry
is globally shortest across all possible lengths. A caller can compare a
bounded set of target geometries using the reported physical measurements.

## Symbolic domains

An IUPAC symbol is a set of possible bases, not a wildcard character. HOP uses
set intersection to distinguish guaranteed, possible, and absent motif
presence. Exact precursor searches calculate their candidate-space cardinality
before enumeration and preserve correlation between paired positions.

Avoid an unqualified “degeneracy cost.” Neutral measurements include:

- the number of authored positions narrowed by a process footprint;
- the resolved domain at each position; and
- the change in exact sequence-space cardinality.

Synthesis cost, preferred diversity, and application value belong to the
caller.

## Ordering is not recommendation

Candidate order is deterministic so two consumers can replay the same bounded
result. Basal and concrete precursor searches use literal content order;
geometry searches use stable identifiers and declared coordinate relations.
Measured GC content, homopolymer length, extra-site counts, or M/W/X profiles
do not silently determine the prefix returned under a hit budget.

`canonical_ordinal` is only a reproducible position in HOP's neutral order. It
is not a score or recommendation. A future optimization surface would have to
name its objective, report its measurements, and define deterministic
tie-breaking. The caller should persist its own selection rule and selected
candidate identity.

## What site placement proves

Site placement proves that the motif, orientation, and cut coordinates fit the
modeled substrate. It does **not** prove empirical cleavage efficiency.
Activity near a linear end and sensitivity to flanking bases vary by enzyme and
reaction conditions. NEB recommends extra flanking bases for uncharacterized
cases, while its published results remain enzyme-specific; a single global
cutoff would create false acceptance and false rejection. See [NEB's
cleavage-close-to-ends guidance](https://www.neb.com/tools-and-resources/usage-guidelines/cleavage-close-to-the-end-of-dna-fragments).

Catalog entries can carry warning codes, but current discovery does not convert
them into feasibility or empirical performance claims. A future advisory
contract should identify the agent, applicable context, evidence, and severity.
Until then, callers must apply and preserve their own versioned protocol rules.

The [mechanics reference map](../reference/mechanics-api.md) routes each bounded search
and its completion evidence.
