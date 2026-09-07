---
doc_id: hop-contract-table
title: HOP Design contract table
intent: Summarize boundary preconditions and guaranteed postconditions.
audience:
  - API consumers
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-31
doc_type: reference
journey:
  - compile
  - discover
  - method
---

# HOP Design contract table

## Accepted construction-discovery contracts

These contracts define the implemented semantic authority for
payload-centered construction. They do not enlarge the
`hop_design.spaces` facade. External callers use the narrow
`hop_design.construction` operations rather than importing the raw contracts.

| Contract | Preconditions | Guarantees |
| --- | --- | --- |
| final-payload specification | One intended duplex payload in final-product coordinates; one authored reference strand; explicit basal and foldback boundaries | Derived aligned complement; zero-based half-open positions; immutable payload bases; no assumption of one contiguous source interval |
| route-family source map | Final payload, one route family, and exact source segments | Every payload position maps to explicit strand-local source coordinates; route-specific segmentation cannot redefine payload identity |
| endpoint | One route family and one of `ssdna_hairpin`, `hairpin_pcr_duplex`, or `clone_ready_duplex` | Required neighborhoods, materials, stages, and products follow from the endpoint; later-endpoint requirements do not leak into earlier endpoints |
| local-neighborhood discovery | Final payload, family, route, endpoint, explicit target, constraints, preferences, enzyme catalog, relaxation, finite enumeration, and optional exact sequence-domain part | Exact-first foldback or basal realizations; requested and achieved geometry; rejection accounting; `complete`, `infeasible`, or truthful `truncated` status; unchanged realization identity across execution parts |
| foldback target | Explicit nick offset within the first foldback arm, loop length, and annealing-arm length | Exact achieved retained geometry, exposed strand, fragments, complementary arm, and closure bond; no mnemonic schema aliases |
| basal target | Endpoint-dependent nick target and exact proximal-outward pair constraints; optional end-generation request | Literal pairing state and classes; canonical proximal match when adapter ligation requires it; Type IIS cuts and cohesive ends only for a requesting endpoint |
| reaction stage | One accepted pre-stage molecular state and one or more declared concurrent operations | Every intended and unintended actionable binding resolves against the same pre-stage state; one atomic non-conflicting post-stage state or route failure |
| source preparation | One exact or derived source ssDNA, two resolved source-preparation primers, a payload-to-source span, and exact terminal chemistry | Primer bindings lie outside the payload; the exact copied duplex, pairings, chemistry, identity, and per-base lineage replay from the three external materials |
| complete route composition | Exact local realizations, one payload, one route family, one endpoint, and explicit bounds | Payload preservation, stage order, site availability, lineage, strand continuity, closure, endpoint processing, and final encoding are validated globally |
| realization grouping | Complete exact realization set and deterministic grouping keys | Local, complete, final-product, and achieved-geometry identities remain distinct; group membership reversibly covers every realization without deduplication |
| construction source | One bounded regular nonsymlink JSON/YAML mapping with exact schema; strict foldback, optional basal, source-preparation policy, endpoint auxiliaries, constraints, and finite bounds; separate verified design-bundle path | The source cannot author design or result identity; source preparation produces the duplex from one source ssDNA and two source primers; endpoint structure fails closed; the design payload belongs to every declared local payload space |
| `compile_design_from_local_realizations` | Exact payload, explicit realization ids, replay-verified foldback and basal receipts, and a PCR-bearing endpoint | One route-neutral exact-junction `Compilation`; arbitrary equal nonzero basal-arm lengths; molecularly identical selections are independent of search ids and bounds |
| `compile_construction` | Strict construction source and separately replay-verified `HopBundle` | Verified local authorities, replayable source-ssDNA preparation, bounded whole-route composition, exact endpoint materialization, encoding equality with the design, and an opaque write-capable receipt with complete/infeasible/truncated status |
| `ConstructionBundle` | Replay-verified complete result and embedded unchanged design authority | Content-addressed root inventory, exact result and design identities, byte integrity, complete semantic replay, and create-only atomic persistence |
| construction projection | Opaque verified construction receipt plus explicit family or accepted realization selection where required | Deterministic JSON, optional tidy CSV, and SVG preserving the exact source relation; no ranking, implicit exemplar selection, or authority mutation |

