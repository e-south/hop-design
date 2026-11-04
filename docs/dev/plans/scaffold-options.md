---
doc_id: hop-scaffold-options-plan
title: Discover complete scaffold options before choosing a preparation
intent: Deliver bounded product exploration, explicit retrieval and controlled-set discovery through the CLI and API.
audience: [maintainers, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-05
doc_type: explanation
journey: [maintain]
---

# Discover complete scaffold options before choosing a preparation

A user supplies a stem, intended product, permitted scaffold dimensions and
method/material requirements. HOP returns complete molecular alternatives,
then helps the user choose one preparation or a deliberate comparative set.
The payoff is making product choice possible before the user must understand
local witness identities or supply an already completed reference.

The public exploration, group discovery and explicit label retrieval are now
implemented and verified: 1,989 tests pass, with 91.35% coverage and source/wheel
parity for exploration, grouping and explicit retrieval. Existing execution,
continuation and matching behavior remains covered by regression tests. The [public construction example](../../../examples/complete-construction/README.md)
supplies public inputs. No downstream study or private record is a dependency.

## Scope and delivery boundary

In scope:

- Exact product requests for direct hairpins and released duplex inserts.
- Bounded evaluation of recorded local choices using existing complete-route
  compilation and replay.
- Whole-molecule options, scoped failures, explicit coverage, and portable
  retrieval of a user-selected option.
- Comparative grouping that satisfies existing shared-property contracts and
  retrieves explicit membership.
- CLI/API parity and static, publication-usable molecular views.

Deferred:

- A new molecular solver, relaxed requirements, inferred laboratory inventory,
  automatic repair, biological scoring or claims of exhaustive global search.
- New open-side authoring dimensions, exposed-end hairpins, symbolic complete
  preparations or additional enzyme/topology support.
- Joint search outside the evaluated candidate pool, incremental search resume,
  an interactive editor, assay management or manuscript composition.

The first endpoint-to-endpoint slice is request → complete options → explicit
selection → preparation. Group discovery follows that working slice. No
interface should require a user to choose local witnesses just to see products.

## Product contract

1. **Input.** Reuse the current product request and require an explicit complete-
   continuation budget. Start with the existing matching bound of 1–64 tested
   local combinations. Local domains, quotas and whole-route limits retain their
   authored values. Reject malformed or contradictory input before any publication.
2. **Evaluation.** Discover each required local neighborhood once; inspect the
   recorded foldback choices and optional basal choices. Continue a deterministic
   bounded sequence of their combinations using the existing authorities. A
   direct hairpin has no invented basal search. A failed complete continuation
   consumes budget and remains visible.
3. **Coverage.** Separately report each local search's termination, recorded
   combinations, tested combinations, unexamined recorded combinations and
   accepted complete realizations. Preserve each continued authority's own
   enumeration/accounting status as well. All recorded pairs examined does not mean
   all possible routes exhausted. Zero accepted products with unexamined choices
   is an incomplete result, not global infeasibility.
4. **Identity.** Retain source request, local receipts, exact selected identities,
   complete bundles and producer. The options summary and portraits are derived
   views. Human-readable option labels are scoped to the immutable packet and
   resolve to exact authorities; they are not identities or quality rankings.
   For an unchanged request, local receipts and producer, increasing only the
   continuation budget must retain the same identities for already evaluated
   choices. Do not derive design identity from page order or the total budget.
5. **Selection.** Evaluating alternatives chooses no user product. Require an
   explicit option label for retrieval; translate it into the existing canonical
   selection/set request and verify that request. Do not ask users to copy paths
   or molecular hashes. Multi-member retrieval additionally preserves explicit
   membership, baseline and shared requirements.
6. **Publication.** Use create-only atomic delivery with bounded capture and
   existing protected-path/inventory rules. Replay the saved authorities before
   later retrieval or rendering; edited summary facts must not redefine products.

The implemented surface is `construction explore`, `construction option-sets`
and `construction select-options`, with matching facade operations. See the
[public guide](../../guides/explore-scaffolds.md) and [ADR 0042](../../architecture/decisions/0042-complete-scaffold-options.md).
The comparison intent is reusable at selection so controls need not be re-entered.

## Ordered implementation checklist

- [x] **1. Freeze a public acceptance workflow and add a failing integration test.**
  Extend the public request in the test to loops 3/4/6/8 nt and closing
  extensions 6/9/12 bp, retaining current endpoint-specific material policies.
  Set the foldback retained-overhead bound to 32 nt, node bound to 100,000 and
  realization limit/result quota to 32. Retain the insert's one-witness basal
  bound and the existing per-selected-combination construction limits.
  Author independent hairpin and insert requests. With the current recorded
  domain, expect twelve foldback choices, eleven complete preparations and the
  retained 6-bp/3-nt primer-span rejection per endpoint. The baseline result is
  selection-required before complete options exist. Treat these counts as a
  pinned regression case, not a scientific coverage claim.

- [x] **2. Implement bounded completion in the owning construction layer.**
  Reuse request translation, local receipt loading/discovery, explicit
  continuation and complete verification. Examine the common work in
  [matching_candidates.py](../../../src/hop_design/design/construction/families/matching_candidates.py)
  and [request_continuation.py](../../../src/hop_design/design/construction/request_continuation.py).
  Extract only the shared candidate-evaluation responsibility required by both
  consumers; family-reference comparison stays family-owned. Preserve existing
  matching order, identities and budget semantics with characterization tests.
  Keep portrait rendering and export out of the evaluation loop's domain logic.

- [x] **3. Deliver the first usable CLI/API path, including retrieval.**
  Add opaque options publication/admission, facade and thin command adapters.
  The opening report states the intended product and permitted dimensions,
  presents complete hairpins with achieved dimensions and links exact
  preparations. Keep rejected continuations and incomplete coverage legible.
  A caller explicitly selects one displayed option and receives its verified
  preparation without manually assembling a local ID, path or set JSON.
  Include public runnable examples for both endpoints and a reduced-budget run.

- [x] **4. Dogfood that end-to-end slice and correct task failures.**
  Run the same brief through CLI and API: inspect the requested product,
  distinguish complete products from local candidates, choose a stated geometry,
  retrieve it, relocate the packet and retrieve it again. Repeat with a budget
  that stops before useful products appear. Record manual interventions and
  interpretation errors; preserve requests and expected outcomes across
  interface revisions. Fix observed failures before adding more presentation.

- [x] **5. Add comparative-set discovery over evaluated options.**
  Accept an explicit desired roster and existing shared-property requirements.
  Compute groups from verified product facts; return available and missing
  requested members for each shared background. Do not choose the first
  completed product as a compulsory reference or enumerate every Cartesian set
  of equivalent preparations. Retain alternatives within each group and require
  explicit final membership/baseline. Reuse selected-set admission and material
  comparisons. Discovery covers the evaluated pool only.

- [x] **6. Refine one molecular comparison plate from actual task results.**
  Use desired scaffold → available whole molecules → chosen series →
  preparations. Show loop bases and added paired positions where differences
  occur, label shared features once and distinguish product changes from
  manufacturing changes. Depict later sticky ends only on the released product.
  Reuse portraits and comparison projections; do not build a parallel molecular
  renderer or lead with an outcome matrix.

- [x] **7. Verify and document the delivered boundaries.**
  Update facade/CLI/schema references and the owning ADR after the public
  contract is implemented. Run focused failure/identity tests, strict preflight,
  full verification and source/wheel parity. Preserve existing execute/continue/
  match behavior. Downstream study dogfood and scientific figure selection are
  separate from HOP's implementation gate.

## First-slice delivery contract

**Goal:** one exact product envelope yields complete, inspectable alternatives
and lets a user retrieve one explicitly selected preparation.

**In scope:** steps 1–4, covering both endpoint paths, truthful bounded coverage,
portable options, whole-molecule report and selection. Small shared internal
extraction is allowed when tests protect the existing matcher. Group discovery,
new molecular capabilities and UI frontends are outside this slice.

**Done when:** the public workflow reproduces the pinned alternatives without
local-witness authoring or a prior complete reference; expected failed
continuations remain; the reduced-budget outcome is explicitly incomplete;
CLI/API agree; selected preparations replay and relocate; no default winner or
constraint relaxation exists; full repository gates pass.

**Handoff:** request/producer/bounds, outcome and choice inventories, exact
selections, focused RED/GREEN evidence, gate logs and tester observations.
Use public synthetic inputs in HOP. Callers retain private task motivation and
observations. No external publication or release is implied.

## Validation and risks that affect the user

| Situation | Required behavior and check |
| --- | --- |
| Many local witnesses, no complete reference | Complete alternatives appear under an explicit budget; no manual local-ID requirement. |
| A rejected preparation comes first | Count it, retain its explanation, and continue only while budget remains; never label unexamined alternatives impossible. |
| Budget changes | Original request/local bounds remain identical; disclose deterministic ordering and the examined prefix. No hidden search expansion. |
| More than one basal and foldback witness | Test paired enumeration and truthful unexamined counts, not only the public one-basal example. |
| All recorded pairs examined after a local quota stop | Say recorded pairs examined; retain incomplete local coverage. |
| Same geometry, different sequences or chemistry | Group only for presentation and retain every exact product/preparation identity. |
| First successful candidate for each requested value disagrees on shared properties | Reject that selection; group alternatives using verified controls rather than display order. |
| Missing requested family member | Distinguish absent from the evaluated pool from rejected selected preparation and unexamined search. |
| Material changes across the chosen series | Show molecular controls and changed source/adapter/primer roles separately. |
| Stale selection, changed request, corrupt nested authority or edited summary | Fail before publishing a retrieval; a manifest alone does not replace molecular replay. |
| Moved packet | Explicit labels resolve to the same product and exact oligo chemistry using portable relative authority paths. |
| Invalid output destination or capture bound exceeded | Reject without overwriting inputs or leaving a publishable partial packet. |

## Plan dogfood and refinement

Before implementation, an implementation-aware planning pass replayed 22 complete public-example
authorities, inspected the recorded prefix at five continuation budgets and
used current selected-set admission/retrieval. That was a contract rehearsal;
the exploration command had not yet been implemented. Both endpoint
paths gave the same prefix pattern:

| Recorded pairs examined | Complete products | Unexamined recorded pairs | Complete shared-background loop series |
| --- | --- | --- | --- |
| 1 | 0 | 11 | None in the examined prefix |
| 4 | 3 | 8 | None; requested 3-nt loop absent |
| 6 | 5 | 6 | None, although all four requested loop counts occur |
| 8 | 7 | 4 | 9-bp closing extension |
| 12 | 11 | 0 | Both 9-bp and 12-bp closing extensions |

Selecting the first complete product for each loop count was rejected by current
HOP admission: closing extension, non-loop sequence and regional contacts
disagreed. Both full shared-background sets passed all declared controls for
each endpoint. All four sets were retrieved again after relocation with equal
set identities and exact oligo/role-use specifications.

These observations refine the implementation acceptance criteria:

- The first report must distinguish **products obtained** from **the requested
  comparison obtained**. Presence of all requested dimension values is insufficient.
- A zero-product stopped prefix must lead with remaining coverage and an explicit
  larger-budget action; it must not propose changing the molecule as though the
  request had been exhausted. Rerunning with a larger bound is sufficient for
  the first slice; persisted resume is deferred.
- Group discovery must expose both compatible backgrounds and retain caller
  choice. A first-success policy would unnecessarily restrict that choice.
- Selection must use admitted molecular controls, not only geometry labels;
  compact reports and thin retrieval commands cannot bypass that check.
- Static report refinement follows these tasks. It should make incomplete
  exploration and unavailable comparative membership understandable without
  turning search counters into the principal molecular view.

The first slice has no blocking product questions. Exact command names and
module placement are implementation decisions within the boundaries above.
