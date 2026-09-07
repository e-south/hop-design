---
doc_id: hop-reliability
title: HOP Design reliability contract
intent: Define determinism, integrity, limits, and degraded behavior.
audience:
  - maintainers
  - bundle consumers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-31
doc_type: reference
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

`method-bundle.json` applies the same safe-path, complete-inventory, digest,
atomic-write, and no-overwrite rules to a method request and plan. Verification
parses both strict schemas, recompiles the request, and requires the plan,
trajectory, FASTA, GenBank, artifact inventory, manifest digest, and bundle ID
to match byte for byte. A checksum-valid reseal of one generated artifact is
therefore rejected.

`construction-bundle.json` inventories one exact complete-construction result
and every byte of the separately verified design bundle embedded below
`authorities/design/`. Verification checks the root result and manifest
digests, construction and design identities, exact artifact inventory, and
safe paths. It then semantically replays the design authority, each embedded
foldback and optional basal authority, whole-route composition, reaction-site
assessment, endpoint products, disposition accounting, rejection reasons, and
grouping. Finally, it recompiles the expected construction bundle and requires
exact artifact and manifest equality. Construction-bundle and projection
writes are atomic and create-only.

A hairpin design set inventories its normalized per-position molecular domains,
resolved hairpin defaults reference, and every byte of every unique member
bundle below `bundle/`. Verification recomputes collection identity, replays
canonical space enumeration, and semantically replays each member. Display
names, descriptive context, segment labels and boundaries, allocation bounds,
and the HTML, CSV, FASTA, and YAML projections do not enter collection identity.
Collection compilation stages authority and projections together and atomically
commits only after complete verification.

The design-set manifest records independent claim statuses for complete space
accounting, replay-verified digital designs, method and destination questions
not evaluated by the package, and construction, quality-control, and activity
evidence not recorded by the package. Verification rejects absent, unknown, or
altered status literals. Human projections render this matrix from the verified
manifest rather than maintaining a second claim authority.

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

A substrate-space preview computes cardinality arithmetically before member
allocation. The scientist surface compiles through its tested 256-design
release envelope. A valid larger space is `blocked`; compilation writes
nothing. V1 does not truncate or publish partial authoritative sets.

Basal candidate discovery calculates the exact left-arm by right-arm IUPAC
cardinality before evaluation. It examines at most `max_search_nodes`, returns
at most `max_hits`, reports reserve and reject exclusions for every examined
non-hit, and distinguishes node truncation from result truncation. Candidate
identity covers the exact pairing request and complete evaluation; result
validation rejects domain, accounting, canonical-ordinal, and order drift.

Payload-centered foldback and basal neighborhood discovery traverses finite
geometry, strand, payload, and enzyme-program domains in ascending absolute
retained-overhead order. Each examined level accounts for candidates as
accepted plus rejected and partitions rejections by observed primary failure
category. Only the final recorded level may be partial. Completion is separate
from feasibility: an exhausted domain is `complete` with either `feasible` or
`infeasible` existence status; an evaluation cap is `truncated`, and an explicit
quota is `stopped_by_policy`. An existence query preserves a witness for each
accessible local work unit without claiming all exact realizations were
enumerated. Projection verification rebuilds level membership and accounting
from the exact source result, so a checksum-consistent subset, reordering, or
extra row is rejected.

Complete construction composition computes the nominal local Cartesian
cardinality before evaluation, examines only its canonical bounded prefix, and
records accepted plus rejected dispositions for every examined combination.
Selected-pair composition instead records the explicit foldback and basal
selection in the request and evaluates exactly that one replay-verified pair;
absent selection fields do not alter exhaustive compilation bytes.
`complete` and `infeasible` require full nominal exhaustion; `truncated`
requires an exact local or composition reason. Accepted realizations remain
separately identifiable even when achieved-geometry or final-product groups
coincide. A trajectory projection requires an explicit accepted realization
identity and never treats canonical order as preference.

