# HOP documentation

Choose a task, then follow its guide through the CLI or Python API. The
[installation guide](guides/install.md) identifies the version each workflow needs.

## Start here

[Install HOP](guides/install.md), then choose the task that matches your input:

| I want to… | Guide |
| --- | --- |
| Preserve my stem and see complete designs | [Discover designs](guides/discover-designs.md), optionally constrain ends or scaffold properties, then retrieve a preparation |
| Discover complete hairpin or insert options | [Specify desired scaffolds](guides/discover-product-scaffolds.md) by dimensions, terminal form and permitted methods |
| Make a controlled set of molecules | [Specify a molecular comparison](guides/specify-a-comparison.md) with required members and shared properties |
| Work through one preparation request | [Design one construction](guides/design-a-construction.md), from materials to endpoint |

For the molecular concepts, read [Understand the construction](start/mental-model.md).
For sequence anatomy without a preparation route, [compile a payload design](guides/quickstart.md)
or [preview a substrate space](guides/substrate-spaces.md).

## Choose a lower-level task

### Explore and compare

- [Explore conditional variants](guides/explore-conditional-variants.md): preserve
  explicit properties while browsing supported complete molecules and preparations.
- [Edit folded sequences](guides/edit-folded-sequences.md): loop words, finite
  released-end placements, retained-base changes and a bounded exact stem family.

- [Explore complete scaffolds](guides/explore-scaffolds.md): find whole-molecule
  options from an explicit product request.
- [Author an explicit family roster](guides/compare-scaffold-families.md): bind
  member requests and selections, assess a reference and reconcile alternatives.
  Start with the comparison guide above to specify desired membership.

### Specify construction steps

Local junction searches describe part of a construction. Use whole-route
compilation to check their combination and materials.

- [Search junctions and compile a construction](guides/compile-construction.md):
  payload, enzymes, local constraints, required materials, and endpoint.
- [Search compatible basal candidates](guides/discover-compatible-basal-candidates.md):
  a runnable bounded query. See [search interpretation](discovery/overview.md)
  for coverage, feasibility, and ordering.
- [Find a fragment-removal program](guides/discover-source-partitions.md):
  which nickase combinations leave the required fragments after separation?
- [Enumerate foldback sequence populations](guides/foldback-sequence-space.md):
  count exact local configurations and recover molecular examples from compact sets.
- [Enumerate basal sequence populations](guides/basal-sequence-space.md):
  admit full sources, count distinct local words, and recover molecular examples.
- [Check exact materials through a named method](guides/resolve-production-method.md):
  inspect its molecular states and products; see the [method model](methods/overview.md).

### Inspect and share

- [Save and share preparations](guides/share-atlas-edition.md): reopen recorded
  choices and retrieve their figures and materials without repeating discovery.
- [Render molecular views](guides/render-component-views.md).
- [Verify saved results](provenance/overview.md).

## Inputs and reference

- [Payload files and expansion](guides/payload-sources-and-expansion.md) and
  [degenerate bases](guides/degenerate-payloads.md).
- [Design anatomy](language/overview.md), [terms](language/ontology.md), and
  [pairing rules](language/relationships-and-invariants.md).
- [CLI](reference/cli.md), [Python API](reference/python-api.md), and
  [component calculations](reference/mechanics-api.md).
- Interface surveys: [request and search limits](reference/interface-survey-search.md)
  and [queries, selections and exports](reference/interface-survey-results.md).
- [Material requirements](reference/linear-source-method-materials.md) and
  [view formats](reference/view-contracts.md).
- [Design files](reference/bundle-layout.md),
  [construction files](reference/construction-bundle-layout.md),
  [method files](reference/method-bundle-layout.md), and [schemas](reference/schemas.md).
- [Downstream integration](ecosystem/ownership-boundaries.md).

## Contribute

[Contributor instructions](../CONTRIBUTING.md) and the [maintainer map](dev/README.md)
cover implementation, verification, and releases.
