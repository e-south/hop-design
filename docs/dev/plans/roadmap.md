---
doc_id: hop-roadmap
title: HOP product roadmap
intent: Distinguish released capabilities, source capabilities, and remaining product work.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-10-09
doc_type: explanation
journey:
  - maintain
---

# HOP product roadmap

## Product direction

HOP is a domain-specific language and compiler for sequence-encoded hairpins.
Its public roadmap is organized by the claim each surface makes, not by a
private consumer migration.

## Candidate and published scope

The source checkout is the unreleased `v0.1.0a9` candidate. Its implemented
workflows include complete scaffold discovery, stage-specific comparisons,
terminal hairpin requirements and explicit material reuse. Public publication
remains pending; a version label alone does not identify a tested source tree.

The candidate also includes [folded-sequence editing](../../guides/edit-folded-sequences.md):
exact loops, finite released-end placements and explicit method alternatives,
shared CLI/API retrieval, a local editor, and bounded exact expansion of a
degenerate stem. These operate on modeled preparations. Unrestricted nucleotide
editing, new chemistry, RNA prediction, destination validation, global optimization
and pooled-library guarantees remain outside that increment.

[Conditional variant exploration](../../guides/explore-conditional-variants.md)
adds browsing over admitted complete results: neighborhood choices narrow whole
products under fixed references and stage-qualified controls. The API, CLI and
single-molecule viewport share the query model; retrieval rechecks its constraints.
Repeated queries use immutable facts, while search expansion and control relaxation
remain explicit, separate operations. This is a source-candidate capability.

The construction-envelope navigator adds paged permitted domains, including words
and geometries without completed preparations. Field-bound permission revisions
are previewed before explicitly bounded evaluation; replay retains the original
pool and the declared changes. The shared CLI/API/browser contract keeps the
supplied stem, receiving ends, material policies and preservation controls fixed.
The public open-domain example separates molecular permissions from computation
quotas. This does not establish exhaustive satisfiability or a jointly optimized
experimental family. See [ADR 0051](../../architecture/decisions/0051-explicit-envelope-revisions.md).

Continuous molecular inspection keeps variant choice, processing state and camera
movement independent. Stage-qualified surroundings controls narrow supported
variants. Persistent recognition footprints and active cuts have separate
projections; verified correspondence follows a position while retaining copying,
material ancestry and ambiguity. Static SVG exports and the viewport consume the
same scene. Motion depicts correspondence between recorded states, not reaction
dynamics or predicted physical conformation.

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

## Published design-language contract

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

The published substrate-space surface is exhaustive or blocked. Sampled design sets,
large-set storage, pool-level method assessment, QC attachments, assay data,
and browser authoring remain outside this release until an experimental
handoff requires them.

`hop_design.methods.list_method_capabilities()` exposes every named method's
implementation availability and input exactness as a closed, immutable tuple.
It does not introduce a plugin registry, select a method, construct a request,
or change method resolution.

## Source capabilities

The source checkout extends the published artifact under candidate version
`0.1.0a9`. Retained-overhead contracts, query checkpointing and request execution
require its matching artifact. Use tagged documentation with the published
`0.1.0a8` wheel; a prepared candidate is not evidence of public availability.

The [construction guide](../../guides/compile-construction.md) exposes:

- Foldback search in increasing retained-overhead order, with explicit geometry
  bounds, physical strand actions, coverage, and witness or all-realizations scope.
- Profile-free local basal search with proximal pairing, adapter-completion
  obligations, and state-indexed future-release constraints.
- Source-partition search over enzyme programs on an exact supplied duplex,
  including terminal fragments and inclusive maximum-fragment certificates.
  The source and required survivors can also be derived from one selected
  construction or an examined PCR-bearing combination, with caller-supplied
  enzyme and fragment policies. A cleanup program can then be bound during
  full-route compilation; rejected candidates are not silently accepted.
- Composition of selected local authorities, source preparation, optional
  source-partition evidence, exact auxiliaries, and endpoint-specific chronology.
  PCR-bearing routes incorporate the selected cleanup nick program before
  actionable-site assessment and preserve the exact local joining strands.
  Required adapter annealing is completed against available invariant source
  bases and replayed position by position; insufficient source sequence or an
  incompatible fixed adapter rejects that exact composition.
- Bounded upstream sequence completion for PCR-bearing endpoints. A caller-supplied
  IUPAC context is enumerated without changing either local junction; each assignment
  must satisfy source preparation, adapter pairing, primer binding, and route checks.
  The [construction guide](../../guides/compile-construction.md) defines orientation,
  limits, and exact-versus-truncated accounting.
- Replay-verified portable results, lossless geometry grouping, tidy relations,
  and typed molecular projections. Saved-route navigation selects existing
  results; specialist local compilation uses the public Python facade, while
  product-request workflows also have CLI entrypoints.
  End-focused inspection shares one CLI/API reader for an exact released word,
  optional base position, recorded material origins and release cuts.
