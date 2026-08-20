---
doc_id: hop-design-contracts
title: HOP Design engineering contracts
intent: State non-negotiable invariants, error channels, and change rules.
audience:
  - maintainers
  - API consumers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# HOP Design engineering contracts

## Invariants

- The payload is authored once; the paired payload is its DNA IUPAC reverse
  complement and is never an input field.
- Exact payloads accept only `A/C/G/T`. Degenerate payloads accept the complete
  DNA IUPAC alphabet and reject RNA `U`.
- Symbolic payloads remain symbolic unless the explicit `expand_payload`
  operation receives and enforces a hard `max_variants` budget after computing
  exact cardinality.
- Public models are strict, frozen, and reject unknown fields.
- Spans are zero-based and half-open. Boundaries, nucleotide counts, and base
  pair counts are distinct types.
- Biophysical nouns are `FoldbackJunction` and `BasalJunction`. Processing-route
  names describe operations; historical migration terms are not schema aliases.
- A plan is fully resolved and immutable. A bundle is content-addressed and
  must verify before consumption.
- Foldback pairing, basal pair classification, and strand-state projection are
  physical derivations. Caller selection thresholds, reserve acceptance, and
  application eligibility are separate explicit policy inputs.
- Renderers consume `WorkflowView`; they cannot derive or revise molecular
  state.
- Molecular sequence fields are serialized 5′→3′. Coordinate-aligned 3′→5′
  bottom tracks exist only in views.
- A resolved release product must equal its foldback precursor input. Route
  steps are contiguous and the plan source records the actual route input.
- Canonical junction pairs cover every aligned position, including wobble and
  mismatch calls. Feasibility policy does not alter the physical object.

## Error channels

Invalid schemas, alphabets, catalog references, coordinates, or internal
invariants raise immediately. Expected scientific infeasibility is represented
by a `CheckReport` with stable `Diagnostic` records so callers can receive all
independent findings at once.

Fail fast means rejecting invalid state at the boundary. It does not mean
returning one opaque error at a time or converting a programming failure into
an empty candidate set.

## Defaults

Biologically meaningful defaults are named, versioned, printed by the CLI, and
recorded in both the expanded spec and plan lock. The convenience sequence call
must remain observationally equivalent to compiling its expanded `HopSpec`.

## Change discipline

Add or change behavior with a failing contract test first. Preserve refactors
separately from semantic changes. A schema change requires an architecture
decision record, explicit compatibility posture, negative tests, and an update
to the reference docs.
