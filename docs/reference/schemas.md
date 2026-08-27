---
doc_id: hop-schema-reference
title: Current source schema identifiers
intent: List the exact schemas accepted by the unreleased current source candidate.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-27
doc_type: reference
journey:
  - compile
  - discover
  - method
  - verify
---

# Current source schema identifiers

This table documents the unreleased `0.1.0a7` source candidate. The latest published wheel is `0.1.0a6`; use the documentation shipped with that artifact
for its accepted schemas. Contributor-checkout examples in this repository use
the candidate contracts below. Do not submit these identifiers to an a6
installation.

| Schema ID | Root model | Purpose |
| --- | --- | --- |
| `hop/substrate-space/v1` | `SubstrateSpaceSpec` | One bounded, segmented authored payload arm and exhaustive member bound |
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
| `hop.linear-source-hairpin-pcr-materials/v1` | `LinearSourceHairpinPcrMaterialsSpec` | Six method oligos and ligation-end preparation |
| `hop.linear-source-hairpin-pcr-materials-plan/v1` | `LinearSourceHairpinPcrMaterialsPlan` | Derived terminal bindings and material handoff |
| `hop.linear-source-multinick-hairpin-pcr-request/v1` | `LinearSourceMultinickHairpinPcrRequest` | Exact method inputs, agents, selection, and projection |
| `hop.linear-source-multinick-hairpin-pcr-plan/v2` | `LinearSourceMultinickHairpinPcrPlan` | Complete molecular-state and product derivation with a replayable restriction agent |
| `hop.linear-source-multinick-hairpin-pcr-result/v2` | `LinearSourceMultinickHairpinPcrResult` | Orthogonal method outcome and optional plan |
| `hop.method-bundle/v2` | `MethodBundle` | Content-addressed method plan and artifacts |
| `hop.workflow-view/v1` | `WorkflowView` | Renderer-independent panels and tracks |

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
