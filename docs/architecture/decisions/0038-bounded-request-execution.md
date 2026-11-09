# Bounded execution of authored product requests

`execute_construction_request` and `construction execute` compose existing
translation, local discovery, exact design compilation, selected construction
and saved-bundle verification. The caller explicitly opts into `sole-witness`:
continue only when each required local search records exactly one realization.
Enumeration order is not a ranking. Multiple local witnesses require explicit
selection through `continue_construction_request` / `construction continue`. A single witness can
suffice for an existence question while search coverage remains incomplete.

The opaque `ConstructionRequestExecution` contains immutable delivery bytes.
Its `hop.request-execution-report/v1` summary is a read-only projection, not a
new molecular authority. The delivery retains original inputs and existing
local/design/construction bundles. Publication is atomic and create-only.
Malformed inputs raise; exhausted local absence, unresolved bounded searches,
multiple choices and rejected selected continuations produce scoped handoffs.
The helper does not change ends, contacts, material policies, enzymes or bounds.
It does not try another local combination after a rejected continuation.

The derived summary repeats authored `requested_ends`. Each local coverage row
projects `rejection_counts` from that verified result's existing failure counts;
local-stop `rejection_reasons` exposes the same codes. These are observations of
examined candidates, not repair instructions or global-route absence. The human
report shows the end words, polarity, orientation and paired flank distances
beside those counts. The exact-design model's existing identity constraint is
checked before discovery, so malformed IDs cannot pass only because a request
stops before design compilation. Neither change modifies molecular authorities.

Direct hairpin execution requires `hairpin_basal_component`, two exact equal-
length arms each written 5′→3′. This optional addition to the unreleased
`hop.product-request/v1` authoring contract is omitted when absent; existing
requests keep their translation and canonical construction bytes. Preparation
without this field remains possible for callers supplying an independent exact
design authority. The execution helper requires it before discovery. PCR-bearing
requests reject it because their basal component derives from selected local
processing evidence. No compatibility reader or molecular schema changes are
introduced. Direct API callers can provide `hairpin_basal_arms` when compiling
an exact design from a verified foldback realization.

The model validates the authored component; the existing design bridge derives
its pair observations and content identity. Foldback selection, paired payload,
materialization and complete-route replay retain their existing authorities.
The standalone tutorial supplies an explicit component and shortened primer
span. Those are separate preparation inputs, not automatic repairs or claims
that an insert preparation has the same recoverable hairpin intermediate.

Endpoint names in prose are `ssDNA hairpin`, `copied hairpin duplex` and
`released insert`; machine identifiers remain unchanged. Handoff enzyme names
come from the verified source catalogs through the existing enzyme-definition
resolver. The separate `enzyme-labels.json` is presentation context, like a
caller-stated selection reason; it changes neither projection JSON nor
molecular identity.

Tests exercise CLI/API equality, changed stem length, independent hairpin
execution, absent and malformed components, exhausted and stopped searches,
multiple local witnesses, fixed-source rejection and create-only output. The
public tutorial consumes this shared executor rather than implementing another
continuation policy. Public distribution remains a separate release decision.

## Continue explicit choices and inspect rejected requirements

`continue_construction_request` accepts the saved authored request, a design ID,
and verified local paths plus exact realization IDs. The CLI's `construction
continue` exposes those same fields. It derives payload, endpoint, exact terminal
arms and material policies from the request, replays the local files, and checks
their complete local requests against the translated inputs before compiling.
Changed geometry, permissions, bounds or payload cannot masquerade as the old
local result. Changing only a whole-route material policy is an explicitly new
request evaluated under that policy; it does not reuse an earlier complete
result. Selection summaries name the exact chosen IDs and preserve original
inputs. Missing families must first be discovered from the saved local inputs;
there is no enumeration-order default or implicit search.

The lower-level `compile-local-design` also accepts paired `--hairpin-left-arm`
and `--hairpin-right-arm` options, each written on its own 5′→3′ strand. They
are required for direct hairpins and rejected for PCR-bearing endpoints.

Complete summary rows preserve typed preparation constraints from the replayed
result. Execution summaries and text expose them as `preparation_constraints`:
field, stage, relation, requested value, available/evaluated value and message.
A source primer exceeding its available binding span differs from a fixed
source, end-chemistry or fixed-adapter prefix conflict. These are evaluated
conditions, not proposed edits. A required adapter prefix is not a replacement
whole oligo and does not discard its handle. The result/summary version cut is
recorded in the [schema reference](../../reference/schemas.md).