- Checkpointed collections of independent local queries. Batch size controls
  receipt retention without changing individual result identities.

The [implementation inventory](retained-overhead-construction-inventory.md)
locates these responsibilities and their allocation measurements.

The current small `hop_design.spaces` journey is unchanged. Circularized-source
chemistry, thermodynamic and enzyme-performance prediction, study history,
experimental evidence, and manuscript assembly remain deferred or
consumer-owned.

The [construction journey](../../guides/design-a-construction.md) provides an
end-to-end walkthrough for users seeking a molecular preparation. The facade accepts strict files and
a separately verified design authority; raw construction models remain internal.
The [usability priorities](construction-user-journey.md) distinguish current
handoffs from remaining authoring work. The public-input walkthrough and
opt-in bounded request executor are implemented in the candidate; a graphical
freeform request authoring surface is outside these workflows. The local viewport
chooses among supported complete designs through the same constrained API.

## Implemented product workflows in the source candidate

### Complete product options before selection

[Complete scaffold exploration](../../guides/explore-scaffolds.md), controlled-set
grouping and explicit label retrieval are implemented in the local candidate.
The [delivery plan](scaffold-options.md) records acceptance and verification.
The same comparison intent carries shared controls through selection. New
molecular capabilities, joint search beyond the evaluated pool and persisted
continuation resumption remain separate work.

### Product-driven preparations

[Desired scaffold dimensions](../../guides/discover-product-scaffolds.md) now drive
explicitly permitted adapter and release-method branches in the local candidate.
Exact stage grouping distinguishes hairpins from alternative preparations of one
released product. [Acceptance and verification](product-first-discovery.md) remain
with the delivery plan. This does not add joint molecular optimization or new chemistry.

### Explicit comparative sets

The [comparison brief](../../guides/specify-a-comparison.md) names required
members, shared properties and permitted preparation changes. Its versioned
grouped form requires identical stage products within scaffold groups and
different products between groups. Verified prior-product references and exact
loop words retain their molecular meaning through discovery and retrieval.
The [grouped-comparison plan](grouped-comparisons.md) owns delivery verification.
These operations do not establish experimental equivalence or public release.

### Terminal forms, stage controls and prior-material reuse

The [terminal-scaffold delivery plan](terminal-scaffold-comparisons.md) records
high-level unpaired terminal requirements for the adapter-ligated hairpin,
explicit permitted tail sequences, stage-qualified non-loop controls,
required-member-first bounded scheduling and verified prior-material reuse.
These compose existing molecular authorities. They do not infer arbitrary tail
bases, certify assembly compatibility or make a stopped search exhaustive.

## Remaining product work

### Molecular organization of conditional exploration

The source implementation adds parameter roles and boundary semantics, explicit
request-fixed versus observed-constant status, and source-primer failure diagrams
shared by CLI/API exports and the explorer. Required primer footprints and
available source flanks remain separate; zero extents retain boundary anchors.

The preparation-bound `teaching` projection and `teaching.svg` now cover source/
association, hairpin and insert frames. Browser and static exports share exact
parameter locations; selected contacts expose source/adapter/class together.
A connected short-wide plot replaces the five axis menus, with local detail from
the molecular key and persistent receiving-interface context. Same-record agent
comparison favored the connected plot over three repeated regional strips.

Discovery v6 adds a finite joint receiving-end roster. Words, polarity, orientation
and placements remain one permission, with no undeclared crossed combinations.
Brushing existing evidence, changing permissions and requiring every member
remain distinct actions. Agent-operated browser and CLI/API tasks cover primer
failure, loop changes, zero-gap coverage and explicit end-pair retrieval. A fixed
comparison reference, processing state and zoom survive preparation changes.
Installed-wheel exports match source outputs for discovery, teaching, atlas and
retrieval. The full repository verification endpoint remains the delivery gate;
unfamiliar-user and laboratory evaluation remain separate evidence needs.

### Bounded scaffold completion

Upstream completion searches a caller-authored fixed-length IUPAC pattern or
an inclusive length range with an explicit base domain. Every examined length
and sequence retains its own disposition; a stopped prefix remains truncated.
Interface surveys additionally offer explicit `paired_scaffold_completions`:
preserve context length and sequence dependencies of basal pairing and the
released insert, then seek one exact handle completion per local group. Unknown
coordinate frames retain all context positions. A bounded resumable queue
interleaves unfinished completions with other local pairs and geometry; exact
initial-source site predicates can exclude conditional subsets. This does not
enumerate all unpaired hairpin sequences or all preparations, nor establish a
compact complete relation over the entire coupled construction problem.
Source-partition search still evaluates a supplied exact source. Constraint-directed
joint design of source sequence, cleanup-nick tiling, and a required fragment
partition remains unimplemented; bounded upstream enumeration alone is not
global scaffold design.

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