Basal processing-geometry discovery evaluates at most `max_search_nodes`
nicking agents and returns at most `max_hits`. Every examined agent has one
feasibility row. The result validator requires full node-budget exhaustion,
exact compatible-hit accounting, canonical agent order, content-addressed hit
projection, and distinct node/hit truncation. Signed release/nick coordinates
remain local geometry; concrete molecular spans remain nonnegative.

Basal processing-route composition evaluates the canonical Cartesian product
of the returned basal candidates and returned processing geometries. It reports
upstream basal or geometry truncation separately from its own node and hit
bounds. `available_pair_count` describes that returned cross-product, not an
unobserved global search space. HOP computes that count arithmetically and does
not allocate pairs beyond the node budget. Every feasibility row and returned
route replays its embedded inputs, retained scar, terminal nick, surviving
strand, content identity, canonical ordinal, and order.

Released-foldback geometry discovery calculates the full agent-pair by release-
orientation by boundary-window cardinality without materializing that product.
It consumes nodes only through `max_search_nodes`, returns hits only through
`max_hits`, and reports either bound explicitly. Validation replays every
examined recognition footprint, cut, foldback pair domain, sequence-space
cardinality, hit identity, canonical ordinal, and order from the embedded catalog and request.
It never reports an unexamined concrete sequence.

Released-foldback precursor search calculates the exact intersection of one
selected geometry and one caller-authored IUPAC template before allocation.
Correlated foldback pairs count as one axis. `max_search_nodes` bounds exact
sequences examined and `max_hits` independently bounds returned candidates;
both limits are replayed from the embedded request. A zero intersection is
explicitly infeasible, and result validation rejects sequence, digest, content
identity, canonical ordinal, order, accounting, or truncation drift.

Resolved release and foldback requests cannot be joined unless
their adjacent sequence states are identical. Release scanners discard any
resolved top or bottom cut beyond the supplied sequence. Search result models
reject terminal statuses that contradict hits or the number of examined nodes.
A release projection cannot enter resolved-junction derivation without a terminal nick.
Component evaluation emits the one-dimensional hairpin-encoding sequence and
produces route-neutral views; it never fills missing method fields from a
catalog search or default.
An absent paired stem extension is omitted from serialized v2 design specs.
When present, its arms, pair calls, two feature spans, and state transition must
all agree. Method-material plans reject terminal-binding or chemistry drift.

## Degraded modes

There is no permissive fallback for an unknown schema, catalog reference,
profile, route, source endpoint, or corrupted bundle. Construction sources are
bounded regular nonsymlink JSON/YAML mappings read through one checked file
descriptor. Duplicate keys and YAML aliases, anchors, and merge keys are
rejected before model validation. Sources dispatch only the exact
`hop.construction-source/v5` schema; the design authority is loaded from a
separate verified bundle path. Each accepted route replays its declared source
ssDNA and two source-preparation primers into the exact duplex that seeds
downstream construction. For PCR-bearing endpoints, a separate policy resolves
the adapter and two endpoint primers in `derive`, `constrain`, or `fixed` mode.
Derived and constrained primers bind invariant construction sequence outside
the payload; constrained reusable handles are caller-authored, not silently
generated or ranked. Direct ssDNA-hairpin routes reject endpoint auxiliaries.
When composition binds a selected replay-verified source partition, route
verification replays its prepared duplex, enzyme definitions, concurrent nick
program, inclusive fragment rule, and required survivors. The built-in SVG
renderer has no plotting dependency and consumes only a typed workflow view.
Optional future renderers may be absent without blocking the typed plan, but
they may not recompute molecular state.

Standalone local-neighborhood requests retain the one-megabyte authored-source
limit and may declare at most 100,000 search nodes and 100,000 realizations.
Portable local-neighborhood results have a separate 64 MiB envelope because
they contain bounded candidate, rejection, and replay evidence. The loader
checks embedded execution bounds before semantic replay. A larger study must
narrow its declared search or use every member of a deterministic, disjoint
sequence-domain partition. Each part remains independently replayable and
cannot claim whole-domain payload compatibility; the loader never treats an
oversized result as a partial authority.
External observations may be unavailable without invalidating a prospective
HOP bundle because execution evidence is caller-owned.
