# Product intent expands into existing construction contracts

The complete example previously required repeated payloads, catalogs and end
requirements in local and whole-route inputs. Editing one copy could leave
another inconsistent. `hop.product-request/v1` authors the exact stem arm,
endpoint and oriented ends once. It retains explicit local geometry, material
permissions, enzyme permissions and finite bounds.

`prepare_construction_request` and `construction prepare` use the same strict
translation. They emit the authored request, `hop.construction-source/v8`, its
local request files, and an intent report distinguishing required, derived and
unresolved values. The prepared object is **not a verified receipt**. Discovery,
explicit witness selection, design authority, complete construction and replay
remain separate operations with existing contracts.

The model layer binds the shared catalog to the existing permission contract,
copies the selected product end into the declared basal release projection,
derives payload boundary coordinates, and validates the resulting construction
source. It does not derive cleavage geometry, synthesize oligos, rank candidates
or relax ends. `EnzymePermissions` shares field definitions with
`EnzymeProvisioningPolicy`; catalog-bound validation remains in the latter.
The export layer renders intent. The design layer owns bounded file intake and
create-only publication. The CLI calls the public API.

For a single bottom-strand nick offset and a right-end source-duplex projection,
the existing end-coordinate model also maps the required left end onto already
declared source contact positions. Translation intersects these implied bases
with authored permissions; an empty intersection names the end and conflicting
position. This source-base propagation never changes pairing classes, adapter permissions
or the contact window on its own. Multiple offsets and other strand/material frames receive no additional
local narrowing; complete-route end verification remains mandatory in every
case. The report distinguishes these paths. This keeps one authority for strand
coordinates while removing redundant end-base authoring in the public example.

An earlier endpoint rejects downstream end or release declarations. A basal
geometry cannot separately declare a future end. A hairpin-only request still
needs an explicit exact design for execution; translation does not fabricate
a basal component to satisfy that separate authority. [ADR 0038](0038-bounded-request-execution.md)
adds an optional exact component to this authoring contract for independent
hairpin execution, keeping the translated construction source unchanged.

Tests cover CLI/API byte equality, exact requirement preservation, unknown
fields, reserved enzymes, invalid orientation/units, duplicate end authority,
endpoint obligations, create-only output and a complete public example. A
browser editor remains a separate decision. Bounded sole-witness continuation
is governed by ADR 0038.

Related: [construction facade](0027-file-oriented-construction-facade.md),
[material closure](0033-close-linear-source-material-dependencies.md), and
[construction journey](../../guides/design-a-construction.md).

## Explicit end-relative permissions and edit preview

The unreleased v1 product request additionally accepts
`basal.end_footprint_pairing` with the explicit fields
`reference: left_end_source_contacts`, `proximal: match`, and `within` (one
existing pairing allowance). It expands only in the single bottom-strand nick,
right-end source-duplex frame above, using `source_contact_bases`; unresolved
frames reject this declaration. Matching proximal contacts and the chosen
footprint permission are authored requirements, not inferred concessions.
Absolute constraints can be omitted or supplied alongside the declaration:
contradictory classes reject, explicit base restrictions survive, and constraints
outside the generated span stay unchanged. Expansion is bounded to 100000
positions and the existing local contract validates the resulting geometry.
No annealing minimum or noncanonical-pair cap changes automatically.

`PreparedConstructionRequest.preview_json_bytes` and the emitted `preview.json`
show both end requirements, source footprint, expanded permissions, annealing
minimum, exact material policies and unsupported upstream-context search for a
direct hairpin. `prepare_construction_request(path, compare_to=reference)` and
`construction prepare REQUEST --compare-to REFERENCE --out NEW` add semantic
request-field differences and both derived footprints. Original authored bytes
remain in `request.json`; a digest binds each preview to its request. This is
`hop.construction-request-preview/v1`, an unevaluated display contract. It cannot
be used as a local or complete construction authority.
