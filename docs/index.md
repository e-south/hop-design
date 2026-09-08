---
doc_id: hop-docs-index
title: HOP documentation
intent: Find a starting example, a molecular task guide, or the relevant API and file reference.
audience:
  - users
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-09-08
doc_type: index
journey:
  - install
  - compile
  - discover
  - method
  - verify
  - integrate
---

# HOP documentation

Choose the task you need. Use the CLI to compile designs, preview sequence
spaces, and inspect saved constructions. Use Python to search junctions and
compile construction routes.

## Start here

1. [Install and compile](guides/quickstart.md) a first design.
2. [Define a substrate space](guides/substrate-spaces.md) with fixed and variable positions.
3. [Understand the construction](start/mental-model.md): payload, local junctions,
   materials, and processing steps. [Why HOP](start/why-hop.md) explains the design question.

## Work on a construction

- [Search junctions and compile a construction](guides/compile-construction.md):
  payload, enzymes, local constraints, required materials, and endpoint.
- [Search compatible basal candidates](guides/discover-compatible-basal-candidates.md):
  a runnable bounded query. See [search interpretation](discovery/overview.md)
  for coverage, feasibility, and ordering.
- [Find a fragment-removal program](guides/discover-source-partitions.md):
  which nickase combinations leave the required fragments after separation?
- [Check exact materials through a named method](guides/resolve-production-method.md):
  molecular states and products, explained in the [method model](methods/overview.md).
- [Render molecular views](guides/render-component-views.md) and
  [verify saved results](provenance/overview.md).

## Inputs and reference

- [Payload files and expansion](guides/payload-sources-and-expansion.md) and
  [degenerate bases](guides/degenerate-payloads.md).
- [Design anatomy](language/overview.md), [terms](language/ontology.md), and
  [pairing rules](language/relationships-and-invariants.md).
- [CLI](reference/cli.md), [Python API](reference/python-api.md), and
  [component calculations](reference/mechanics-api.md).
- [Material requirements](reference/linear-source-method-materials.md) and
  [view formats](reference/view-contracts.md).
- [Design files](reference/bundle-layout.md),
  [construction files](reference/construction-bundle-layout.md),
  [method files](reference/method-bundle-layout.md), and [schemas](reference/schemas.md).
- [Downstream integration](ecosystem/ownership-boundaries.md).

## Contribute

[Contributor instructions](../CONTRIBUTING.md) and the [maintainer map](dev/README.md)
cover implementation, verification, and releases.
