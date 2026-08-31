---
doc_id: hop-adr-0032
title: ADR 0032 - Compose one explicitly selected local pair
intent: Evaluate one caller-selected foldback and basal pair without replaying their full Cartesian product.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
---

# ADR 0032: Compose one explicitly selected local pair

## Context

Local discovery can produce many exact foldback and basal alternatives. After a
caller selects one realization from each replay-verified receipt and derives
their matching design authority, exhaustive complete composition would still
evaluate the full local Cartesian product. That work answers a different
question from whether the selected pair resolves through the declared endpoint.

## Decision

`compile_construction_from_local_realizations` accepts one strict construction
source, one separately verified design bundle, replay-verified foldback and
basal receipts, and one explicit realization identity from each receipt. The
source must declare the exact local requests that produced the receipts. The
selected realizations must belong to those authorities, match the exact design
payload, and satisfy the existing endpoint and design-encoding contracts.

Selection is recorded on the existing complete-construction request. Absent
selection fields are omitted from canonical serialization, so the established
exhaustive compiler retains its exact request, result, and bundle bytes. A
selected execution has one foldback member, one basal member, one nominal
combination, and one examined disposition. The existing endpoint evaluator,
materializer, result model, portable bundle, and replay verifier remain the
authorities for its outcome.

Local-search truncation does not make an explicitly selected pair truncated:
the selected molecular authorities are already present and replay-verified.
Endpoint evaluation may still report an explicit truncation if its own declared
bound prevents a conclusion.

## Consequences

The operation returns the existing `ConstructionCompilation` receipt and adds
no public model. It does not rank or choose local alternatives, weaken source
identity, infer missing materials, or claim laboratory construction. Unknown,
wrong-family, source-mismatched, forged, or design-incompatible selections fail
before a portable authority is returned.
