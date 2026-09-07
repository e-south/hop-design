---
doc_id: hop-adr-0026
title: ADR 0026 - Compose complete construction chronology around enzyme phases
intent: Preserve exact non-enzyme route transitions without weakening ReactionProgram semantics.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
---

# ADR 0026: Compose complete construction chronology around enzyme phases

## Context

Local foldback and basal discovery use `ReactionProgram` to declare ordered
enzyme operations and the exact states against which those operations are
assessed. A complete construction route also contains denaturation, fragment
selection, annealing, ligation, and primer extension. Those transitions are
not enzyme-site programs.

Representing the full route as one existing `ReactionProgram` would require a
cleavage operation to appear to create an annealed, ligated, or PCR-copied
state. That would make adjacency syntactically valid while making the
chemistry false.

## Decision

This decision amends the exclusive chronology language in
[ADR 0020](0020-separate-design-derivation-from-method-chronology.md) without
returning chronology to design derivation. A complete construction route and a
named method plan own distinct ordered histories for their respective
competencies.

`ReactionProgram` remains the authority for one or more assessed enzyme
phases. It continues to own enzyme operations, actionable bindings, concurrent
cut checks, state-specific unintended sites, and the exact pre-state used by
each operation.

`ConstructionProgram` owns the complete route chronology. It contains exact
molecular states connected by `ConstructionTransition` records. Transition
kinds are closed and distinguish enzyme phases from denaturation, fragment
selection, annealing, ligation, primer extension, and end generation.

An enzyme-phase transition references exactly one embedded, assessed
`ReactionProgram`. A non-enzyme transition references an exact derived-state
relation binding its pre- and post-state identities. The construction program
requires contiguous state order, complete transition coverage, no repeated or
unreferenced enzyme program, complete stage-assessment coverage, and content
identity over the complete chronology.

The composition envelope does not reinterpret a local reaction program or
replace family-specific molecular-state authorities. Whole-route
materialization remaps local coordinates onto the complete precursor,
reassesses enzyme phases against their actual complete pre-states, and embeds
the resulting exact authorities in route order.

The complete result embeds the self-validating detailed foldback discovery
authority and, when present, the detailed basal discovery authority. Its
ordered provenance domains derive from those authorities rather than from a
separately authored member list. Each accepted complete realization embeds the
exact local members it composes.

Each local discovery result embeds its replay execution, including enumeration
bounds, route implementation version, operation ceiling, and environment. A
raw result is a parsed structural and molecular record; its recorded shell
prefix cannot independently prove that no omitted candidate exists. The design
layer admits a `VerifiedFoldbackNeighborhoodResult` or
`VerifiedBasalNeighborhoodResult` only after rerunning the exact request and
requiring canonical-byte equality. Equality with an execution bound is not by
itself evidence of truncation. Complete-route composition likewise records
dispositions only for the canonical examined Cartesian prefix. The nominal
domain size proves the unexamined suffix without allocating or storing one
record per unexamined pair.

The complete request embeds the exact authored `DesignSpec`, `HopPlan`, and
`HopBundle` manifest. Model-layer validation replays the deterministic plan
identity, specification and plan digests, bundle manifest digest, bundle
identity, design and payload relations, locked defaults, and external
references. Complete composition additionally requires a `VerifiedHopBundle`,
whose compile replay establishes the artifact-backed design authority. A raw
composition result remains a parsed record; `VerifiedConstructionSpaceResult`
admission reruns exact whole-route composition against the verified local and
design authorities and requires canonical-byte equality.

The advanced construction models remain internal. The
`hop_design.construction` facade defined by ADR 0027 accepts one strict source
file and one separate verified design bundle, then returns opaque compilation,
verified-bundle, and projection receipts. It does not expose raw result
producers or make parsed structural records interchangeable with
replay-verified authorities.

One model-layer route derivation replays the required combined enzyme program
and every post-cleavage strand from those local members, the lifted basal
prefix, and exact source materials. Generation and validation use that same
derivation for operation membership, strand origin, coordinate, orientation,
and end chemistry. Content-addressing remains evidence of immutable content;
membership in an upstream discovery result remains a separate validated fact.

For PCR-bearing routes, the retained source prefix may extend beyond the local
basal pairing arm. The local pairing state identifies that arm as a terminal
subspan of the prefix. The source-return arm is the reverse complement of the
complete prefix, while the ligation adapter remains a separate exact material.
The design encoding is validated as an exact, possibly nonzero subspan of the
PCR product.

Pure actionable-site scanning and reaction-program assessment are owned by the
internal `models.reaction_replay` package. This permits model-adjacent route
validation to assess embedded enzyme phases without importing `kernel` or a
higher use-case layer. There is no compatibility import at the former kernel
path.

One pure complete-route combination evaluator applies the intrinsic gates in
this order: basal source-map compatibility, source end chemistry, global
actionable-site assessment, and design-encoding equality. Discovery and sealed
result validation both call that evaluator. Disposition metrics and intrinsic
rejection reasons are therefore derived evidence rather than author-supplied
accounting. The all-combinations-valid rule remains a post-pass global policy:
it may reclassify intrinsically compatible combinations only after a complete,
untruncated examination while preserving intrinsic failures.

## Consequences

Complete construction can represent PCR-bearing and clone-ready routes
without inventing enzyme chemistry for non-enzyme transformations. Local
reaction programs remain independently inspectable, while one construction
program answers the chronological question across local-family boundaries.

The additional envelope is deliberate domain structure, not a second generic
workflow engine. Experimental execution, yield, quality control, and activity
remain outside the digital method-resolution claim.
