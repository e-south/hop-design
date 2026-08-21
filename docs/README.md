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
last_verified: 2026-08-20
---

# HOP Design documentation map

Start at the shallowest layer that answers the task.

## Use the product

- [Quickstart](guides/quickstart.md): compile exact and symbolic sequences.
- [Degenerate payloads](guides/degenerate-payloads.md): understand DNA IUPAC
  preservation and explicit expansion budgets.
- [Payload sources and expansion](guides/payload-sources-and-expansion.md):
  compose iterables, FASTA, CSV, duplicate policy, and concrete variants.
- [CLI reference](reference/cli.md): current commands and failure behavior.
- [Python API](reference/python-api.md): stable public facade.
- [Mechanics API](reference/mechanics-api.md): foldback, basal, release, and
  caller-supplied processing catalog contracts.
- [View contracts](reference/view-contracts.md): renderer-independent workflow
  views and deterministic SVG output.
- [Schema identifiers](reference/schemas.md): strict version dispatch and
  compatibility behavior.
- [Bundle layout](reference/bundle-layout.md): consume and verify outputs.

## Understand the domain

- [Ontology](ontology.md): the smallest public vocabulary.
- [Processing method boundary](processing-method-boundary.md): the concrete
  source-to-insert method scope, current coverage, and caller boundary.
- [Spec, plan, and bundle](spec-plan-bundle.md): ownership across the product
  spine.
- [Contract table](contracts.md): preconditions and guarantees.

## Change the product

- [Maintainer map](dev/README.md) routes governance, release, and migration work.
- [Architecture](../ARCHITECTURE.md), [engineering contracts](../DESIGN.md),
  [reliability](../RELIABILITY.md), and [security](../SECURITY.md) are the root
  authorities.
- [Roadmap](dev/plans/roadmap.md) defines phased proof of done.
- [Architecture decisions](architecture/decisions/) record costly choices.
