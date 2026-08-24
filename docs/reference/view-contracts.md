---
doc_id: hop-view-contracts
title: Workflow view contracts
intent: Define renderer-independent scientific views and their generated artifacts.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: reference
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
| `foldback_qa` | source sequence, resolved junction, folded junction |
| `released_workflow` | precursor, released fragments, origin-anchored foldback |
| `basal_pairing` | paired basal junction only; no terminal nick asserted |
| `basal_terminal_nick` | pre-terminal nick, post-terminal nick |
| `method_trajectory` | the eight derived states of a complete named method plan |

Run the complete component example:

```bash
uv run python examples/render_component_views.py --out build/component-views
```

Or build views from already-derived mechanics:

```python
import hop_design as hop
import hop_design.views as views

foldback_view = views.build_foldback_view(foldback_evaluation)
basal_view = views.build_basal_view(
    basal_evaluation,
    nicked_strand=hop.Strand.TOP,
)
svg_bytes = views.render_workflow_svg(foldback_view)
```

Use `build_foldback_junction_view` and `build_basal_pairing_view` when the
components are known but a processing route is not asserted.

The dependency-free SVG renderer consumes only `WorkflowView`. It does not
recalculate pairing, cuts, spans, strand state, or eligibility. Equivalent view
JSON therefore produces byte-identical SVG.

Explicit-component bundles include route-neutral foldback and basal view
JSON/SVG. A design with an explicit terminal-nick request receives the basal
processing view. A design with a release projection also receives the
released-workflow JSON/SVG.
The JSON is the renderer-independent review and interoperability surface; the
SVG is a deterministic convenience artifact. Neither is experimental evidence.
