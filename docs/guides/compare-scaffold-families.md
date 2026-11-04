---
doc_id: hop-compare-scaffold-families
title: Specify and retrieve a comparative scaffold set
intent: Preview finite whole-hairpin variations, compare complete members and retrieve their individual preparations.
audience: [users, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-03
doc_type: tutorial
journey: [discover, verify]
---

# Specify and retrieve a comparative scaffold set

To discover required comparisons before selecting construction details, start with
[Specify and retrieve a molecular comparison](specify-a-comparison.md). This guide
retains explicit per-member family authoring and continuation workflows.

If you want to discover whole-scaffold alternatives before selecting construction
details or a complete reference, start with [explore scaffolds](explore-scaffolds.md).

Start with the stem and the scaffold differences you want to investigate. HOP
can execute a finite roster of loop lengths and loop-side paired extensions,
then retrieve explicitly selected complete members as one comparative packet.
Their sequences and preparations remain individual; a common shape does not
make two products interchangeable.

Choose the product first. Both examples use the same public 34-base stem; each
has an independently authored preparation.

| Intended product | Run from a matching source checkout |
| --- | --- |
| Hairpin as the endpoint | `uv run --locked python examples/complete-construction/family.py --endpoint hairpin --out build/hairpin-family` |
| Released duplex insert, via a hairpin intermediate | `uv run --locked python examples/complete-construction/family.py --endpoint insert --out build/scaffold-family` |

Open `comparison/report.pdf`, then `comparison/report.md` for the selected
preparations, order specifications and member/role uses. The report puts these
actions before detailed search accounting. The direct hairpin family ends at the
hairpin; it does not claim exposed cloning ends. In the insert example, AGTC/AGTC
ends arise only after copying and release.

Both compare 3-, 4- and 5-nt loops at a 7-bp loop-side extension. They explicitly
require unchanged non-loop regional sequences, region-local contacts and joins,
and hairpin terminal chemistry while permitting derived source oligos and primers.
These are selected-set admission requirements, not a promise that a search finds
an admissible series. The insert example retains a rejected 6-bp/3-nt preparation:
its selected reverse primer requires 14 nt and the span supplies 13. The report
shows an explicitly edited 7-bp alternative beside that outcome; it does not
exclude every possible preparation of the failed geometry.

## Author one finite family

The generated `comparison.json` is the concise starting point. It names a
`base_request` file and its matching `product`, a `vary` roster and `hold`
properties. `geometry_permissions` explicitly replaces only the named base
domains. Omitted `requirements` and `materials` preserve the base. An explicit
`requirements` object replaces scaffold requirements; `requirements: null`
clears only those scaffold requirements. `materials`, when supplied, is the
complete materialization policy, not a partial patch. The portable authoring
packet preserves the original base alongside the brief.

```bash
hop-design construction author-family build/scaffold-family/comparison.json --out build/authored-family
```

Open `authored-family/preview.svg` for dimensioned intent and the member roster.
Read `authored-family/report.md`: product, permitted material changes, effective
member geometry, conflicts and bounds appear together. Execution consumes the
compiled `authored-family/family.json`. Editing the lower-level canonical family
is also supported:

- `base_request` contains one complete `hop.product-request/v1` document:
  stem, endpoint, enzyme permissions, material policies, requirements and
  finite local searches.
- `members` explicitly names each combination. Author `loop_nt`,
  `loop_side_paired_bp`, or both. HOP does not expand an implicit Cartesian grid.
- `shared_properties` names properties that complete displayed members must
  retain: `stem_sequence`, `endpoint`, `release_interfaces`,
  `open_side_paired_positions`, `loop_side_paired_bp`, `loop_nt`, or
  `terminal_chemistry`, `non_loop_sequences`, `regional_contacts`, or
  `regional_joins`. Non-loop sequences include both terminal tracts and every
  non-loop region. Contacts retain each primary-region offset, bases and pair
  class; joins retain region-local bond boundaries, including the loop. The
  recorded hairpin stage must agree. Shifted absolute coordinates are not changes
  to these regional controls. Material changes remain separately visible.
  `terminal_chemistry` refers to the depicted joined hairpin, not its source
  oligo. `release_interfaces` compares each later end's side, word and polarity;
  shifted cut coordinates remain in the full comparison.
- `display_preferences` orders eligible complete alternatives by a supported
  numeric dimension, ascending or descending. It never selects a winner or
  relaxes requirements.
- `bounds` explicitly caps members, total declared search nodes and selected-pair
  continuations. The roster allows at most 64 members. Each local search keeps
  its own limits; one member continues at most one local pair under the
  explicitly requested `sole-witness` policy.

A member value intersects the base's hard requirements and local geometry
domain. To permit 3/4/5-nt loops, author that base domain and remove any
contradictory exact 4-nt requirement yourself. HOP will not widen either input.
Open-side extent is currently an achieved shared property and display key,
not a new independently editable member dimension.

## Preview, execute, inspect

```bash
hop-design construction prepare-family build/scaffold-family/family.json --out build/family-preview
hop-design construction execute-family build/scaffold-family/family.json --continuation sole-witness --out build/family-outcomes
```

Preview runs no search. Its summary lists each requested variation, effective
geometry or conflict, and aggregate upper bounds. Execution rejects conflicts
before search. A valid request can still yield a rejected selected preparation,
an exhausted local absence, a stopped unresolved search or multiple local
choices. Every member retains its request, local coverage and scoped outcome.
Only complete, shared-property-compatible choices enter `display_choices`.
The shared reference is the first complete recorded choice, identified in the
summary; it is not a scientific preference. If a local search has multiple
witnesses, use [explicit continuation](../reference/cli.md#continue-explicit-local-choices)
for that member and select its resulting complete authority yourself.

The family summary does not establish exhaustive scaffold coverage. A member's
complete route can follow an existence search stopped at its first witness.
Family artifacts have a 512-MiB capture limit; narrow the roster if exceeded.

## Select a deliberate set

The example's `set.json` names the three loop members explicitly. Each entry
has a safe short `name`, a `bundle_path` and a result-bound `selection_path`.
Paths are relative to that request file or absolute. `baseline` names the
comparison reference; `shared_properties` must agree across all selected
members, while `compared_properties` states what the author wants to compare.
The latter is not a causal-isolation claim or a requirement that values differ.
The report names that intended comparison before retrieval and distinguishes
it from observed differences. A one-molecule selection is valid for retrieval,
but between-member agreement remains unassessed. If a selection renames a family
member, the report explicitly connects both names.

```bash
hop-design construction select-set build/scaffold-family/set.json --out build/comparative-preparations
```

Every selection is replay-verified before publication. Duplicate exact
selections, stale selections, missing authorities, mixed endpoints/stages or
false shared-property claims reject the entire packet. Same-shaped molecules
with different sequences or chemistry retain their own identities. Publication
is create-only and outside every input authority.

The output contains:

- `members/NAME/portrait/projection.svg` and `preparation/`: exact molecular
  drawing, preparation report, oligos and supporting trajectory.
- `comparisons/NAME.json`: baseline comparison of sequences, material roles,
  operations, product dimensions and region-local contacts. Equal sequence
  and shifted coordinates are reported separately.
- `oligos.csv`: one order row per exact sequence and terminal chemistry.
- `oligo-uses.csv`: every member/role using each specification. Deduplication
  does not imply pooled reactions, quantities or stock availability.
- `set.json`: portable membership, reusable after moving the whole packet.

In this loop series the loop sequence and count change. Recorded regional
sequences outside the loop, regional contacts, joins, terminal chemistry and
extension dimensions remain unchanged. Later coordinates shift. The source
oligo and reverse primer change to make these products; these material changes
do not imply additional sequence differences elsewhere in the hairpin.
Biological effects remain untested. Read each preparation's unresolved removal, reaction and
destination obligations before experimental use. The drawings depict recorded
pairing architecture, not predicted physical conformation.

Python exposes the same workflow through `prepare_construction_family`,
`execute_construction_family(..., continuation="sole-witness")` and
`select_construction_set`. Each opaque packet provides `json_bytes`,
`report_text` and create-only `write(path)`. See the
[public API](../reference/python-api.md) and [example recipe](../../examples/complete-construction/family.py).

## Open one portable comparison

```bash
hop-design construction report-family build/scaffold-family/executed --selection build/scaffold-family/set.json --baseline loop3 --edit short-primer:loop3 --out build/family-report
```

`report.pdf` contains the requested and obtained family, explicit membership,
an authored alternative, matched closing-region crops and actual product stages.
`report.md` is the offline relative-link index to editable page SVGs, exact
preparations, consolidated orders and the portable set request. Move the whole
folder to preserve those links. `summary.json` retains every member and choice,
requested/effective/achieved geometry, scoped diagnostics and typed comparisons.
Large rosters paginate rather than silently omit members. Raw captured source
artifacts in `family/` are provenance; the report regenerates its reading surfaces.

The selection and baseline are optional. With neither, the report shows all
outcomes without choosing a design. `--baseline` explicitly chooses a comparison
reference; it is not an optimum. Repeat `--edit SOURCE:TARGET` to describe an
intentional request change. An edit does not alter either saved request, rerun
search, select its target or identify a uniquely necessary repair. A failed
continuation has no complete product for sequence comparison.

The loop enlargement counts nucleotides. Regional comparison separates literal
sequence changes from movement of half-open coordinates. A unique minimum-edit
display alignment can highlight additions, removals and substitutions. Repeated
bases can make that correspondence ambiguous; HOP then shows the sequences
without inventing a changed position. Larger alignments retain exact sequences
and an explicit unresolved comparison budget. Neither display establishes
mutation history or a biological effect.

Verification replays the saved bounded local and complete authorities and
reconciles them with the family request and selections. Rendering then performs
no new design search. Stale/foreign selections, modified geometry summaries,
missing authorities and unsafe inventories reject before publication. Historical
producer identity is retained separately from the current verifier/renderer and
its library/font versions; recorded provenance is not a signed attestation.

To change requirements: edit a copy of `family.json`, run `prepare-family`, read
effective domains/conflicts, run `execute-family` into a new directory, then
report that outcome. Explicitly edit conflicting hard requirements or domains;
HOP never widens them. Select only result-bound choices present in that saved
family.

## Find preparations that preserve the comparison

If complete members disagree on a required property, hold one explicit complete
reference fixed and evaluate a bounded set of alternative preparations:

```bash
hop-design construction match-family build/family-outcomes --reference-member loop3 --reference-choice 0 --max-continuations 8 --out build/matching
```

Open `matching/report.md`. Each complete candidate links its whole hairpin,
preparation and agreement with the reference. Failed and incompatible candidates
remain visible. The summary records original choices, local coverage, examined
pairs and unexamined pairs. Matching uses the same requests, permissions and
material policies. An omitted local search runs under the original bound; this
command does not widen its domain or quota. Roster ordering does not determine
the reference or member visitation order.

The continuation budget applies to recorded local witness pairs across all
non-reference members. A completed sweep of those pairs can still have incomplete
local coverage. No match means no match among the examined preparations for this
reference; it does not establish that the requested family is impossible.

Choose explicitly. Copy the reference and desired candidate's `selection` fields
from `summary.json` into a `hop.construction-set/v1` request; preserve the listed
shared requirements. Put that request beside the matching directory and prefix
each relative path with `matching/`. Run `select-set` to retrieve the set. To put
a chosen candidate in a revised family report, use `reconcile-family` with its
`candidates/MEMBER/PAIR/outcome` folder, then `report-family`. The original
requests and failed or incompatible outcomes remain in the history.

This runnable example begins with 7- and 8-bp complete preparations, declares
7 bp as the reference, and retrieves a matched loop series:

```bash
uv run --locked python examples/complete-construction/match_family.py --out build/matched-family
```

Compare `before/report.pdf` with `comparison/report.pdf`. The caller in this
example explicitly selects the sole compatible examined alternative; HOP's
matching API does not select it. Python exposes the same operation as
`match_construction_family(path, reference_member="loop3", reference_choice=0,
max_continuations=8)`.

Preview conflicts identify both the member dimension and its exact canonical
declaration, including permitted geometry and inherited hard requirements.
Change the named member, or explicitly revise the relevant permission or
requirement while retaining the others. Re-run `author-family` or `prepare-family`
and inspect the resulting intersection. These are suggested edits, never automatic
relaxations.

## Reconcile an explicit continuation

A member with multiple local witnesses stays `selection-required`. Discover any
missing local result, inspect the choices, then use `construction continue` with
explicit result-bound witness IDs. Admit that complete outcome into a new family:

```bash
hop-design construction reconcile-family build/family-outcomes --source-member choices --outcome build/continued --preferred-loop-nt 4 --out build/revised-family
hop-design construction report-family build/revised-family --baseline choices --out build/revised-report
```

`--preferred-loop-nt` is optional. It records a caller-declared preference after
explicit witness selection and checks the completed hairpin against that value.
It does not select a witness. Omit it if no such preference was declared; the
report will not infer one. Revision reports show the available recorded local
choices, scoped earlier outcome and resulting complete preparation.

This operation does no new search or automatic selection. It verifies the exact
input request, local pair and complete result. `history/parent/` preserves the
original stopped family and its manifest. A changed request requires both
`--member NEW_NAME` and `--revised-request FAMILY_JSON`; that roster must retain
every original member and add the edited alternative. Original failures remain
visible. The revised family still has one base: an edit must be expressible
without changing any original member request. Different base material policies
or endpoints require a separate family. Author a new set from the revised result-bound choices to retrieve it.
Foreign inputs, stale witnesses, changed original requests or forged ancestry
reject before publication. Up to 16 revisions can be nested within packet limits.

The public demonstration declares a 4-nt loop preference, explicitly selects
that local witness, reconciles it and retrieves its preparation:

```bash
uv run --locked python examples/complete-construction/continue_family.py --out build/family-recovery
```

Python provides `project_construction_family_report(path, selection=...,
baseline="loop3", edits=(("short-primer", "loop3"),))` with `json_bytes`,
`report_text` and create-only `write(path)`. Inputs are read-only. The supported
family endpoints share the current single-loop portrait contract; no exposed-end
hairpin topology is inferred. See the [report contract](../reference/family-report.md).
