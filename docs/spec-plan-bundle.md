---
doc_id: hop-spec-plan-bundle
title: HopSpec to HopPlan to HopBundle
intent: Explain information ownership and derivation across compilation.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-21
---

# `HopSpec` to `HopPlan` to `HopBundle`

The spec is the only manually authored source of truth. `HopSpec` selects the
visible generic catalog route. `ResolvedHopSpec` instead supplies explicit
foldback and basal components, an optional terminal nick, an optional
route-dependent duplex release, and caller-owned references. Both contain one
typed payload, a positive candidate limit, and optional neutral external
references. Neither can contain a paired payload, source oligo, or compiled
hairpin-encoding sequence.

`HopPlan` is compiler-generated and immutable. It locks the compiler and named
references, resolves both junctions and the route, derives the paired payload,
creates typed features and spans, and reconstructs the source oligo and a
digest-bearing `HairpinEncodingInsert`. This product is a one-dimensional
sequence that encodes the hairpin core; it is not a physical duplex. An
optional paired stem extension adds literal left and right features without
changing the derived payload complement. In `component_assembly`, the source
oligo equals the hairpin-encoding sequence and
the plan makes no discovery or processing claim. In `resolved_events`, the
source oligo is the actual molecular route input and may differ from the
hairpin-encoding sequence. That route records an ordered state graph, including
the terminal-nick transition before encoding assembly, physical evaluations, literal
nicked/surviving strands, and an optional released-strand state.

`HopBundle` is a portable manifest plus artifacts. Every compilation emits:

```text
hop-bundle.json
hop-plan.json
hop-spec.json
provenance.json
hairpin-encoding.fasta
source-oligo.fasta      # only when route source differs from the encoding
```

An explicit component or resolved-mechanics compilation also emits:

```text
expected-intermediates.json
foldback-view.json
foldback-view.svg
basal-view.json
basal-view.svg
released-workflow-view.json   # only when release is requested
released-workflow-view.svg    # only when release is requested
```

Component-assembly foldback and basal views contain only junction state.
Resolved-event views add the applicable pre/post-processing panels.

Bundle IDs are derived from the manifest digest. The manifest inventories all
content artifacts but not itself, avoiding a recursive self-hash. Execution and
evidence remain outside HOP. Verification loads and cross-checks the strict spec,
plan, and provenance records, regenerates plan-owned FASTA, and deterministically
replays the spec into the complete stored plan, artifact set, and manifest.
`load_verified_bundle()` returns these typed semantic contents only after that
replay succeeds. Caller systems may link by bundle ID, plan digest,
hairpin-encoding digest, or neutral external reference.
A compiled and verified bundle is not evidence that a route works experimentally.

Production-method resolution uses a separate
[method bundle](reference/method-bundle-layout.md). This preserves design
identity when more than one physical method could produce the same
hairpin-encoding sequence.
