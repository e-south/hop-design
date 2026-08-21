---
doc_id: hop-view-contracts
title: Workflow view contracts
intent: Define renderer-independent scientific views and their generated artifacts.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# Workflow view contracts

`WorkflowView` (`hop.workflow-view/v1`) is the scientific authority for a
visualization. A view contains ordered panels, strand-aware sequence tracks,
typed feature spans, and explicit pair calls. Referential and coordinate
validity are checked before rendering.

Molecular sequence fields are 5′→3′. Released-product tracks therefore display
as 5′→3′ regardless of literal strand. A coordinate-aligned precursor-bottom
track is explicitly 3′→5′; it is a display transformation, not stored molecular
state.

| View kind | Required panels |
| --- | --- |
| `foldback_junction` | folded junction only; no nicking state asserted |
| `foldback_qa` | pre-nick duplex, post-nick exposed, post-nick foldback |
| `released_workflow` | precursor, released fragments, origin-anchored foldback |
| `basal_pairing` | paired basal junction only; no terminal nick asserted |
| `basal_terminal_nick` | pre-terminal nick, post-terminal nick |

Build views from already-derived mechanics:

```python
foldback_view = hop.build_foldback_view(foldback_evaluation)
basal_view = hop.build_basal_view(basal_evaluation, nicked_strand=hop.Strand.TOP)
svg_bytes = hop.render_workflow_svg(foldback_view)
```

Use `build_foldback_junction_view` and `build_basal_pairing_view` when the
components are known but a processing route is not asserted.

The dependency-free SVG renderer consumes only `WorkflowView`. It does not
recalculate pairing, cuts, spans, strand state, or eligibility. Equivalent view
JSON therefore produces byte-identical SVG.

Explicit-mechanics bundles always include foldback and basal view JSON/SVG.
Component assemblies receive route-neutral views. Resolved events receive
processing-state views and include released-workflow JSON/SVG only when a
release projection exists.
The JSON is the renderer-independent review and interoperability surface; the
SVG is a deterministic convenience artifact. Neither is experimental evidence.
