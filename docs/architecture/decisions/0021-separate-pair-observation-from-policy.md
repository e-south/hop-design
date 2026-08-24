---
doc_id: hop-adr-0021
title: ADR 0021 - Separate pair observation from acceptance policy
intent: Make physical pair kind invariant across all HOP operations.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-23
doc_type: decision
---

# ADR 0021: Separate pair observation from acceptance policy

## Context

Foldback, basal, and stem-extension paths could classify the same G:T pair
differently depending on an `allow_gt_wobble` input. That made a physical fact
depend on policy.

## Decision

One literal classifier applies everywhere:

- canonical complements are `watson_crick`;
- G:T and T:G are `gt_wobble`;
- every other pair is `hard_mismatch`.

Policy may accept, reserve, or reject an observed kind but may not relabel it.
The retired `allow_gt_wobble` request fields are rejected rather than adapted.
The `pair-count-weighted@1` support and disruption indices are explicit,
dimensionless policy heuristics. They replay M/W/X weights but make no energetic
or empirical claim.

## Consequences

Pair observations replay identically across components, methods, views, and
serialized artifacts. Constraint profiles carry the remaining acceptance
choice explicitly.
