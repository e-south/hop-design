---
doc_id: hop-processing-and-assembly
title: Method language overview
intent: Route readers through named molecular methods without conflating design, production, or destination assembly.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: explanation
journey:
  - method
  - integrate
---

# Method language overview

The method language answers one question: what exact molecular states follow
from one named method request? It is a sibling of design compilation, not a
later phase hidden inside a design plan.

```text
MethodRequest -> exact states and transitions -> destination-neutral product
```

Keep these claims separate:

- a valid hairpin design does not imply that a production method is available;
- an available method does not imply that one request resolves;
- a complete method result does not imply destination compatibility;
- a compatible destination does not imply experimental success.

`hop_design.methods.list_method_capabilities()` reports which named method
families this HOP version implements and their defined input exactness. Current
records distinguish `exact_only` from `not_defined`; they do not imply symbolic
method support. The query does not construct a request, select a method, or
predict feasibility.

## Follow the task you have

- [Hairpin-processing method boundary](destination-neutrality.md) defines the
  detailed state trajectory, capability facets, materials, outputs, and
  non-claims.
- [Resolve and verify a production method](../guides/resolve-production-method.md)
  shows both explicit request authoring and canonical JSON replay.
- [Linear-source method materials](../reference/linear-source-method-materials.md)
  defines the six required oligos and terminal-chemistry checks.
- [Method-bundle layout](../reference/method-bundle-layout.md) defines persisted
  artifacts and semantic replay.
- [Provenance and verification](../provenance/overview.md) shows the
  caller-owned digest equality between separate design and method bundles.

## Boundary

HOP records exact sequence-bearing states, transitions, terminal chemistry,
pairing, bonds, cuts, and lineage. It does not simulate yield, kinetics,
cleanup recovery, PCR side products, or experimental success. A produced
cohesive end remains destination-neutral until a caller checks it against a
specific assembly context.
