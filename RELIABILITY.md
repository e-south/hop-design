---
doc_id: hop-reliability
title: HOP Design reliability contract
intent: Define determinism, integrity, limits, and degraded behavior.
audience:
  - maintainers
  - bundle consumers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# HOP Design reliability contract

## Determinism

The same normalized spec, compiler version, locked catalog/profile references,
and route must produce byte-identical artifacts, plan digest, manifest digest,
plan ID, and bundle ID. Canonical JSON is UTF-8, key-sorted, compact, and ends
with one newline. FASTA uses deterministic headers, 80-column sequence lines,
and one trailing newline. Host paths, timestamps, usernames, and environment
ordering do not enter content identity.

## Bundle integrity

`hop-bundle.json` inventories every content artifact except itself. Each entry
records a normalized relative path, media type, byte count, and SHA-256 digest.
Verification rejects missing, symlinked, modified, unmanifested, path-traversing,
or root-digest-inconsistent content. It also loads the strict spec, plan, and
provenance schemas; checks their identities and locked references against each
other; then deterministically recompiles the spec and requires the complete
plan, artifact set, and manifest to match. This replay catches a consistently
resealed bundle whose authored intent and derived state disagree. Writes use a
sibling temporary directory, verify it, then rename it atomically. Existing
output paths are never replaced.

## Limits

Every spec has an explicit positive candidate bound. The convenience route
resolves exactly one generic design. Foldback enumeration reports `complete`,
`infeasible`, or `truncated`, including the fired node or hit bound; a truncated
search is never presented as complete. Nicking-placement discovery evaluates at
most `max_search_nodes` caller-owned catalog entries and returns at most
`max_hits`. Its result distinguishes an incomplete catalog search from a
complete search whose returned hit list was bounded; both conditions produce an
explicit `truncated` status. Symbolic expansion calculates exact
cardinality before allocation, raises when it exceeds `max_variants`, and never
truncates silently. Design-space planning likewise calculates the full payload
by foldback by basal by release Cartesian cardinality before allocating rows and
fails above `max_designs`.

Resolved release and foldback requests cannot be evaluated as one route unless
their adjacent sequence states are identical. Release scanners discard any
resolved top or bottom cut beyond the supplied sequence. Search result models
reject terminal statuses that contradict hits or the number of examined nodes.
A release event cannot enter component assembly without a terminal nick.
Component assembly emits the final insert as its source oligo and route-neutral
views; it never fills missing route fields from a catalog search or default.

## Degraded modes

There is no permissive fallback for an unknown schema, catalog reference,
profile, route, or corrupted bundle. The built-in SVG renderer has no plotting
dependency and consumes only a typed workflow view. Optional future renderers
may be absent without blocking the typed plan, but they may not recompute
molecular state.
External observations may be unavailable without invalidating a prospective
HOP bundle because execution evidence is caller-owned.
