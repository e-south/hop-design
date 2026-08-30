---
doc_id: hop-schema-reference
title: Current schema identifiers
intent: List the exact authored, authority, and projection schemas in the unreleased current candidate.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: reference
journey:
  - compile
  - discover
  - method
  - verify
---

# Current schema identifiers

This table documents the unreleased `0.1.0a8` source candidate. The published
`0.1.0a7` release retains construction-contract v1; use the tagged documentation
shipped with that artifact.

| Schema ID | Root model | Purpose |
| --- | --- | --- |
| `hop/substrate-space/v1` | `SubstrateSpaceSpec` | One labeled fixed-and-variable authored payload arm with an optional question |
| `hop.hairpin-design-set/v2` | `HairpinDesignSet` | Complete content-addressed digital design-set manifest |
| `hop.molecular-substrate-space/v1` | `MolecularSubstrateSpace` | Normalized per-position molecular authority for one substrate space |
| `hop.design/v2` | `HopSpec` | Named generic design intent |
| `hop.resolved-design/v2` | `ResolvedHopSpec` | Explicit caller-supplied components and design derivation |
| `hop.plan/v3` | `HopPlan` | Immutable compiler-owned design derivation and encoding |
| `hop.bundle/v2` | `HopBundle` | Content-addressed design artifact manifest |
| `hop.provenance/v2` | `ProvenanceRecord` | Compiler and design-reference lock |
| `hop.resolved-design-space/v2` | `ResolvedDesignSpace` | Bounded composable payload and component axes |
| `hop.design-space-plan/v2` | `DesignSpacePlan` | Renderer-free checked Cartesian review table |
| `hop.processing-catalog/v1` | `ProcessingCatalog` | Caller-supplied nicking and release agents |
| `hop.foldback-precursor-search/v1` | `FoldbackPrecursorSearchRequest` | Exact precursor materialization after placement |
| `hop.basal-candidate-search/v2` | `BasalCandidateSearchRequest` | Bounded basal arm domains and explicit heuristic-index policy |
| `hop.basal-processing-geometry-request/v1` | `BasalProcessingGeometryRequest` | Terminal processing geometry query |
| `hop.basal-processing-route-search-result/v2` | `BasalProcessingRouteSearchResult` | Bounded basal pair and processing join |
| `hop.released-foldback-geometry-request/v1` | `ReleasedFoldbackGeometryRequest` | Cross-agent foldback target and boundary window |
| `hop.released-foldback-geometry-search-result/v1` | `ReleasedFoldbackGeometrySearchResult` | Replayable geometry domains and completion evidence |
| `hop.released-foldback-precursor-search-request/v1` | `ReleasedFoldbackPrecursorSearchRequest` | Selected geometry and caller precursor domain |
| `hop.released-foldback-precursor-search-result/v1` | `ReleasedFoldbackPrecursorSearchResult` | Bounded exact precursor materialization |
| `hop.hairpin-junction-route-search-result/v2` | `HairpinJunctionRouteSearchResult` | Bounded continuity join across junction processes |
| `hop.construction-source/v2` | public file source | Strict foldback, optional basal, endpoint-materialization, whole-route-constraint, and finite-enumeration input; the design bundle remains a separate verified path |
| `hop.source-partition-request/v1` | public file source | Exact source duplex, payload mapping, caller-provisioned enzyme domain, required survivor spans, length selection, and finite subset-enumeration bounds |
| `hop.source-partition-result/v1` | public discovery result | Replay-verified nick sites, denatured fragments, selected survivors, candidate dispositions, nick functions, and truthful completion status |
| `hop.final-payload/v1` | internal construction model | Final-product payload coordinates, authored reference strand, boundaries, and derived pairing authority |
| `hop.local-neighborhood-request/v2` | internal construction model | Exact foldback or basal target, route, endpoint, enzyme policy, relaxation, and finite bounds |
| `hop.neighborhood-discovery-result/v2` | internal construction model | Shared exact-first local accounting, shells, grouping, provenance, and completion status |
| `hop.foldback-neighborhood-result/v2` | internal construction model | Replayable exact foldback realizations and their detailed molecular authorities |
| `hop.basal-neighborhood-result/v2` | internal construction model | Replayable endpoint-aware basal realizations and detailed molecular authorities |
| `hop.construction-discovery-request/v2` | internal construction model | Verified design reference, local result references, exact materialization, route constraints, and composition bounds |
| `hop.construction-space-result/v2` | internal construction model | Complete examined composition prefix, exact accepted routes, endpoint products, accounting, grouping, and claim boundary |
| `hop.construction-bundle/v2` | portable construction manifest | Content-addressed complete-construction result and embedded verified design authority |
| `hop.foldback-feasibility-landscape/v2` | public construction projection | Every exact foldback realization and achieved construction dimensions |
| `hop.basal-feasibility-landscape/v1` | public construction projection | Every exact basal realization and endpoint-dependent pairing, nick, cut, and cohesive-end facts |
| `hop.foldback-relaxation-frontier/v2` | public construction projection | Exact examined foldback shells with complete or partial accounting |
| `hop.basal-relaxation-frontier/v1` | public construction projection | Exact examined basal shells with complete or partial accounting |
| `hop.complete-construction-summary/v1` | public construction projection | Lossless disposition, grouping, material, failure, and truncation relation over one verified complete result |
| `hop.complete-construction-trajectory/v2` | public construction projection | One explicitly selected accepted realization with its exact molecular chronology |
| `hop.linear-source-hairpin-pcr-materials/v1` | `LinearSourceHairpinPcrMaterialsSpec` | Six method oligos and ligation-end preparation |
| `hop.linear-source-hairpin-pcr-materials-plan/v1` | `LinearSourceHairpinPcrMaterialsPlan` | Derived terminal bindings and material handoff |
| `hop.linear-source-multinick-hairpin-pcr-request/v1` | `LinearSourceMultinickHairpinPcrRequest` | Exact method inputs, agents, selection, and projection |
| `hop.linear-source-multinick-hairpin-pcr-plan/v2` | `LinearSourceMultinickHairpinPcrPlan` | Complete molecular-state and product derivation with a replayable restriction agent |
| `hop.linear-source-multinick-hairpin-pcr-result/v2` | `LinearSourceMultinickHairpinPcrResult` | Orthogonal method outcome and optional plan |
| `hop.method-bundle/v2` | `MethodBundle` | Content-addressed method plan and artifacts |
| `hop.workflow-view/v1` | `WorkflowView` | Renderer-independent panels and tracks |

The construction source, source-partition request/result, construction bundle,
and six generated construction projection schemas are active external contracts through
`hop_design.construction`. The request and result schemas in that pipeline are
active replay authorities but remain internal: callers do not construct or
import their raw models through the public facade.

`hop.foldback-nucleotide-exemplar/v1` and
`hop.foldback-geometry-count-table/v1` are reserved projection identifiers in
the foldback inventory. No current public model, renderer, or reader accepts
them, and an inventory entry marked `not_generated` is not an artifact claim.

Serialized documents use the JSON key `schema`. Exact IDs are dispatch
contracts: unknown or retired versions fail and are never interpreted as the
nearest known schema. Public models are strict, frozen, and reject unknown
fields. HOP provides no old-version readers, aliases, or artifact-name fallback.

`hop.load_spec(path)` accepts only `.json`, `.yaml`, and `.yml`, and only the
two current single-design authored schemas. The scientist-facing CLI dispatches
`hop/substrate-space/v1` explicitly through `hop_design.spaces`; it does not
extend the single-design loader or guess from fields. Design spaces, catalogs,
plans, bundles, and workflow views use their own strict models or integrity
operations.

Breaking-history rationale belongs in the [decision index](../architecture/decisions/README.md),
not in the active schema contract.
