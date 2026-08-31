---
doc_id: hop-linear-source-product-closure-audit
title: Linear-source product closure audit
intent: Map the implemented linear-source authorities to one source-ssDNA-to-endpoint product result.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-31
doc_type: explanation
journey:
  - maintain
---

# Linear-source product closure audit

## Decision

HOP must return a complete digital molecular dependency bundle without relying
on a caller repository. The smallest sound closure is:

```text
exact source ssDNA + exact source primers
  -> replayable source-duplex preparation
  -> exact source duplex
  -> source partition and local junction authorities
  -> existing complete construction chronology
  -> requested molecular endpoint
```

The source-duplex preparation is a molecular derivation, not a PCR-performance
model. It records terminal bindings, exact products, pairings, chemistry, and
sequence lineage. It does not predict amplification, yield, purity, or recovery.

The historical worked route remains a caller-owned integration fixture. HOP's
tracked examples and tests use application-neutral sequence analogues; private
part identifiers and study sequences do not enter this public repository.

## Current authority map

| Route fact | Current authority | Closure classification | Required connection |
| --- | --- | --- | --- |
| final payload and derived partner | `FinalPayloadReference` | present and connected | preserve |
| exact foldback alternatives | verified foldback-neighborhood result | present and connected | preserve local authority |
| exact basal alternatives | verified basal-neighborhood result | present and connected | preserve local authority |
| source ssDNA sequence | content-addressed external material and contextual route use | present and connected | preserve exact payload mapping |
| source-PCR primers | content-addressed external materials and contextual route uses | present and connected | preserve explicit resolution policy |
| source-PCR duplex | replay-verified source-preparation authority | present and connected | preserve exact producer lineage |
| initial complete-route duplex | source-preparation product and first `ConstructionProgram` state | present and connected | preserve byte-equivalent state identity |
| source-wide cleanup nicks and selection | verified source-partition result | present and connected | preserve explicit selected-realization binding and replay |
| foldback and basal enzyme stages | assessed local and complete reaction programs | present and connected | preserve staged, state-aware replay |
| denaturation and fragment selection | exact construction transitions | present and connected | preserve equality with the selected source-partition authority when supplied |
| foldback closure | explicit association and covalent bond | present and connected | preserve as a bond separate from adapter ligation |
| adapter | exact construction material plus endpoint auxiliary policy | present and connected | preserve derive, constrain, and fixed resolution modes |
| adapter ligation | explicit adapter authority and bond | present and connected | preserve |
| hairpin-PCR primers | exact construction materials plus endpoint auxiliary policies | present and connected | preserve contextual route use and safe non-payload binding |
| hairpin-PCR duplex | primer-extension authority and exact state | present and connected | preserve |
| defined-end duplex | Type IIS release authority | present and connected | keep destination compatibility separate |
| material grouping and route selection | reversible result projections plus result-bound selection | present and connected | preserve grouping, explicit sorting, and non-ranking semantics |
| physical materials and observations | caller study or laboratory system | out of HOP scope | bind through stable HOP material and realization IDs |

## Reuse decisions

The implementation reuses:

- `ExactConstructionMaterial` as the exact DNA and terminal-chemistry value;
- `PcrPrimer` as the terminal annealing contract;
- `pcr_products` for exact primer incorporation and copied product derivation;
- `ConstructionState` for paired source-duplex output;
- existing complete-route material, state, transition, bundle, and replay
  authorities after the source duplex; and
- source-partition request, result, and replay contracts without moving cleanup
  nicks into basal geometry.

The named-method `SourcePcrDuplex` remains a behavioral oracle, not the new
authority. It lacks content identity and does not carry the complete
construction result's molecular replay contract.

## Historical fixture role map

The caller-owned worked route exercises eight contextual roles:

1. principal source ssDNA;
2. source-materialization forward primer;
3. phosphorylated source-materialization reverse primer;
4. phosphorylated ligation adapter with a pairing region and endpoint handle;
5. hairpin-PCR forward primer;
6. hairpin-PCR reverse primer;
7. optional destination forward primer; and
8. optional destination reverse primer.

The first six close HOP's destination-neutral linear-source route. The final
two belong only to an optional destination-preparation branch. Exact fixture
sequences, commercial reagent identities, and physical records remain in the
owning Research Studies record.

## Product gaps

Source preparation and one selected source-partition realization are consumed
by complete-route replay. The portable result binds accepted routes and retains
enough sealed evidence to replay exact partition rejection reasons.

Endpoint auxiliary resolution is connected. PCR-bearing routes now resolve the
adapter and both endpoint primers through explicit `derive`, `constrain`, or
`fixed` policies. Derived and constrained primers bind invariant construction
sequence outside the payload; reusable handles are explicit caller inputs, and
no thermodynamic rank is inferred.

Concise grouped result navigation is connected. The public CLI summarizes exact
accounting, groups accepted alternatives by geometry or endpoint product,
applies explicit filters and sorts, inspects one accepted trajectory, writes its
deterministic projection, and persists a result-bound selection reference.
Display limits do not change verified accounting, and no ordinal or sort becomes
a route rank. This closure adds no generic workflow engine, inventory subsystem,
dashboard, PCR thermodynamics model, or cleanup-recovery predictor.

## Verification plan

Each behavior change begins with a failing contract test. Closure requires:

- forged source-preparation sequence, chemistry, binding, pairing, lineage, or
  identity to fail replay;
- exact source-preparation output to equal the complete route's initial duplex;
- selected source-partition membership, source identity, fragment rule, and
  survivors to replay inside the route result;
- source and wheel runs to produce canonical-byte-identical results; and
- one application-neutral fixture plus one caller-owned historical replay to
  close through the installed public package.
