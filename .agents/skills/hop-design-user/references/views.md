# Typed views

Use this reference to project already-derived design, discovery, route, or
method state for inspection.

Read [the view contract](../../../../docs/reference/view-contracts.md) and import
builders and rendering from `hop_design.views`.

- Choose the builder whose input type matches the claim already established.
- Use route-neutral foldback and basal builders when no process occurred.
- Use processing or method views only with the matching resolved state.
- Treat `WorkflowView` JSON as the scientific authority.
- Use `render_workflow_svg()` only as a deterministic projection.
- Do not infer eligibility, molecular state, or empirical evidence from a
rendered shape.

Run `examples/render_component_views.py --out build/component-views` for a
minimal foldback and basal example with explicit pair kinds.
