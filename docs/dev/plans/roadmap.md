---
doc_id: hop-roadmap
title: HOP product roadmap
intent: Distinguish released capabilities, source capabilities, and remaining product work.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-09-07
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

The published `v0.1.0a8` artifact provides:

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

The published `v0.1.0a8` line deliberately breaks the preceding alpha schemas
and public facade to close seven ontology and usability defects:

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

## Source capabilities

The source checkout extends the published artifact. Its retained-overhead
contracts and query checkpointing require a distinct release version before
artifact consumers can adopt them. Use the tagged documentation with a released
wheel; do not infer source capabilities from the shared alpha version string.

The [construction guide](../../guides/compile-construction.md) exposes:

- Foldback search in increasing retained-overhead order, with explicit geometry
  bounds, physical strand actions, coverage, and witness or all-realizations scope.
- Profile-free local basal search with proximal pairing, adapter-completion
  obligations, and state-indexed future-release constraints.
- Source-partition search over enzyme programs on an exact supplied duplex,
  including terminal fragments and inclusive maximum-fragment certificates.
- Composition of selected local authorities, source preparation, optional
  source-partition evidence, exact auxiliaries, and endpoint-specific chronology.
- Replay-verified portable results, lossless geometry grouping, tidy relations,
  and typed molecular projections. CLI navigation selects existing results;
  discovery and compilation use the public Python facade.
- Checkpointed collections of independent local queries. Batch size controls
  receipt retention without changing individual result identities.

The [implementation inventory](retained-overhead-construction-inventory.md)
locates these responsibilities and their allocation measurements.

The current small `hop_design.spaces` journey is unchanged. Circularized-source
chemistry, thermodynamic and enzyme-performance prediction, study history,
experimental evidence, and manuscript assembly remain deferred or
consumer-owned.

The construction facade is not a second scientist quickstart. Its exact
allowlist accepts strict files and a separately verified design authority. Raw
construction models remain internal, and no compatibility alias exposes their
former or current internal paths.

## Remaining product work

### Bounded scaffold completion

Source-partition search currently evaluates a supplied exact source. It does
not derive a full scaffold across a bounded sequence/context domain while
satisfying local junction, primer, and adapter obligations. That solver is
required before claiming automatic global scaffold completion.

### Resumption within one local query

Checkpoints persist completed independent queries. A local query still assembles
its result in memory; partial-query coverage and realization streaming are not
persisted. Collection resumption does not remove this limit or make a truncated
query exhaustive.

### Bounded symbolic method assessment

Exact method compilation remains exact. A separate pool assessment must reason
over correlated DNA IUPAC domains and distinguish universally feasible,
possibly feasible, exhaustively infeasible, and truncated outcomes without
silently enumerating an unbounded pool.

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

A downstream system installs one immutable release artifact and preserves
verified features and identities without reconstructing molecular facts. Its
execution, review, and evidence policy remain independent of HOP's release gate.
Rollback is deployment of a prior coherent revision and pin, not a runtime fallback.

Public HOP documentation records these generic gates. Consumer-specific status,
repository SHAs, infrastructure blockers, and migration evidence remain in the
owning system.
