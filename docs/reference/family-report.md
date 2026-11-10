# Saved scaffold family report

This exporter turns an executed family into a portable comparison of its named
members. The report shows requested variation, complete preparations, failed
continuations and remaining search coverage together. An optional selection
adds the chosen members and their order specifications.

`project_construction_family_report(path, selection=None, baseline=None, edits=())`
returns `ConstructionFamilyReport`. The equivalent CLI is `construction
report-family FAMILY --out NEW [--selection SET] [--baseline NAME]
[--edit FROM:TO]`. Export is create-only and may not sit inside an input authority.

Provide an executed `hop.construction-family-packet/v1`. The exporter checks its
bounded canonical manifest and semantically verifies the request, derived member
inputs, local receipts, selected local pair, exact design, composition and
outcomes. It rederives presentation choices and shared-property agreement.
The optional `hop.construction-set/v1` request must name exact choices in those
outcomes; a name or matching geometry cannot substitute for verified membership.
Verification repeats the recorded calculations under their original bounds,
using the same membership, routes and requirements.

`summary.json` uses `hop.construction-family-report/v3` and contains:

- Source family identity and manifest digest; recorded and current producers,
  including PDF encoder versions and bundled-font digest.
- Requested variations, effective geometry, scoped status, local coverage,
  preparation diagnostics and all complete choices for each named member.
- Each choice's exact result/realization identity, achieved dimensions, shared
  differences, membership, relative portrait/preparation paths and actual product
  stage projection. End sequences and polarity come from the recorded product.
- Optional named-baseline comparisons: all molecular properties and material
  roles plus regional sequence correspondence, half-open spans and net length.
  Unit-cost edit alignment is limited to 65,536 cells. Ambiguous optimal paths
  carry no asserted base correspondence. Coordinate shifts remain separate.
- A rederived comparison assessment separates scaffold facts, downstream endpoint
  facts, preparation changes and shifted regional coordinates. Non-loop conservation
  requires complete same-stage sequence evidence.
- Optional revision lineage identifies same-request continuation versus an edited
  alternative, the original status and the preserved parent packet.
- Explicit authored member edits and their requested/effective differences.
  These are comparisons of saved requests, not actions that modify them.
- Separate family and selected-set controls: requirements, reference, membership,
  required-and-verified or observed agreement, differences and missing evidence.
  A failed member is unassessed for molecular agreement, never silently matching.
- Recovery facts from the selected complete authority: recorded local choices,
  selected witness, previous status and optional declared loop preference.
- The selected set's declared `compared_properties` and each choice's
  `selection_name`, preserving intended variation and aliases independently of
  observed differences. A singleton has no between-member agreement assessment.

`report.md`, `report.pdf`, `report.svg`, `pages/*.svg` and molecular SVGs are
views of those facts. `selected/`, when present, carries its own portable set,
member authorities, exact preparations, `oligos.csv` and `oligo-uses.csv`.
`family/` retains the captured input and its archived presentations. The report
regenerates its reading views from those records. The packet manifest inventories
all exported bytes. PDF pages are 180 mm wide and deterministic within the
recorded rendering environment. Use JSON for machine-readable facts and PDF/SVG
for reading and visual comparison.

An infeasible selected continuation excludes that continuation. An unfinished
search leaves unexamined alternatives unresolved. Shared-property disagreement
and absence of explicit selection remain separate from construction completion. Exact
sequences and terminal chemistry never collapse to a shape category.

The opening PDF groups up to three whole molecules per plate, with countable
closing-region crops, one dimensioned reference and one named representative
product continuation. Shared agreement is labeled once with its membership scope.
An explicit edit and its failed source preparation share one compact panel.
A single-member recovery uses a decision view rather than empty family slots.
`details/comparison-N.svg` retains full sequence correspondence diagnostics.
Every member's own stage view and preparation remain linked from `report.md`.
A representative continuation never substitutes for the other member records.

The Markdown entrypoint places individual preparations, consolidated orders and
member/role uses before domain JSON and local accounting. A family requirement
cannot be bypassed by reporting an incompatible selection with weaker set controls.
See [explicit comparison controls](../architecture/decisions/0040-explicit-comparison-controls.md).
