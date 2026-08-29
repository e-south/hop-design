---
doc_id: hop-construction-realignment-gap-audit
title: Payload-centered construction realignment gap audit
intent: Map the current HOP, Research Studies, and manufold authorities to the payload-centered construction contract before implementation.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-29
doc_type: explanation
journey:
  - maintain
---

# Payload-centered construction realignment gap audit

## Decision

HOP already has trustworthy payload, molecular-state, discovery, bundle, and
verification authorities. The realignment must reuse those authorities while
adding one missing scientific seam:

```text
final payload coordinates
→ local target geometry
→ exact enzyme and sequence realizations
→ ordered reaction stages
→ exact endpoint products
→ lossless scientific groupings
```

The existing substrate-space journey remains unchanged. Construction discovery
is an advanced competency and must not enlarge the `hop_design.spaces` facade or
turn HOP into a study notebook, experiment tracker, or manuscript renderer.

The current alpha method schema cannot be reinterpreted silently as the staged
construction authority. Its fixed chronology and `LigatedHairpin` state encode
different semantics. New construction schemas must preserve all existing bundle
bytes and verification behavior.

## Audited repositories

| Owner | Checkout used for this work | Branch and revision | State at audit |
| --- | --- | --- | --- |
| HOP | `projects/phd/hop-design` | `dev/hop-scientist-surface-subtraction` at `a4e6449faa2b819893f1c51e275909fcfa6b9e66` | clean |
| Research Studies | `projects/phd/.worktrees/research-studies-hairpin-construction` | `feat/rule-defined-hairpin-construction` at `2ba407e5e08f9cdc623e09626b459f17e66bdc5c` | clean; four commits ahead and six behind `origin/main` |
| manufold | `projects/.worktrees/manufold-hop-manuscript` | `feat/hop-hairpin-manuscript` at `b22b271d400f9078155c08073a8dd9ece99d5a8e` | clean; local-only branch |

The ordinary Research Studies and manufold checkouts contain unrelated
uncommitted work and are outside this implementation. No merge, rebase, push,
tag, release, pull request, or publication action is part of this tranche.

Applicable routing comes from the PhD workspace router, each repository's
`AGENTS.md`, the HOP maintainer skill, the Research Studies workspace contract,
and the HOP manuscript workspace router.

## Baseline verification

The following checks passed before any implementation change:

- HOP: strict preflight, 468 tests, 90.22 percent coverage, documentation,
  security, build, clean-install smoke, and source-versus-wheel parity.
- Research Studies: workspace validation, 180 tests, Ruff check, and Ruff
  formatting.
- HOP manuscript: locked-Pixi documentation and toolchain gate using Pandoc
  3.10 and Tectonic 0.16.9.

The host `uv` 0.12.5 satisfies HOP and Research Studies, which require the
0.12 line. manufold requires `uv <0.10`; its verification must continue through
the locked Pixi environment, which currently supplies `uv` 0.9.30.

## Authorities to preserve

| Scientific or software fact | Current authority | Reuse decision |
| --- | --- | --- |
| One authored payload and derived complement | `models/payload.py`, `models/space/scientist.py` | Preserve unchanged |
| Presentation-independent substrate-space identity | `design/space/authority.py` | Preserve unchanged |
| Small first-use facade | `hop_design.spaces` | Preserve its seven-name allowlist |
| Exact spans and boundaries | `models/coordinates.py` | Reuse for payload and state maps |
| Literal strands, ends, bonds, pair observations, fragments, and lineage | `models/molecular_state.py` | Reuse as molecular primitives |
| Physical pair classification | `models/physical.py`, `models/junction.py` | Reuse; policy must not relabel observations |
| Nicking and duplex-release placement | `models/catalog.py`, `kernel/site_scanning.py` | Generalize through characterized enzymes rather than duplicate |
| Bounded complete/infeasible/truncated searches | `models/discovery/`, `design/*discovery*` | Reuse accounting and deterministic-order patterns |
| Exact design compilation | `HopSpec`, `HopPlan`, `HopBundle` | Preserve as design authority |
| Exact named-method compilation | linear-source method request, plan, and method bundle | Preserve existing authority; reference it from new results where applicable |
| Replay and safe serialization | design and method bundle readers/writers | Extend their patterns; do not create permissive readers |
| Typed neutral views | `models/views.py`, `export/svg.py` | Reuse for diagram-ready projections |
| Study interpretation and asset promotion | Research Studies | Keep outside HOP |
| Manuscript selection and accepted imports | manufold | Keep outside HOP |

## Current public posture

The public facades currently contain:

- `hop_design.spaces`: 7 names;
- `hop_design.discovery`: 74 names;
- `hop_design.methods`: 54 names;
- package-root design language: 91 names.

The first-use surface is genuinely small, but the expert surface is not. The
new capability therefore belongs behind one narrowly scoped advanced facade.
It must not be root re-exported and must not add construction terminology to
the scientist-space quickstart.

## Gap map against the construction contract

### Payload and coordinates

