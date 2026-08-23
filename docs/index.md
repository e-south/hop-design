---
doc_id: hop-docs-index
title: HOP documentation
intent: Route readers through HOP's design, discovery, method, provenance, and ecosystem surfaces.
audience:
  - users
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
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

HOP is a domain-specific language and compiler for sequence-encoded hairpins.
Follow the shortest route that answers your question. The CLI supports the
common design-compilation path; discovery, method resolution, and typed
integration use Python.

## Start here

1. **Why HOP:** [Why HOP](start/why-hop.md) explains the product's narrow-waist role.
2. **Mental model:** [Five claims HOP keeps separate](start/mental-model.md)
   establishes the boundary between sequence identity, method support,
   destination fit, and experimental success.
3. **Install and compile:** [Quickstart](guides/quickstart.md) covers exact and
   symbolic input, persisted output, and verification.
4. **Design language:** [Language overview](language/overview.md) introduces the
   small public vocabulary and routes to the formal ontology.
5. **Discovery language:** [Discovery overview](discovery/overview.md) explains
   bounded competency questions; [the discovery guide](guides/discover-compatible-basal-candidates.md)
   runs one complete and one truncated query.
6. **Method language:** [Method overview](methods/overview.md) separates exact
   molecular chronology from declarative design derivation; [the method guide](guides/resolve-production-method.md)
   writes and verifies one method bundle.
7. **Verify and inspect:** [Provenance and verification](provenance/overview.md)
   runs the matched `examples/verify_design_method_handoff.py` journey and
   routes to the [design-bundle](reference/bundle-layout.md),
   [method-bundle](reference/method-bundle-layout.md), and
   [view](reference/view-contracts.md) contracts.
8. **Integrate:** [Ownership boundaries](ecosystem/ownership-boundaries.md)
   defines what remains caller-owned and how broader campaign systems can call HOP.

## Five sibling surfaces

- [Design language](language/overview.md): anatomy, authored inputs, derived
  relationships, invariants, and deterministic encoding.
- [Discovery language](discovery/overview.md): deterministic bounded queries,
  candidate identity, completeness, and neutral order.
- [Method language](methods/overview.md): exact materials, molecular states,
  transformations, products, and capability status.
- [Provenance and verification](provenance/overview.md): bundle identity,
  semantic replay, digests, and typed handoff relations.
- [Ecosystem](ecosystem/ownership-boundaries.md): campaign orchestration,
  placement, assessment, studies, execution, and observations.

## Guides and reference

- [Degenerate payloads](guides/degenerate-payloads.md): DNA IUPAC preservation
  and explicit expansion budgets.
- [Payload sources and expansion](guides/payload-sources-and-expansion.md):
  iterables, FASTA, CSV, duplicate policy, and concrete variants.
- [CLI](reference/cli.md) and [Python API](reference/python-api.md).
- [Mechanics API](reference/mechanics-api.md): foldback, basal, release,
  discovery, and caller-supplied processing catalogs.
- [Linear-source method materials](reference/linear-source-method-materials.md):
  declared oligos, terminal chemistry, and binding checks.
- [Schema identifiers](reference/schemas.md), [formal ontology](language/ontology.md),
  and [relationships and invariants](language/relationships-and-invariants.md).

## Maintain

- [Maintainer map](dev/README.md) routes governance, release, and migration work.
- [Architecture](../ARCHITECTURE.md), [engineering contracts](../DESIGN.md),
  [reliability](../RELIABILITY.md), and [security](../SECURITY.md) are the root
  authorities.
- [Roadmap](dev/plans/roadmap.md) defines phased proof of done.
- [Architecture decisions](architecture/decisions/) record costly choices.
