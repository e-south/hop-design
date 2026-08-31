---
doc_id: hop-plans-artifacts-bundles
title: Plans, artifacts, and bundles
intent: Explain the separate derivation and verification boundaries for design and method products.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: explanation
journey:
  - verify
  - integrate
---

# Plans, artifacts, and bundles

HOP has two plan types because declarative design derivation and temporal
molecular production are different authorities.

## Design compilation

```text
HopSpec or ResolvedHopSpec
    -> DesignDerivation
    -> HopPlan
    -> HairpinEncodingInsert
    -> HopBundle
```

The spec is authored intent. `HopPlan` is the immutable compiler result. It
derives the paired payload, evaluates selected components, partitions the
normalized encoding into typed features, and records how those design values
were derived. Its `design_derivation` owns no ordered production chronology. A
resolved design may preserve caller-asserted nick or release projection geometry,
but it makes no complete production-method claim.

Every design bundle contains:

```text
hop-bundle.json
hop-plan.json
hop-spec.json
provenance.json
hairpin-encoding.fasta
```

Explicit component designs also contain deterministic JSON and SVG review views.

## Method resolution

```text
MethodRequest
    -> exact molecular states and transitions
    -> MethodPlan
    -> destination-neutral product
    -> MethodBundle
```

A method plan is the only HOP object that owns temporal production history. Its
bundle records the exact request, complete plan, trajectory, modeled molecular
products, and derived exports. Replay does not establish that a molecule was
constructed or recovered.

## Verification

Bundle identifiers derive from manifest content. Verification checks paths and
inventory, validates every digest, reloads strict schemas, and reruns the
authoritative compiler. A resealed but semantically altered derived artifact is
rejected because replay must reproduce every stored byte.

Use `load_verified_bundle()` for a design bundle and
`load_verified_method_bundle()` for a method bundle. A consumer must preserve
the returned immutable object and its digests rather than reconstructing HOP
features.

## Cross-bundle relation

Design and method bundles do not share identity. When a method claims to
realize a design, the consumer checks equality of the design encoding digest
and the method product's encoding-projection digest. See
[provenance and verification](overview.md).