Current discovery requests use route-local precursor coordinates such as a
target nick boundary, precursor spans, or a fixed release boundary. There is no
shared final-payload coordinate authority or explicit route-owned
payload-to-source map.

The payload model does not itself require one contiguous source slice, which is
the correct extension point. Add a final-payload specification, explicit basal
and foldback boundaries, and a route-owned ordered segment map. Represent a
future pair-state exception in the shared payload contract, but reject it as
unsupported by the current linear-source route. Do not implement circularized
source chemistry.

### Route family and endpoint

The named method identifies one whole historical recipe but there is no shared
route-family and endpoint hierarchy. Add the linear-source route family and the
three endpoint values:

- `ssdna_hairpin`;
- `hairpin_pcr_duplex`;
- `clone_ready_duplex`.

Endpoint choice must determine whether adapter capture, PCR, and end-generating
cleavage are required. Direct hairpin requests must not inherit requirements
from the clone-ready branch.

### Characterized enzymes and provisioning

`ProcessingCatalog` currently stores `NickingAgent` and `ReleaseAgent` records
with motif and cut offsets. It lacks a vendor-neutral characterized-enzyme
identity, explicit substrate requirements, resulting-end model,
characterization source, and request-level allowed, forbidden, reserved, and
role policies.

Generalize through a new characterized catalog that can project to the existing
agents. Vendor metadata remains non-authoritative. Catalog policy precedence
must be explicit: an enzyme must be in the allowed universe when an allowlist
is supplied, must not be forbidden or reserved for the active role, and must
satisfy any role restriction. Conflicting policy fields are invalid input.

### Staged molecular operations

The existing linear-source compiler resolves all nickases against one PCR
duplex and then follows a fixed state sequence. There is no reusable reaction
stage containing concurrent operations resolved against the same pre-stage
state. Site scanning generally accepts a sequence rather than a typed molecular
availability context.

Add immutable reaction stages, enzyme-operation bindings, and stage results.
The canonical rule is snapshot concurrency: every operation and unintended
active site is resolved against the same pre-stage state; a stage is accepted
only when its complete non-conflicting event set can be applied atomically.
The next stage consumes only that accepted post-stage state.

The starting ordered single-stranded source material must remain visible when
it precedes the PCR duplex. Foldback closure and basal-adapter ligation must be
separate bonds and transitions. Existing `LigatedHairpin` bytes remain valid as
the historical method authority but do not define the new staged vocabulary.

### Foldback neighborhood

Current released-foldback discovery joins a nick boundary, paired tract, turn
length, agents, orientation, and one-dimensional boundary displacement. It
does not expose the target tuple:

```text
junction_offset_nt
loop_length_nt
annealing_arm_length_bp
```

Add this canonical geometry and support single-cleavage and sequential
terminus-plus-nick programs. The current controlled-flap model requires the
terminus-defining and nick operations to act on different strands. Exact sites,
stage order, released fragments, complementary arm bases, closure bond,
retained sequence, and transient sequence must all be replayable.

### Basal neighborhood

The current basal path is a valid historical four-position profile, but it
embeds four-nucleotide S3/S2/S1/S0 arms, a four-base retained scar, and a fixed
release geometry as though they were universal.

Add an endpoint-dependent basal target. Store pairing positions from the
payload-proximal ligation position outward, with literal bases and physical
`match`, `wobble`, or `mismatch` classes. The PCR branch requires a canonical
proximal match. Type IIS processing belongs only to the clone-ready branch.
Mismatch-directed asymmetry must be derived from exact adapter heteroduplex,
PCR copying, cleavage, and resulting ends rather than assigned as a label.

### Relaxation and completeness

Existing discovery has explicit bounds and truthful statuses but no shared
multidimensional relaxation authority. Add exact-first Manhattan shells with
`exact_only`, `first_feasible_shell`, and `through_radius`. Enumerate all
enabled moves within one shell in canonical order. Reaching a node, hit, or
composition limit before exhaustion always yields `truncated`.

### Symbolic payload compatibility

Current symbolic payloads have exact cardinality, but method compilation is
exact-only. Construction discovery must never repair payload bases. For bounded
spaces, report total assignments, compatible assignments, per-conflict
exclusions, and exhaustiveness. Above the evaluation bound, report
`not_computed` and a conservative warning rather than an estimate.

### Whole-route composition and identity

Current local joins stop at basal pairing/processing and a surviving-strand
continuity test. They do not materialize a complete precursor, run staged
global validation, project endpoint products, or group multiple routes by an
identical final product.

Add separate identities for payload specification, problem, execution,
geometry, local realization, complete realization, final product, result, and
projection. Existing objects named as geometry IDs include enzyme or sequence
facts and cannot be reused as geometry-only IDs. Grouping must remain a
reversible projection whose member IDs and counts exactly cover the underlying
realizations.

### Projections and manuscript ownership

`export/space_figures.py` hand-authors the current substrate-space schematic,
design-set map, and scientific receipt. Those projections remain stable for the
small scientist surface but are not construction-result authorities.

