---
doc_id: hop-roadmap
title: HOP product roadmap
intent: Define public product capabilities, open pre-1.0 work, and evidence gates.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
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

The public `v0.1.0a6` artifact provides:

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

The next prerelease candidate deliberately breaks the alpha schemas and public
facade to close six ontology and usability defects:

The local package version for this candidate is `v0.1.0a7`; it is not a
published artifact until the release gate below passes.

1. Pair kind becomes an invariant physical observation; policy cannot relabel
   G:T as a hard mismatch.
2. Design derivation owns no ordered production chronology; only named method
   plans own molecular-state history.
3. Foldback input includes an exact source-turn span.
4. Discovery uses `canonical_ordinal`, not an ambiguous `rank` field.
5. Restriction products contain exact cohesive-end objects while remaining
   destination-neutral.
6. The package root is the design-language golden path; bounded discovery,
   named methods, and views use explicit sibling facades.

No retired schema reader, field alias, or artifact fallback is retained.

`hop_design.methods.list_method_capabilities()` exposes every named method's
implementation availability and input exactness as a closed, immutable tuple.
It does not introduce a plugin registry, select a method, construct a request,
or change method resolution.

## Open product work

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
