---
doc_id: hop-docs-index
title: HOP Design documentation map
intent: Route readers from product concepts to contracts, guides, and internals.
audience:
  - users
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
---

# HOP Design documentation map

Follow the shortest journey that answers the question. The CLI supports design
compilation; discovery, method resolution, and typed integration use Python.

## Start here

1. **Install and compile:** [Quickstart](guides/quickstart.md) covers exact and
   symbolic input, persisted output, and verification.
2. **Understand the components:** [Hairpin components](concepts/hairpin-components.md)
   distinguishes payload, foldback, basal junction, and physical products.
3. **Understand discovery and selection:** [Discovery and selection](concepts/discovery-and-selection.md)
   explains bounded geometry search, IUPAC domains, ordering, and caller policy.
4. **Understand method resolution:** [Processing and assembly](concepts/processing-and-assembly.md)
   separates molecular events, pair geometry, ligation evidence, and destination
   assembly.
5. **Verify and inspect:** use the [design-bundle](reference/bundle-layout.md),
   [method-bundle](reference/method-bundle-layout.md), and
   [view](reference/view-contracts.md) contracts.
6. **Integrate:** [Spec, plan, and bundle](spec-plan-bundle.md) explains the
   immutable consumer boundary; the [processing method boundary](processing-method-boundary.md)
   defines what remains caller-owned.

## Concepts

- [Concept map](concepts/README.md): plain-language routing by domain question.
- [Ontology](ontology.md): canonical public terms and strict type meanings.
- [Contract table](contracts.md): preconditions and guarantees.
- [Degenerate payloads](guides/degenerate-payloads.md): DNA IUPAC preservation
  and explicit expansion budgets.
- [Payload sources and expansion](guides/payload-sources-and-expansion.md):
  iterables, FASTA, CSV, duplicate policy, and concrete variants.

## Reference

- [CLI](reference/cli.md) and [Python API](reference/python-api.md).
- [Mechanics API](reference/mechanics-api.md): foldback, basal, release,
  discovery, and caller-supplied processing catalogs.
- [Linear-source method materials](reference/linear-source-method-materials.md):
  declared oligos, terminal chemistry, and binding checks.
- [Schema identifiers](reference/schemas.md): strict version dispatch.

## Maintain

- [Maintainer map](dev/README.md) routes governance, release, and migration work.
- [Architecture](../ARCHITECTURE.md), [engineering contracts](../DESIGN.md),
  [reliability](../RELIABILITY.md), and [security](../SECURITY.md) are the root
  authorities.
- [Roadmap](dev/plans/roadmap.md) defines phased proof of done.
- [Architecture decisions](architecture/decisions/) record costly choices.
