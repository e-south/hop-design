---
doc_id: hop-design-contracts
title: HOP Design engineering contracts
intent: State non-negotiable invariants, error channels, and change rules.
audience:
  - maintainers
  - API consumers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
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
- Catalog discovery and molecular compilation are separate operations.
  Discovery reports physical placement facts and explicit truncation; caller
  selection policy cannot silently become HOP rank.
- Basal candidate discovery enumerates only caller-authorized IUPAC arm domains.
  Returned order is a canonical physical record order; profile preference,
  control distance, procurement, and agent eligibility remain separate caller
  decisions.
- Basal processing geometry separately intersects release, terminal-nick,
  retained-scar, and explicit post-nick domains in signed cut-relative
  coordinates; it does not infer a downstream degeneracy rule.
- Basal processing-route composition joins exact basal candidates to exact
  processing geometries only when the basal left arm is an allowed retained
  scar and does not retain the selected release site. It preserves upstream
  incompleteness, returns all bounded compatible joins in neutral order, and
  does not select an enzyme or assert released-foldback continuity.
- Released-foldback geometry discovery evaluates the bounded nick-agent by
  release-agent by orientation by boundary product. It returns correlated
  sequence domains and their exact cardinality without allocating a concrete
  precursor or applying warning, vendor, or study rank.
- Component assembly and processing-route compilation are separate claims.
  Supplied components may be evaluated and composed without asserting their
  discovery method, enzyme route, nicked strand, or historical lineage.
- Optional paired stem extensions remain separate from both the four-position
  basal junction and the authored payload. Literal extension arms may preserve
  noncanonical pairs; the paired payload remains derived.
- Process materials are distinct from molecular states. Terminal binding and
  ligation-end chemistry must be explicit before a material is reported as
  route-ready.

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
