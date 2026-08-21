---
doc_id: hop-schema-reference
title: Public schema identifiers
intent: List stable schema dispatch points and compatibility behavior.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# Public schema identifiers

| Schema ID | Root model | Purpose |
| --- | --- | --- |
| `hop.design/v1` | `HopSpec` | Named generic-route design intent |
| `hop.resolved-design/v1` | `ResolvedHopSpec` | Explicit caller-supplied components and optional resolved events |
| `hop.resolved-design-space/v1` | `ResolvedDesignSpace` | Bounded composable payload and mechanics axes |
| `hop.design-space-plan/v1` | `DesignSpacePlan` | Renderer-free checked Cartesian review table |
| `hop.plan/v1` | `HopPlan` | Immutable compiler result |
| `hop.bundle/v1` | `HopBundle` | Content-addressed artifact manifest |
| `hop.provenance/v1` | `ProvenanceRecord` | Compiler and reference lock provenance |
| `hop.processing-catalog/v1` | `ProcessingCatalog` | Caller-supplied nicking and release agents |
| `hop.workflow-view/v1` | `WorkflowView` | Renderer-independent panels and tracks |

Serialized documents use the JSON key `schema`. Exact IDs are dispatch
contracts: an unknown or stale version fails and is never interpreted as the
nearest known schema. Public models are strict, frozen, and reject unknown
fields.

The `0.1.0a1` line adds the `component_assembly` plan-route discriminator and
the `foldback_junction` and `basal_pairing` workflow-view kinds. Existing
inputs retain their prior discriminator and bytes. Strict consumers must add
the new cases before accepting bundles that use component assembly.

`hop.load_spec(path)` accepts only `.json`, `.yaml`, and `.yml`, and only the
two single-design authored schemas. Design spaces are composed through their
strict model and planned explicitly; catalogs, plans, bundles, and workflow
views are validated through their own root models or integrity operations.
`load_spec` does not guess a document type.
