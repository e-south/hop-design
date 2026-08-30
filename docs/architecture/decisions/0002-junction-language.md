---
doc_id: hop-adr-0002
title: ADR 0002 - Canonical junction language
intent: Record the public molecular terms and migration-only vocabulary.
audience:
  - users
  - maintainers
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
amended_by: hop-adr-0026
---

# ADR 0002: Canonical junction language

> Amended by [ADR 0020](0020-separate-design-derivation-from-method-chronology.md)
> and [ADR 0026](0026-compose-complete-construction-chronology.md): design
> derivations no longer use a `ProcessingRoute` or own ordered chronology;
> construction routes and named methods own their respective molecular
> histories.

## Context

Predecessor tools named whole molecular deliverables after particular process
routes. Those labels obscure which part of the resulting hairpin they describe.

## Decision

The public biophysical nouns are `foldback_junction` and `basal_junction`.
`turn` is only the short unpaired portion of a foldback junction. Process names
belong to `ProcessingRoute`; historical labels are migration vocabulary and are
not accepted schema aliases.

## Consequences and reversal cost

Models, errors, docs, and plots share one molecule-centered ontology. Migration
requires an explicit one-way mapping. Renaming after schema v1 would be a public
breaking change, so this decision is intentionally fixed before route parity.
