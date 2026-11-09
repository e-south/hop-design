# Method language overview

The method language derives exact molecular states from one named method
request: the materials and permitted processing that the caller supplies.
HOP records the resulting states and transitions in a method plan, independently
of the design plan that describes the hairpin's sequence anatomy.

```text
MethodRequest -> exact states and transitions -> destination-neutral product
```

Check three things separately:

- whether this HOP version implements the named method;
- whether the exact request resolves to a complete result; and
- whether the resulting product matches the caller's destination.

`hop_design.methods.list_method_capabilities()` reports which named method
families this HOP version implements and their defined input exactness. Current
records use `exact_only` for implemented exact-sequence requests and
`not_defined` when no request schema exists. Use this query before authoring or
resolving a request.

## Follow the task you have

- [Hairpin-processing method boundary](destination-neutrality.md) defines the
  detailed state trajectory, capability facets, materials, outputs, and
  caller responsibilities.
- [Resolve and verify a production method](../guides/resolve-production-method.md)
  shows both explicit request authoring and canonical JSON replay.
- [Linear-source method materials](../reference/linear-source-method-materials.md)
  defines the six required oligos and terminal-chemistry checks.
- [Method-bundle layout](../reference/method-bundle-layout.md) defines persisted
  artifacts and semantic replay.
- [Provenance and verification](../provenance/overview.md) shows the
  caller-owned digest equality between separate design and method bundles.

## Boundary

HOP records exact sequence-bearing states, transitions, terminal chemistry,
pairing, bonds, cuts, and lineage. Check the resulting cohesive ends against a
specific assembly context before using the product there.
