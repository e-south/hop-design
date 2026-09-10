---
doc_id: hop-adr-0035
title: ADR 0035 - Bound noncanonical basal pairing
intent: Keep an aggregate pairing constraint separate from molecular classification.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-09-08
doc_type: decision
---

# ADR 0035: Bound noncanonical basal pairing

`BasalGeometryDomain.max_noncanonical_pairs` optionally limits the number of
non-Watson–Crick pairs across the declared proximal `pairing_constraints`.
G:T/T:G wobble and other mismatches each consume one position in this budget.
Literal pair classes remain distinct. The cap does not cover distal adapter
completion or assert ligation efficiency. Its window can differ from the final
cohesive end when the nick is displaced from the payload.

The cap travels into each exact `BasalTarget`. Search applies it before accepting
a witness; intrinsic realization replay enforces the same predicate. Result
validation binds the target cap back to the request. Excluded candidates retain
the `basal-pair-budget-exceeded` disposition and obey existing enumeration bounds.

## Contract

This is an optional additive field in the current pre-1.0 schema. Omission means
no aggregate cap, not an implicit biological default. The absent value is not
serialized; unconstrained request and result bytes retain their meaning. An
explicit cap participates in identities. Readers without this field reject it;
there is no compatibility reader or alias. Callers choose and record the cap.

Tests cover zero, two, and absent budgets, G:T counting, invalid counts, complete
infeasibility, and resealed over-budget molecular records.
