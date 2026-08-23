---
doc_id: hop-concepts-index
title: HOP Design concept map
intent: Route readers through hairpin anatomy, discovery, and processing boundaries.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
---

# HOP Design concept map

HOP separates the object being designed from the method used to produce it and
from the destination where it will be assembled.

1. [Hairpin components](hairpin-components.md) explains what the payload,
   foldback junction, basal junction, and compiled products are.
2. [Discovery and selection](discovery-and-selection.md) explains what HOP can
   search, what its ordering means, and where caller policy begins.
3. [Processing and assembly](processing-and-assembly.md) explains how molecular
   states change and why destination assembly remains a separate decision.

Use the [ontology](../ontology.md) when an exact schema term matters and the
[mechanics API](../reference/mechanics-api.md) when implementing against a
specific operation.
