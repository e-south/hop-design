---
doc_id: hop-schema-reference
title: Public schema identifiers
intent: List stable schema dispatch points and compatibility behavior.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
---

# Public schema identifiers

| Schema ID | Root model | Purpose |
| --- | --- | --- |
| `hop.design/v1` | `HopSpec` | Named generic-route design intent |
| `hop.resolved-design/v1` | `ResolvedHopSpec` | Explicit caller-supplied components and optional resolved events |
| `hop.resolved-design-space/v1` | `ResolvedDesignSpace` | Bounded composable payload and mechanics axes |
| `hop.design-space-plan/v1` | `DesignSpacePlan` | Renderer-free checked Cartesian review table |
| `hop.plan/v2` | `HopPlan` | Immutable compiler result with one typed hairpin-encoding product |
| `hop.bundle/v1` | `HopBundle` | Content-addressed artifact manifest |
| `hop.provenance/v1` | `ProvenanceRecord` | Compiler and reference lock provenance |
| `hop.processing-catalog/v1` | `ProcessingCatalog` | Caller-supplied nicking and release agents |
| `hop.released-foldback-geometry-request/v1` | `ReleasedFoldbackGeometryRequest` | Cross-agent foldback target and exact-first boundary window |
| `hop.released-foldback-geometry-search-result/v1` | `ReleasedFoldbackGeometrySearchResult` | Replayable bounded physical geometry and sequence domains |
| `hop.released-foldback-precursor-search-request/v1` | `ReleasedFoldbackPrecursorSearchRequest` | Selected geometry and caller-authorized precursor domain |
| `hop.released-foldback-precursor-search-result/v1` | `ReleasedFoldbackPrecursorSearchResult` | Bounded exact precursor materialization and completion evidence |
| `hop.hairpin-junction-route-search-result/v1` | `HairpinJunctionRouteSearchResult` | Bounded strand-continuity join across exact foldback and basal routes |
| `hop.linear-source-hairpin-pcr-materials/v1` | `LinearSourceHairpinPcrMaterialsSpec` | Six method oligos and ligation-end preparation |
| `hop.linear-source-hairpin-pcr-materials-plan/v1` | `LinearSourceHairpinPcrMaterialsPlan` | Derived terminal bindings and material handoff |
| `hop.linear-source-multinick-hairpin-pcr-request/v1` | `LinearSourceMultinickHairpinPcrRequest` | Agents, selection, annealing, projection, and materials |
| `hop.linear-source-multinick-hairpin-pcr-plan/v1` | `LinearSourceMultinickHairpinPcrPlan` | Complete molecular-state and restriction-product derivation |
| `hop.linear-source-multinick-hairpin-pcr-result/v1` | `LinearSourceMultinickHairpinPcrResult` | Orthogonal method outcome and optional complete plan |
| `hop.method-bundle/v1` | `MethodBundle` | Content-addressed complete method plan and exported artifacts |
| `hop.workflow-view/v1` | `WorkflowView` | Renderer-independent panels and tracks |

Serialized documents use the JSON key `schema`. Exact IDs are dispatch
contracts: an unknown or stale version fails and is never interpreted as the
nearest known schema. Public models are strict, frozen, and reject unknown
fields.

The `0.1.0a1` line added the `component_assembly` plan-route discriminator and
the `foldback_junction` and `basal_pairing` workflow-view kinds. Existing
inputs retain their prior discriminator and bytes. Strict consumers must add
the new cases before accepting bundles that use component assembly.

The `0.1.0a2` line added an optional paired stem extension to
`hop.resolved-design/v1`. The field is omitted when absent, preserving the
existing serialized input and route surfaces. Plans with an extension add two
feature roles. The independent method-material schemas do not change bundle
replay.

The `0.1.0a3` line replaces `hop.plan/v1` with `hop.plan/v2`. The plan owns one
`HairpinEncodingInsert` containing its sequence digest and nested features, and
bundles emit `hairpin-encoding.fasta`. There is no v1 plan reader or legacy
artifact-name fallback.

The `0.1.0a4` line replaces the generic method-material schema names with the
linear-source names above and adds the strict method request, plan, and result.
There is no reader for the retired generic material schema. Method
implementation availability and request resolution remain separate fields.

The `0.1.0a5` line adds `hop.method-bundle/v1` as a sibling of the design
bundle. It does not change or reinterpret `hop.bundle/v1`. Method-bundle
verification replays one strict request into its complete state plan and exact
exports.

The unreleased line adds strict released-foldback geometry, precursor-search,
and hairpin-junction route schemas. Geometry discovery does not select a
concrete sequence. The separate precursor search accepts one selected geometry,
intersects it with a complete caller-authored IUPAC template, and allocates only
inside explicit node and hit budgets. The junction-route result projects the
exact released state and requires active/surviving strand continuity without
requiring the same release agent at both ends. None of these schemas
reinterprets an existing plan or bundle.

`hop.load_spec(path)` accepts only `.json`, `.yaml`, and `.yml`, and only the
two single-design authored schemas. Design spaces are composed through their
strict model and planned explicitly; catalogs, plans, bundles, and workflow
views are validated through their own root models or integrity operations.
`load_spec` does not guess a document type.
