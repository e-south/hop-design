# Python API

Use `hop_design.construction` to discover complete preparations and retrieve
materials. Follow the [worked tutorial](../guides/discover-designs.md) for runnable
CLI and Python examples, then use this reference for field and operation details.

Operations often return a **receipt**: an object that exposes checked results,
their identities and, where supported, methods for writing or projecting them.
**Replay** repeats the recorded calculation from its inputs. A **projection**
turns those results into a table, molecular drawing or report for inspection.

## Find the operation you need

### Discover and refine preparations

- [Discover complete designs](python-api/discovery.md#discover-complete-designs)
  from an exact stem, continue a saved search, and choose an exact preparation.
- [Explore conditional variants](python-api/variants-and-comparisons.md#conditional-variant-exploration)
  within a recorded pool, inspect a molecule, or evaluate changed permissions.
- [Edit sequences](python-api/variants-and-comparisons.md#molecular-edits) or
  [compare scaffold families](python-api/variants-and-comparisons.md#scaffold-families-and-explicit-comparative-sets)
  with explicit required members and controls.

### Construct and inspect molecules

- [Search local construction regions](python-api/construction/local-search.md)
  for foldback and basal realizations, exact sequence spaces, or source removal.
- [Compile a complete route](python-api/construction/routes.md)
  from a product request or verified local selections, then inspect and export it.
- [Compile sequence anatomy and named methods](python-api/anatomy-and-methods.md)
  for design specs, component evaluation, processing discovery and molecular views.

### Keep and share results

- [Create a complete design set](python-api/collections.md#substrate-spaces-and-design-sets)
  from a bounded substrate space.
- [Capture or reopen an atlas edition](python-api/collections.md#frozen-atlas-editions-and-guided-exploration)
  for inspection independent of the live discovery producer.

## Public facades

The package root provides the single-design language. Use these public facades
for construction, discovery, methods, spaces and views:

```python
# Prepare molecular edits through the public construction API.
import hop_design as hop
import hop_design.construction as construction
import hop_design.discovery as discovery
import hop_design.methods as methods
import hop_design.spaces as spaces
import hop_design.views as views
```

Use `hop` for design compilation, payloads, bounded design spaces, and explicit
component evaluation. Use `construction` for file-oriented payload-centered
construction compilation and its neutral projections, `discovery` for bounded
catalog queries, `methods` for named production methods and molecular states,
`spaces` for substrate-space preview and compilation, and `views`
for state projections and rendering. Internal `hop_design.design.*` modules are
not public facades.
