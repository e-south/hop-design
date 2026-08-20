---
doc_id: hop-contract-table
title: HOP Design contract table
intent: Summarize boundary preconditions and guaranteed postconditions.
audience:
  - API consumers
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
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
| `FoldbackJunction` | Contiguous spans; ordered bounded pair observations | Retained tract, turn, and foldback arm partition its sequence; exact and mismatched positions share one physical representation |
| `evaluate_foldback` | Exact precursor; explicit nick, spans, arm, turn, and constraints | Canonical junction, mismatch/run measurements, designed sequence, and all independent diagnostics |
| `search_foldback_arms` | Valid foldback search request; positive node and hit limits | Exact-first deterministic hits and truthful `complete`, `infeasible`, or `truncated` status |
| `BasalJunction` | Equal-length arms; one ordered pair observation per position | Pair count and literal pair bases match the antiparallel arms, including wobble or mismatch calls |
| `evaluate_basal_pairing` | Two exact four-base arms; explicit wobble choice and caller constraint profile | Physical S3/S2/S1/S0 pair calls plus separate active, reserve, or reject decision |
| `project_released_strand_state` | Exact precursor; route-compatible nick; explicit in-bounds cuts and constraints | Active and retained sequences stored 5′→3′, literal strand roles, precursor spans, and orientation-correct per-base lineage or diagnostics |
| `ProcessingCatalog` | Known schema; unique caller-defined agent IDs | Exact site/cut scanning and symbolic motif presence without package-owned application data |
| `HopSpec` | Known schema; one typed payload; explicit references and bounds | Intent only; no paired arm or final insert input |
| `ResolvedHopSpec` | Known schema; explicit foldback, basal, terminal-nick, and optional release events | Release output equals foldback input or `HOP-ROUTE-001`; caller-resolved mechanics enter the immutable plan and bundle path |
| `HopPlan` | Resolved route and lock | Paired arm and final insert reconstruct exactly from evaluated junctions; source oligo equals the route input; steps form one declared state graph including terminal nick before assembly |
| `HopBundle` | Plan plus generated artifacts | Stable inventory, digests, identifiers, and neutral external references |
| `CheckReport` | Valid spec and configuration | All expected feasibility diagnostics without hiding software failure |
| `WorkflowView` | Valid derived evaluation or strand state | Renderer-independent panels, tracks, spans, pair calls, and stable schema; renderers cannot revise state |

All public Pydantic models are strict, frozen, and reject extra fields. JSON
schema identifiers are exact literals; stale versions fail on load.
