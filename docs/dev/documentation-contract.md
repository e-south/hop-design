---
doc_id: hop-documentation-contract
title: Public concept documentation contract
intent: Standardize the epistemic boundary documented for public HOP concepts and operations.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: reference
journey:
  - maintain
---

# Public concept documentation contract

Every new public object or operation must document these sections, combining
adjacent sections only when the result remains explicit:

1. **Question answered** — the user-level competency question.
2. **Meaning** — the physical or semantic entity represented.
3. **Authored inputs** — fields supplied by the caller.
4. **Derived values** — values HOP computes and owns.
5. **Invariants** — conditions that must always hold.
6. **Claim made** — what successful validation or execution establishes.
7. **Non-claims** — what success explicitly does not establish.
8. **Identity and lineage** — IDs, digests, spans, and parent relations.
9. **Operations** — public producers and consumers.
10. **Failure semantics** — invalid input, infeasibility, unavailability, and
    truncation channels.

Tutorials may introduce only the subset needed for one journey. Reference pages
remain canonical and must link back to the appropriate design, discovery,
method, provenance, or ecosystem surface.

Public prose uses “provenance and verification” for computational derivation
claims. “Experimental evidence” is reserved for caller-owned observations.
