---
doc_id: hop-adr-0036
title: ADR 0036 - Expose command and artifact handoffs
intent: Let independent consumers use existing HOP authorities without Python dependency coupling.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-09-12
doc_type: decision
---

# ADR 0036: Expose command and artifact handoffs

Consumers need HOP's exact derivations and rendered material handoffs while
maintaining independent installations. Python model imports unnecessarily
couple their package graphs and API migrations.

Expose named domain commands over existing request, result, and bundle files.
Command adapters call public use cases; they do not derive molecular state.
Machine-readable reports bind canonical authority bytes and expose existing
producer-computed identities and dispositions. No scientific models,
algorithms, generic RPC dispatch, or executable object representations are
copied into consumers. The current artifact formats and atomic publication
writers remain authoritative.

The executing producer reports installation provenance separately from its
actual package-content digest. Consumers explicitly select its environment.
They may retain a report for later schema and byte checks, but only a producer
execution establishes a fresh deterministic replay claim. Historical frozen
evidence remains unchanged.

The cost is explicit process invocation and replay when reopening authorities.
The benefit is independent installation and release ownership without weaker
scientific checks. CLI parity tests bind report authorities and generated files
to existing public operations; corruption and invalid-input tests preserve
failure behavior. See the [external artifact reference](../../reference/external-artifacts.md).
