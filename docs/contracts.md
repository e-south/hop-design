---
doc_id: hop-contract-table
title: HOP Design contract table
intent: Summarize boundary preconditions and guaranteed postconditions.
audience:
  - API consumers
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
---

# HOP Design contract table

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
| `evaluate_foldback` | Exact precursor; explicit nick, spans, optional zero-length paired arm, turn, and constraints | Canonical junction, mismatch/run measurements, designed sequence, and all independent diagnostics without invented pairs |
| `search_foldback_arms` | Valid foldback search request; positive node and hit limits | Exact-first deterministic hits and truthful `complete`, `infeasible`, or `truncated` status |
| `BasalJunction` | Equal-length arms; one ordered pair observation per position | Pair count and literal pair bases match the antiparallel arms, including wobble or mismatch calls |
| `evaluate_basal_pairing` | Two exact four-base arms; explicit wobble choice and caller constraint profile | Physical S3/S2/S1/S0 pair calls plus separate active, reserve, or reject decision |
| `BasalDesignRequest` | Physical arms, caller policy, acceptance, and optional terminal nick at the basal boundary | A terminal nick is validated when supplied; absence selects route-neutral component assembly |
| `PairedStemExtensionRequest` | Equal nonzero exact-DNA arms and explicit wobble choice | Literal antiparallel pair calls and counts for optional non-payload stem context |
| `LinearSourceHairpinPcrMaterialsSpec` | Six unique sequence materials; exact primers and adapter; explicit ligation-end preparation | Terminal primer bindings, oriented spans, required material IDs, and terminal chemistry in a strict derived plan |
| `MethodOutcome` | Independent implementation and resolution statuses | Unavailable methods remain not evaluated; infeasible results carry errors; complete results carry no errors |
| `LinearSourceMultinickHairpinPcrRequest` | Exact source; unique caller-supplied agents; inclusive length rule; adapter constraints; restriction projection orientation | Every compatible nick and fragment is resolved or the result is explicitly infeasible |
| `LinearSourceMultinickHairpinPcrPlan` | Complete result from the bounded compiler | Source duplex, all nicks and fragments, selection, pairing, bonds, PCR boundaries, duplex, restriction product, and projection replay after serialization |
| `MethodBundle` | One complete method plan and generated artifacts | Content-addressed request, plan, trajectory, duplex/restriction FASTA, GenBank, and hairpin-encoding projection |
| `load_verified_method_bundle` | Persisted method-bundle directory | Safe-path and complete-inventory checks plus deterministic request-to-plan and byte-for-byte artifact replay |
| `project_released_strand_state` | Exact precursor; route-compatible nick; explicit in-bounds cuts and constraints | Active and retained sequences stored 5′→3′, literal strand roles, precursor spans, and orientation-correct per-base lineage or diagnostics |
| `ProcessingCatalog` | Known schema; unique caller-defined agent IDs | Exact site/cut scanning and symbolic motif presence without package-owned application data |
| `search_nicking_placements` | Caller-supplied catalog; explicit target strand, boundary, paired tract, turn allowance, node budget, and hit budget | One strand-compatible geometry per examined nicking agent; exact/nearest placement, blockers, required lengths, neutral deterministic order, and truthful search/result truncation |
| `HopSpec` | Known schema; one typed payload; explicit references and bounds | Intent only; no paired arm or compiled hairpin encoding input |
| `ResolvedHopSpec` | Known schema; explicit foldback and basal components; optional paired stem extension; optional terminal nick; release only with a terminal nick | Route-neutral component assembly or resolved-event compilation; release output equals foldback input or `HOP-ROUTE-001` |
| `HairpinEncodingInsert` | Compiler-owned sequence, digest, and ordered features | Features partition and reconstruct the complete one-dimensional hairpin core; the object makes no duplex or cloning-readiness claim |
| `HopPlan` | Resolved assembly or processing route and lock | Paired payload and hairpin encoding reconstruct exactly from evaluated components; source oligo and state steps match the declared route kind |
| `HopBundle` | Plan plus generated artifacts | Stable inventory, digests, identifiers, and neutral external references |
| `load_verified_bundle` | Persisted bundle directory | Integrity checks and deterministic semantic replay complete before typed spec, plan, provenance, manifest, and artifacts are returned |
| `CheckReport` | Valid spec and configuration | All expected feasibility diagnostics without hiding software failure |
| `WorkflowView` | Valid derived evaluation or strand state | Renderer-independent panels, tracks, spans, pair calls, and stable schema; renderers cannot revise state |

All public Pydantic models are strict, frozen, and reject extra fields. JSON
schema identifiers are exact literals; stale versions fail on load.
