# Current schema identifiers

Use this reference to identify the document an operation accepts or returns.
Authored schemas describe inputs you supply; result and bundle schemas describe
records HOP derives. Projection schemas describe tables, drawings and reports
generated from those records. The exact schema identifier determines which
reader handles the document.

- [Schema inventory and reader contracts](schemas/inventory-and-readers.md)
  lists active identifiers, strict dispatch, size and execution bounds,
  release-coordinate contracts, and family/set admission rules.
- [Discovery and selection packet contracts](schemas/discovery-and-selection-packets.md)
  explains survey, conditional exploration, edit, family, scaffold option and
  comparison packets, including the meaning of their versions.

For the decisions behind schema changes, use the
[decision index](../architecture/decisions/README.md).