Add neutral typed sources for target schematics, nucleotide-level stage
exemplars, feasibility landscapes, relaxation frontiers, composition maps, and
payload-portability matrices. HOP may render deterministic SVG and tidy data.
Research Studies owns literature-informed inputs, labels, panel composition,
interpretation, and asset promotion. manufold owns accepted snapshot selection.

## Cross-repository gaps

### Research Studies

The task-specific study has seven pipeline-shaped lines and four Figure 1
prototypes. Its schema permits only the existing work fields and assigns every
evidence artifact exactly one work owner. Evidence lifecycle values are
`available`, `stale`, `superseded`, and `blocked`; scientific promotion states
therefore belong in a study-level promotion ledger rather than a repository-wide
schema change.

Migrate to eight scientific lines. L01 owns the substrate-pattern and
stem/periphery prototypes, L02 owns the architecture-optionality prototype,
L05 owns the precursor prototype, L07 owns construction and recovery evidence,
and L08 owns sequence evidence. Preserve prototype bytes and digests while
marking them superseded. Record cross-line reuse in prose, not by assigning one
artifact multiple owners.

The study branch is behind current `origin/main`. This implementation must not
merge without authorization; eventual integration must reconcile the catalog,
root README, and workspace census deliberately.

### manufold

The HOP manuscript already has the correct independent ownership, working
title, prior-art restraint, and blocked physical figure. It still uses the old
seven-line study taxonomy and centers substrate-to-precursor translation rather
than payload-centered local geometry, exact alternatives, and whole-route
composition.

Update the contract, figure plan, source map, open-decision ledger, claim lint,
and import naming after the study registry exists. Figure 1 may select the
smallest accepted set from L01-L06. Figure 2 remains blocked on accepted L07 and
L08 evidence. No producer revision or digest may be guessed. All builds and
tests must use the locked Pixi environment.

## Dependency-ordered implementation map

| Phase | Governing contract | Existing authority to reuse | Smallest change and test seam | Study line and candidate asset enabled |
| --- | --- | --- | --- | --- |
| H1 | payload authority, route hierarchy, identity | payload, coordinates, ADR index | ADRs, glossary, final-payload/source-map contracts; tests for metadata invariance and future segmented map | L01 payload/periphery schematic |
| H2 | characterized enzymes and stages | catalog agents, molecular states, site scanners | vendor-neutral catalog, provisioning policy, reaction stages, state-aware active-site checks; concurrency/order tests | L02/L03 route exemplars |
| H3 | shared local request/result and relaxation | discovery statuses and deterministic identities | narrow construction facade, exact-first shells, geometry groups, exact realization records; lossless-group tests | L02-L04 tidy result sources |
| H4 | foldback target and realizations | released-foldback discovery, foldback evaluation | target tuple, single and sequential programs, closure state; cut-order and compactness tests | L02 feasibility and exemplar |
| H5 | endpoint-aware basal construction | basal pair and processing discovery, exact end model | endpoint target, proximal pairing, optional Type IIS, PCR-derived end asymmetry; endpoint tests | L03 pairing/end landscape |
| H6 | materialization and composition | method materials, lineage, bundles, junction joins | exact precursor/auxiliary materials, full cross-product, global validation, final-product groups; denominator and identity tests | L05 composition map and complete trajectory |
| H7 | scientific projections | typed views, SVG exporter | tidy result tables and closed neutral SVG grammar; semantic renderer tests | L01-L06 candidate assets |
| H8 | public documentation and dogfood | docs smoke, wheel parity | exact/infeasible/relaxed examples from source and wheel; performance receipt | L02-L06 installed-package runs |
| S0-S4 | scientific registry and promotion | study work/evidence contracts | L01-L08, supersession, provisional inputs, installed-API run receipts, promotion ledger | reviewed Figure 1 candidates |
| S5 | physical route admission | study QC and evidence ledgers | protocol/sample/control packet and chromatogram binding templates only | L07-L08 remain blocked pending evidence |
| M | manuscript selection | workspace import and claim checks | new claim ceiling, L01-L08 routing, accepted-only imports, locked-Pixi build | bounded Technical Note plan |

## Deferred investigator decisions

The following remain explicitly provisional or blocked and must not be hidden in
package defaults or manuscript prose:

1. paper enzyme-catalog snapshot;
2. literature-informed payload panel;
3. study relaxation radius;
4. paper basal pairing profiles;
5. physical representative-selection rule;
6. accepted protocol and its match to the modeled route;
7. sample and control identities;
8. recovery and sequence-QC thresholds;
9. recoverability of historical raw evidence;
10. whether L04 earns a separate asset;
11. final Figure 1 selection;
12. HOP release and manuscript evidence cutoff.

## Stop conditions

Implementation must stop rather than conceal a conflict when a route would
mutate payload bases, an enzyme is modeled on an unavailable state, a search
hits a bound before exhaustion, grouping would erase a realization, a figure
would require manual molecular-coordinate repair, an asset lacks promotion, or
the real protocol materially conflicts with the modeled route.

The circularized route, thermodynamic or enzyme-performance modeling, wet-lab
execution, pooled-library claims, activity claims, and release operations remain
outside this tranche.