Compactness is achieved endpoint geometry plus retained non-payload sequence.
Transient recognition sites, source handles, auxiliary oligos, and destination
sequence remain visible but do not change that measurement.

HOP owns these molecular contracts and neutral projections. Client studies
own frozen runs, observations, interpretation, and asset promotion. Manuscript
systems own accepted imports, claims, evidence cutoff, and final composition.

## Implemented contracts

| Contract | Preconditions | Guarantees |
| --- | --- | --- |
| `ExactPayload` | Non-empty `A/C/G/T` | Uppercase sequence; derived exact paired arm |
| `DegeneratePayload` | Non-empty DNA IUPAC | Uppercase symbolic sequence; derived symbolic paired arm; no implicit expansion |
| `PayloadCollection` | Non-empty typed records; explicit duplicate-sequence policy | Stable record identities; fail, dedupe, or keep behavior is recorded |
| `expand_payload` | One payload record; positive `max_variants` | Exact cardinality checked before allocation; deterministic exact variants or a budget error; no truncation |
| file payload sources | Regular nonsymlink file; explicit byte, record, and total-nt limits | Same typed payload records as inline input or a limit/malformed-input error; no skipped rows |
| `ResolvedDesignSpace` | Nonempty typed axes; unique option IDs; positive `max_designs`; explicit duplicate-final-sequence policy | Cardinality checked before row allocation; deterministic checked specs and projected sequences; duplicates fail or remain counted; no rendering side effects |
| `Span` | Nonnegative boundaries; end not before start | Zero-based, half-open length |
| `FoldbackJunction` | Contiguous spans; equal retained/foldback-arm lengths; ordered bounded pair observations | Retained tract, turn, and foldback arm partition its sequence; exact, mismatched, and cap-only zero-pair junctions share one physical representation |
| `evaluate_foldback` | Exact precursor; retained-tract, source-turn, and protected-region spans; optional zero-length paired arm; turn extension; constraints | Canonical junction, turn boundary, non-Watson-Crick positions, Watson-Crick-only runs, designed sequence, and all independent diagnostics without invented pairs |
| `search_foldback_arms` | Valid foldback search request; positive node and hit limits | Exact-first deterministic hits and truthful `complete`, `infeasible`, or `truncated` status |
| `BasalJunction` | Equal-length arms; one ordered pair observation per position | Pair count and literal pair bases match the antiparallel arms, including wobble or mismatch calls |
| `evaluate_basal_pairing` | Two exact four-base arms and caller constraint profile | Invariant physical S3/S2/S1/S0 pair calls, dimensionless `pair-count-weighted@1` heuristic indices, and a separate active, reserve, or reject decision |
| `search_basal_candidates` | Two four-base IUPAC arm domains, caller constraint profile, acceptance, and node/hit budgets | Exact evaluated arm pairs in literal content order, contiguous `canonical_ordinal`, content identities, exclusion counts, and truthful completion status |
| `search_basal_processing_geometries` | Caller catalog, selected release agent and orientation, exact terminal-nicked strand, four-base scar domain, explicit post-nick domain policy, and node/hit budgets | Signed release/nick geometry, complete domain intersections and blockers for every examined agent, exact compatible-scar cardinality, neutral hit order, and truthful truncation |
| `search_basal_processing_routes` | Typed basal-candidate and processing-geometry results plus route node/hit budgets | Exact retained-scar compatibility, retained-release-site rejection, derived terminal nick and surviving strand, content-addressed routes in neutral order, and separate upstream/local truncation evidence |
| `search_released_foldback_geometries` | Caller catalog, exposure route, nick target and displacement window, paired-tract and turn lengths, downstream-site and complete-separation rules, and node/hit budgets | Replayable cross-agent footprints, cuts, correlated foldback sequence domains, exact sequence-space cardinality, neutral content identities, and truthful truncation without concrete-sequence selection |
| `search_released_foldback_precursors` | One selected released-foldback geometry, a complete caller-authored IUPAC precursor template, and node/hit budgets | Exact template/domain intersection, correlated-pair cardinality, content-addressed exact precursors with contiguous `canonical_ordinal`, explicit caller-domain infeasibility, and truthful truncation without basal-route composition |
| `search_hairpin_junction_routes` | Typed exact-precursor and basal-route results plus route node/hit budgets | Exact precursor-to-geometry replay, released-state projection, one continuous active/surviving strand, content-addressed routes in neutral upstream order, distinct end-agent identities, and separate upstream/local truncation evidence |
| `build_hairpin_junction_route_view` | One validated exact junction-route candidate | A released-workflow view whose state and foldback panels derive from that route; no independent foldback substitution |
| `build_released_foldback_precursor_view` | One selected geometry, exact precursor, and its derived released state | A released-workflow view after cross-object replay; no independent foldback substitution |
| `BasalDesignRequest` | Physical arms, caller policy, acceptance, and optional terminal nick at the basal boundary | A terminal nick is validated when supplied; absence selects route-neutral component assembly |
| `PairedStemExtensionRequest` | Equal nonzero exact-DNA arms | Invariant literal antiparallel pair calls and counts for optional non-payload stem context |
| `LinearSourceHairpinPcrMaterialsSpec` | Six unique sequence materials; exact primers and adapter; explicit ligation-end preparation | Terminal primer bindings, oriented spans, required material IDs, and terminal chemistry in a strict derived plan |
| `MethodOutcome` | Independent implementation and resolution statuses | Unavailable methods remain not evaluated; infeasible results carry errors; complete results carry no errors |
| `LinearSourceMultinickHairpinPcrRequest` | Exact source; unique caller-supplied agents; inclusive length rule; adapter constraints; restriction projection orientation | Every compatible nick and fragment is resolved or the result is explicitly infeasible |
| `LinearSourceMultinickHairpinPcrPlan` | Complete result from the bounded compiler | Source duplex, all nicks and fragments, selection, pairing, bonds, PCR boundaries, duplex, restriction product, exact cohesive ends, and projection replay after serialization |
| `MethodBundle` | Root manifest derived from one complete method compilation | Content-addressed inventory and identities for the request, plan, trajectory, duplex/restriction FASTA, GenBank, and hairpin-encoding projection; no loaded artifact bytes |
| `load_verified_method_bundle` | Persisted method-bundle directory | Safe-path and complete-inventory checks plus deterministic request-to-plan and byte-for-byte artifact replay |
| `project_released_strand_state` | Exact precursor; route-compatible nick; explicit in-bounds cuts and constraints | Active and retained sequences stored 5′→3′, literal strand roles, precursor spans, and orientation-correct per-base lineage or diagnostics |
| `ProcessingCatalog` | Known schema; unique caller-defined agent IDs | Exact site/cut scanning and symbolic motif presence without package-owned application data |
| `search_nicking_placements` | Caller-supplied catalog; explicit target strand, boundary, paired tract, turn allowance, node budget, and hit budget | One strand-compatible geometry per examined nicking agent; exact/nearest placement, blockers, required lengths, neutral deterministic order, and truthful search/result truncation |
| `HopSpec` | `hop.design/v2`; one typed payload; explicit derivation, policy, and bounds references | Intent only; no paired arm, compiled encoding, or method chronology input |
| `ResolvedHopSpec` | `hop.resolved-design/v2`; explicit foldback and basal components; optional paired stem extension; optional terminal nick; release only with terminal-nick geometry | Component evaluation or explicit resolved-junction derivation; release output equals foldback input or `HOP-ROUTE-001` |
| `HairpinEncodingInsert` | Compiler-owned sequence, digest, and ordered features | Features partition and reconstruct the complete one-dimensional hairpin core; the object makes no duplex or cloning-readiness claim |
| `HopPlan` | `hop.plan/v3`; deterministic design derivation and lock | Paired payload and hairpin encoding reconstruct from evaluated components; projected nick/release geometry is not ordered production history |
| `HopBundle` | Root manifest derived from one design compilation | Stable inventory, digests, identifiers, and neutral external references; no loaded spec, plan, or artifact bytes |
| `load_verified_bundle` | Persisted bundle directory | Integrity checks and deterministic semantic replay complete before typed spec, plan, provenance, manifest, and artifacts are returned |
| `CheckReport` | Valid spec and configuration | All expected feasibility diagnostics without hiding software failure |
| `WorkflowView` | Valid derived evaluation or strand state | Renderer-independent panels, tracks, spans, pair calls, and stable schema; renderers cannot revise state |

All public Pydantic models are strict, frozen, and reject extra fields. JSON
schema identifiers are exact literals; stale versions fail on load.
