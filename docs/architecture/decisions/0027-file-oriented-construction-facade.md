# ADR 0027: Compile construction from strict files behind a narrow facade

Updated by [ADR 0028](0028-separate-foldback-boundary-from-nick-position.md).

The external artifact interface adds `project_basal_source_panel` to this
allowlist. It returns the existing basal molecular panel as canonical JSON
bytes from a verified local receipt and an explicit local realization ID.
It does not select a route or derive additional molecular state. See
[ADR 0036](0036-external-command-artifact-boundary.md).

> [ADR 0028](0028-separate-foldback-boundary-from-nick-position.md) makes
> duplex foldback nick orientation explicit. [ADR 0033](0033-close-linear-source-material-dependencies.md)
> closes the source-ssDNA preparation dependency in the active v5 construction
> source.

## Context

Payload-centered construction discovery now produces replay-verified local
results, complete route realizations, portable bundles, and molecular
projections. Those operations were reachable only through internal model and
design modules. An external caller would have needed to construct embedded
design authorities and connect local result identifiers by hand.

Publishing those internal request, result, molecular-state, and manifest models
would make the complete ontology a supported user surface. It would also let a
source document supply a design that HOP had not independently loaded
and verified.

## Decision

Expose construction through the file-oriented `hop_design.construction` facade.
Strict source files and separately verified authorities produce opaque receipts;
internal request, result and molecular-state constructors remain private.
Projections and explicit selections preserve their source authorities and use
create-only publication.

The complete decision, allowlist, consequences and later extensions are grouped
by API role:

- [Facade, receipts and local construction](0027-file-oriented-construction-facade/facade-and-receipts.md)
  records source ownership, the original public allowlist, inspection,
  projection and selection contracts, plus local and bounded request execution.
- [Discovery, comparison and inspection extensions](0027-file-oriented-construction-facade/discovery-and-selection.md)
  records the public family, option, comparison, conditional exploration, survey,
  optional-intent and frozen-edition operations with their owning decisions.
