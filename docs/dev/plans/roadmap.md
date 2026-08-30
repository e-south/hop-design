---
doc_id: hop-roadmap
title: HOP product roadmap
intent: Define public product capabilities, open pre-1.0 work, and evidence gates.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: explanation
journey:
  - maintain
---

# HOP product roadmap

## Product direction

HOP is a domain-specific language and compiler for sequence-encoded hairpins.
Its public roadmap is organized by the claim each surface makes, not by a
private consumer migration.

## Released foundation

The public `v0.1.0a7` artifact provides:

- exact and DNA IUPAC design compilation;
- strict payload, foldback, basal, paired-stem, coordinate, and feature models;
- bounded nick placement, precursor, basal, released-foldback, and junction
  discovery with truthful completion status;
- exact linear-source multi-nick, size-selection, adapter-ligation hairpin-PCR
  method compilation;
- separate replay-verified design and method bundles;
- deterministic JSON, FASTA, GenBank, typed views, and SVG outputs;
- clean wheel/sdist verification on Python 3.12–3.14.

## Current pre-1.0 semantic line

The current prerelease deliberately breaks the preceding alpha schemas and
public facade to close seven ontology and usability defects:

1. Pair kind becomes an invariant physical observation; policy cannot relabel
   G:T as a hard mismatch.
2. Design derivation owns no ordered production chronology; construction routes
   and named method plans own their respective molecular-state histories.
3. Foldback input includes an exact source-turn span.
4. Discovery uses `canonical_ordinal`, not an ambiguous `rank` field.
5. Restriction products contain exact cohesive-end objects while remaining
   destination-neutral.
6. The package root is the design-language golden path; bounded discovery,
   named methods, and views use explicit sibling facades.
7. First use is one bounded substrate space, one symbolic preview, and one
   complete verified digital design package through `hop_design.spaces`.

No retired schema reader, field alias, or artifact fallback is retained.

The current scientist surface is exhaustive or blocked. Sampled design sets,
large-set storage, pool-level method assessment, QC attachments, assay data,
and browser authoring remain outside this release until an experimental
handoff requires them.

`hop_design.methods.list_method_capabilities()` exposes every named method's
implementation availability and input exactness as a closed, immutable tuple.
It does not introduce a plugin registry, select a method, construct a request,
or change method resolution.

## Open product work

### Payload-centered construction discovery

The accepted semantic contract is
[ADR 0025](../../architecture/decisions/0025-payload-centered-construction-discovery.md).
Phase H1 is complete at the documentation layer: final-payload coordinates,
route and endpoint hierarchy, the shared local-neighborhood contract, explicit
foldback and basal meanings, endpoint compactness, staged state-aware
validation, lossless grouping, the linear-route boundary, and cross-repository
ownership are frozen before public schemas change.

The implementation remains organized in dependency order. H2 through H8 are
present in the current release:

1. **H2 — enzyme and operation semantics: implemented.** Vendor-neutral
   characterized enzymes, request provisioning, ordered reaction stages,
   concurrent operations, and state-aware active-site checks share one pure
   replay authority.
2. **H3 — shared local-neighborhood contract: implemented.** One bounded
   exact-first request/result envelope carries discrete relaxation shells,
   exact realization records, reversible geometry groups, and truthful
   completion.
3. **H4 — foldback neighborhood: implemented.** Exact cleavage programs
   discover junction offset, loop length, and annealing-arm geometry.
4. **H5 — basal neighborhood: implemented.** Nicking and pairing are
   endpoint-aware; Type IIS end generation is confined to clone-ready routes.
5. **H6 — materialization and composition: implemented.** Exact precursor and
   auxiliary materials compose through the bounded staged cross-product while
   preserving complete-realization and final-product identities.
6. **H7 — scientific projections: implemented.** Neutral tidy relations and
   deterministic SVGs expose local feasibility, relaxation, complete
   composition, and an explicitly selected exact trajectory without manuscript
   composition.
7. **H8 — public documentation and dogfood: implemented.** The narrow
   `hop_design.construction` facade, strict external source, portable bundle,
   opaque receipts, and reference contracts are present. Exact, infeasible,
   relaxed, and composed-PCR source-versus-installed-wheel dogfood provides the
   installed-artifact proof.

The current small `hop_design.spaces` journey is unchanged. Circularized-source
chemistry, thermodynamic and enzyme-performance prediction, study history,
experimental evidence, and manuscript assembly remain deferred or
consumer-owned.

The construction facade is not a second scientist quickstart. Its ten-name
allowlist accepts strict files and a separately verified design authority. Raw
construction models remain internal, and no compatibility alias exposes their
former or current internal paths.

### Bounded symbolic method assessment

Exact method compilation remains exact. A separate pool assessment must reason
over correlated DNA IUPAC domains and distinguish universally feasible,
possibly feasible, exhaustively infeasible, and truncated outcomes without
silently enumerating an unbounded pool.

### Bounded geometry ranges and named objectives

Discovery currently answers exact declared geometry questions. A range surface
may cover retained-tract, turn, and foldback-arm lengths. Any compactness choice
must be a named objective with visible measurements and deterministic
tie-breaking; neutral ordinals remain non-scores.

### Interoperability mappings

SBOL and PROV may project stable HOP objects and typed relations after consumer
demand is demonstrated. They do not drive or replace the internal ontology.

## Release gate

Every prerelease requires:

- contract-first negative and replay tests;
- complete local verification and Python-version CI;
- no unresolved high-severity correctness or information-architecture finding;
- wheel/sdist build, clean install, metadata, and source/wheel parity;
- protected-main tag ancestry and published SHA-256 checksums;
- no private application data or caller-repository dependency.

## Consumer adoption gate

A downstream system must install one immutable release artifact, load verified
bundles, preserve HOP features and digests without reconstruction, classify all
semantic differences, and pass its own hosted checks. Rollback is deployment of
a prior coherent revision and pin—not a runtime fallback.

Public HOP documentation records these generic gates. Consumer-specific status,
repository SHAs, infrastructure blockers, and migration evidence remain in the
owning system.
