---
doc_id: hop-adr-0022
title: ADR 0022 - Make boundaries, neutral order, and cohesive ends explicit
intent: Replace inferred boundary facts with strict coordinate and product contracts.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-23
doc_type: decision
---

# ADR 0022: Make boundaries, neutral order, and cohesive ends explicit

## Context

Four boundary facts were previously recoverable but under-specified or
duplicated: the foldback origin, the end of the source-derived foldback turn,
the meaning of candidate `rank`, and the single-stranded ends produced by a
facing restriction digest.

## Decision

Foldback requests declare the foldback origin once as
`retained_tract_span.start` and declare an exact `source_turn_span`. The
redundant generic `nick_boundary` field is removed; actual nicks remain typed
only in discovery, projection, and method contracts. Candidate records expose
`canonical_ordinal`, which is neutral replay order and never an objective score.
Literal candidate searches order by sequence content rather than GC,
homopolymer, extra-site, or pairing-profile measurements.
`RestrictionDigestProduct` contains two exact cohesive-end records with
sequence, protruding strand, polarity, aligned span, and both cut boundaries.

The retired fields are not accepted. Destination compatibility remains a
caller-owned relation and is not inferred from cohesive-end existence.

## Consequences

Generic foldback anatomy no longer implies an experimental nick, unrelated
precursor suffix cannot silently become turn sequence, and campaign systems
cannot mistake HOP order for optimization. Consumers no longer need to rederive
overhangs from cut coordinates.
