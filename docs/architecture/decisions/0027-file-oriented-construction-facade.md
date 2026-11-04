---
doc_id: hop-adr-0027
title: ADR 0027 - Compile construction from strict files behind a narrow facade
intent: Give external callers one replayable construction entrypoint without exporting the internal molecular ontology.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-11-01
doc_type: decision
amended_by: hop-adr-0028
---

# ADR 0027: Compile construction from strict files behind a narrow facade

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

Payload-centered construction discovery now produces exact local authorities,
complete route realizations, portable bundles, and neutral scientific
projections. Those competencies were reachable only through internal model and
design modules. An external caller would have needed to construct embedded
design authorities and connect local result identifiers by hand.

Publishing those internal request, result, molecular-state, and manifest models
would make the complete ontology a supported user surface. It would also let a
source document claim a design authority that HOP had not independently loaded
and verified.

## Decision

`hop_design.construction` is the file-oriented construction facade. The caller
provides one strict `hop.construction-source/v8` JSON or YAML file and one
separate verified design-bundle path. HOP loads the design authority, discovers
and verifies the declared foldback and optional basal neighborhoods, derives
the source ssDNA and source-preparation primers under their declared policies,
produces the exact source duplex, optionally binds one selected replay-verified
source partition, resolves PCR endpoint auxiliaries under their declared
policies, composes the route, and returns an opaque `ConstructionCompilation`
receipt.

The source document owns local requests, source-preparation policy,
endpoint-dependent auxiliary-resolution policy, oriented endpoint release,
whole-route constraints, and finite enumeration policy. Source preparation
uses one source ssDNA and two source-preparation primers to derive the exact
duplex that enters downstream construction. Endpoint PCR primers remain
separate auxiliary materials and appear only for PCR-bearing endpoints. Their
adapter and primer policies are explicitly `derive`, `constrain`, or `fixed`.
Derived and constrained endpoint primers must bind invariant non-payload
construction sequence, and caller-authored handles remain explicit rather than
being selected through an implicit score. The source cannot author a design
authority, result identifier, realization
identifier, projection choice, output path, timestamp, or environment record.
Direct, PCR, and clone-ready endpoints have fail-closed structural requirements.

The exact public allowlist is:

- `BasalSequenceSpace`;
- `ConstructionCompilation`;
- `ConstructionProjection`;
- `ConstructionSelection`;
- `FoldbackSequenceSpace`;
- `LocalNeighborhoodDiscovery`;
- `LocalNeighborhoodBatch`;
- `LocalRealizationChoice`;
- `PreparedConstructionRequest`;
- `ProtectedRoot`;
- `SourcePartitionDiscovery`;
- `VerifiedConstructionBundle`;
- `compare_constructions`;
- `compile_construction`;
- `compile_construction_from_local_realizations`;
- `compile_design_from_local_realizations`;
- `discover_foldback_sequence_space`;
- `discover_basal_sequence_space`;
- `discover_local_neighborhood`;
- `discover_local_neighborhoods`;
- `discover_source_partition`;
- `discover_construction_source_partition`;
- `list_local_realizations`;
- `load_verified_construction_bundle`;
- `load_verified_foldback_sequence_space`;
- `load_verified_basal_sequence_space`;
- `load_construction_selection`;
- `load_verified_local_neighborhood`;
- `load_verified_source_partition`;
- `prepare_construction_request`;
- `project_basal_feasibility`;
- `project_basal_minimum_overhead_matrix`;
- `project_complete_construction_summary`;
- `project_construction_navigation`;
- `project_construction_trajectory`;
- `project_hairpin_portrait`;
- `project_foldback_feasibility`; and
- `project_retained_overhead_frontier`;
- `project_source_partition_certificate`; and
- `select_construction_realization`.

Receipts expose only scalar identity and accounting plus create-only writing.
Projection packets expose deterministic JSON, optional CSV, and SVG bytes.
Selected trajectories also expose an overview through `inspection_text` and
`inspect_end(product_end, base_index=None)` for a released end's recorded
material origins and cuts. The CLI uses the same text reader. These methods
select facts from the typed trajectory; they add no molecular authority,
serialized schema, independent lineage reconstruction or model constructors.
`ProtectedRoot` retains an input directory's filesystem identity across
verification and protected publication. Its mechanics remain in the existing
publication owner; it is neither a molecular model nor portable evidence.
Selection references expose only the source result identity, one accepted
materialized-realization identity, and canonical JSON. They remain
non-authoritative: creating or loading one requires a verified construction
receipt, and loading cross-checks both identities against that receipt.
`LocalRealizationChoice` exposes immutable inspection facts, including the
achieved geometry and the family identity required by compilation. Explicit
filters and ascending preference keys operate on recorded witnesses only;
they neither search unenumerated sequences nor certify a complete construction.
The original receipt remains necessary to compile a selected identity.
`compare_constructions` consumes two verified receipts and explicit accepted
realization identities. It returns a read-only Markdown comparison of recorded
material, retained-sequence, processing-order, and endpoint properties. It is
not a serialized molecular authority, ranking, or equivalence certificate.
Source, result, projection, molecular-state, and bundle-manifest constructors
remain internal. Loading a portable construction bundle performs both
integrity and semantic replay, so the facade does not add a redundant verify
verb.

## Consequences

The molecular-editing extension adds `PreparedMolecularEdit`,
`MolecularEditEvaluation`, `author_molecular_edit`, `prepare_molecular_edit`,
`execute_molecular_edit` and `select_molecular_edit`. An edit captures its original
request and stage-qualified changes; preview never searches. Execution composes
bounded discovery. Retrieval replays the original molecular authorities and
reconstructs the saved sequence views before admitting explicit selections.

The exact-family extension adds `PreparedSequenceFamily`,
`SequenceFamilyEvaluation`, `prepare_sequence_family`, `execute_sequence_family`
and `select_sequence_family`. A finite IUPAC stem domain expands to required exact
members before molecular execution. Paired arms remain derived; shared flanks
and material roles are verified by the existing set contract on explicit
selection. The local editor is a caller of these file-oriented operations, not
another molecular engine. See the [folded-sequence guide](../../guides/edit-folded-sequences.md).

All callers can use the same installed public interface
without copying HOP models or importing private modules. A projection must be
requested from an opaque verified receipt; trajectory projection additionally
requires one exact accepted realization identity and never auto-selects an
exemplar.

The projection operations remain the reversible navigation data surface. The
`hop-design construction` CLI consumes those projections to summarize, group,
filter, explicitly sort, inspect, and select exact realizations without changing
result authority or introducing a hidden rank. Its row limit affects display
only and does not alter search status, accounting, or membership.

An explicit selection writes one create-only JSON file at the caller-supplied
path. It does not mutate, subset, reseal, or supersede the complete result, and
it cannot be reopened without the verified result that establishes membership.

Standalone local-neighborhood discovery returns one replay-verified family
receipt. It establishes only the declared foldback or basal neighborhood and
cannot be interpreted as a complete-route authority.

Exhaustive foldback population discovery may return compact exact sequence sets
through `FoldbackSequenceSpace`. Its strict file request declares finite geometry
and execution bounds; every exact payload/geometry/strand case retains its raw
population, per-program support, and admitted union. Loading repeats complete
deterministic discovery. Computational exhaustion raises without a completed
receipt, and enzyme aliases cannot multiply sequence configurations. Explicit
member recovery uses ordinary full molecular realization for one case, sequence
rank, and supporting program. These operations retain local claim scope and do
not expose internal model constructors or rank biological performance.

An ordered finite collection may use `discover_local_neighborhoods` for
producer-bound checkpoints. `LocalNeighborhoodBatch` exposes execution counts
and iteration over replay-verified individual receipts. It is not a merged
search authority: each query retains its independent scope and status.
Execution storage belongs to `design.construction.execution`; molecular
validation remains with the existing family authorities.

For a PCR-bearing endpoint, a caller may explicitly select one realization
from each verified local receipt and compile their exact molecular junctions
into a route-neutral design authority. The selection operation returns the
existing `Compilation` type. Search-result identities, execution bounds, and
reaction chronology do not enter the design specification or plan identity.

The source compiler may report complete, infeasible, or truncated discovery.
None of those digital states establishes physical construction, QC,
destination compatibility, biological activity, or route performance. This is
an intentional prerelease public-surface addition with no compatibility alias
for internal import paths.

`PreparedConstructionRequest` records translated input, not a verified molecular
receipt. `prepare_construction_request` shares one strict intent translator with
the CLI and expands to existing source contracts. See
[ADR 0037](0037-product-request-authoring.md) for the authoring boundary.

`ConstructionRequestExecution` and `execute_construction_request`, `continue_construction_request` add an explicit
bounded continuation over those same authorities. Their report is not a new
molecular authority; the delivery includes the local results, design bundle and
any complete-construction bundle. See [ADR 0038](0038-bounded-request-execution.md).

## Structured selected-route comparison

`PreparedScaffoldDiscovery` and `prepare_scaffold_discovery` expose desired
scaffolds and explicit preparation-change permissions before search.
`ScaffoldDiscovery` and `discover_scaffolds` evaluate bounded strict branches.
`select_scaffold_options` retrieves explicitly named members through ordinary
replay-verified construction sets. The [product-first delivery plan](../../dev/plans/product-first-discovery.md)
records the implementation boundary and remaining work.

`project_construction_comparison` returns an opaque `ConstructionComparison`
with canonical JSON and the same human report used by `compare_constructions`.
The projection binds both selections, exact material-role changes and regional
hairpin facts. Regional sequence equality is distinct from coordinate equality.
A valid route outside the portrait domain retains its preparation comparison
and an explicit unsupported-region reason; no replacement structure is inferred.


## Bounded scaffold families and selected sets

The opaque `PreparedConstructionFamily`, `ConstructionFamilyExecution` and
`ConstructionSet` compose existing file-oriented operations. Named variations
narrow declared local domains and hard product requirements; contradictions do
not start discovery. A finite roster has aggregate node/continuation limits.
Every execution outcome retains scope, identity and producer. Display ordering
is separate from explicit set membership; scientific interpretation belongs to
the caller. A set verifies all selected members before atomic publication,
retains their complete authorities and consolidates only chemically identical
ordering specifications. Shared ancestry protection covers every input root.
The set does not become a new search authority or establish pooled manufacture.
Public authoring is documented in the
[family walkthrough](../../guides/compare-scaffold-families.md).

Their public operations are `prepare_construction_family`,
`execute_construction_family` and `select_construction_set`.


The opaque `ConstructionFamilyReport` and `project_construction_family_report`
operation admit a saved finite family and optional exact set selection. Admission
replays current molecular verification and checks request/result correspondence;
it is separate from pure report rendering. The report uses existing portraits,
trajectory lineage and construction comparisons. Regional display alignment is
bounded and discloses ambiguity; it does not become molecular authority. Export
owns static SVG page composition and deterministic vector PDF encoding. ReportLab
and svglib are runtime rendering dependencies, with a bundled font and renderer
versions recorded in report provenance. No external SVG or network resource is
admitted by the PDF encoder. Study-owned examples and scientific selection remain
outside HOP.

`author_construction_family` compiles a strict scaffold comparison brief to the
existing family request and preview. `reconcile_construction_family` returns an
opaque `ReconciledConstructionFamily` with verified explicit continuation or
edited-alternative lineage and the preserved parent packet. These operations
remain file-oriented and do not add search or automatic selection. See
[ADR 0039](0039-scaffold-comparison-and-revision.md) for the projection versions,
input contract and revision admission rules.

`match_construction_family` returns an opaque `MatchedConstructionFamily`.
The caller fixes an explicit complete reference and continuation budget; matching
preserves every request and requirement and leaves selection explicit. See
[ADR 0041](0041-reference-bound-family-matching.md) for scope and packet contracts.

## Complete scaffold options

`ConstructionOptions` and `ConstructionOptionSets` are opaque derived packets.
`explore_construction_options` evaluates bounded complete preparations from one
product request before choosing local witnesses. `find_construction_option_sets`
finds comparative groups in that evaluated pool. `select_construction_options`
resolves explicit visible labels into the existing `ConstructionSet` contract,
with optional comparison intent carried through to retrieval. No operation
chooses a winning molecule or changes molecular requirements. See
[ADR 0042](0042-complete-scaffold-options.md).

The explicit selection API also exports `ResolvedStageControl`,
`PriorMaterialReuse` and `SelectedPreparationReference`. Callers can construct
these strict declarations without importing internal model modules. Their
stage, membership and reference semantics are described in
[ADR 0048](0048-stage-controlled-required-panels.md).

The comparison brief adds `PreparedScaffoldComparison`, `ScaffoldComparison`,
`prepare_scaffold_comparison`, `assess_scaffold_comparison`,
`execute_scaffold_comparison` and `select_scaffold_comparison`. These compose
existing verified discovery and explicit set retrieval; see
[ADR 0044](0044-molecular-comparison-briefs.md).

Conditional exploration adds opaque `ScaffoldExploration`, `ScaffoldVariantChoices`
and `ScaffoldVariantView` receipts with `load_scaffold_exploration`,
`query_scaffold_variants`, `project_scaffold_variant` and `select_scaffold_variants`.
These project and filter existing complete authorities; see
[ADR 0049](0049-conditional-variant-exploration.md).

Inspection and required comparisons add `ScaffoldInspection`, `inspect_scaffold_variant`,
`load_scaffold_variant_choices`, `ScaffoldVariantComparison`, `compare_scaffold_variants`
and `select_scaffold_variant_comparison`; see
[ADR 0050](0050-intent-preserving-inspection-and-comparison.md).

The conditional-preview extension adds `ScaffoldVariantPreview` and
`preview_scaffold_variant`. It resolves an observed neighborhood variant against
all current constraints without selecting a preparation or editing permissions.
Ambiguity, missing phases and focus correspondence remain explicit, as described
in [ADR 0050](0050-intent-preserving-inspection-and-comparison.md).

The all-state projection adds `ScaffoldAtlas` and `inspect_scaffold_atlas`.
It composes already verified inspections, transitions and material inputs for
one compatible preparation. The same exact vector scene serves API, CLI and
browser clients. It does not expose authority models, choose a preparation,
alter the conditional query or derive additional molecular states. See the
[conditional guide](../../guides/explore-conditional-variants.md#export-the-complete-atlas).

Parameterized exploration adds `ScaffoldParameterEvaluation` and
`evaluate_scaffold_parameters`. This explicit bounded operation intersects selected
parameters with inherited permissions and preserves the prior pool in an immutable
extension packet; it never joins independently chosen molecular parts. See
[ADR 0049](0049-conditional-variant-exploration.md#parameterized-envelope-projection).

Explicit envelope revision adds `ScaffoldEnvelopePreview`, `ScaffoldEnvelopeEvaluation`,
`preview_scaffold_envelope_revision`, `load_scaffold_envelope_revision` and
`evaluate_scaffold_envelope_revision`. Domain browsing adds `ScaffoldParameterDomain`
and `query_scaffold_parameter_domain`. These retain field-bound permission edits,
preview/evaluation separation and replayed original evidence; see
[ADR 0051](0051-explicit-envelope-revisions.md).

Resumable interface surveys add `evaluate_interface_survey`,
`inspect_interface_survey`, `query_interface_survey`, `verify_interface_survey` and
`retrieve_interface_survey_witness`. These accept strict files and explicit
execution budgets, return versioned JSON summaries, and rehydrate selected
ordinary construction receipts on demand. The checkpoint index remains derived
bookkeeping; aggregate molecular coverage requires replay. See
[ADR 0052](0052-resumable-interface-surveys.md).

Survey inspection also exposes `InterfaceSurveyAtlas` and
`inspect_interface_survey_atlas`. The exact target, step and materialized identity
bind a selected complete path to the shared molecular atlas and teaching
projections. This replays the selected witness without extending the survey or
adapting its domain to the small-roster workflow.

`InterfaceSurveyChoices` and `load_interface_survey_choices` support repeated
conditional queries against an admitted immutable coordinate snapshot. Its
`query` method shares the file query's semantics without reopening the checkpoint.
Loading a new snapshot is explicit; retrieval still replays the selected witness.

Optional molecular intent adds `ResolvedDesignRequest`, `resolve_design_request`,
`DesignChoices`, `discover_designs`, `load_design_choices` and
`continue_design_discovery`. Resolution captures the user's requirements and
effective construction permissions. The shared choice interface delegates to the
existing insert-survey or hairpin-discovery owner, retaining exact selection,
figure and material identities. It does not weaken exact compilation or require
end words before discovery. The insert owner retains its resumable survey.

`DiscoveryProgress` reports committed work through an optional observer shared by
the API, CLI and browser worker. Cooperative stopping preserves saved work and
ordinary continuation. `DiscoveryCancelled` identifies a stop before the first
result snapshot is available; it does not establish molecular exclusion. Feedback
is invocation-owned and does not alter preparation identity or search permissions.

`DesignRevisionPreview`, `preview_design_revision` and `load_design_revision`
expose compact permission edits and their dependent changes. A preview retains the
original request and requires explicit execution into a new discovery. Loading a
saved preview verifies its request and revision before execution can write results.
The hairpin owner appends immutable snapshots of a fully examined local-pair
prefix. Requested execution effort and first-choice stopping are recorded
separately from molecular permissions and the native prefix budget. Resumption
verifies and reuses prior outcomes, then evaluates only the remaining pairs.
An interrupted publication leaves the last committed snapshot authoritative;
unpublished work can be recomputed. Create-only publication rejects competing
writers rather than replacing a snapshot. Earlier selections bind to the original
snapshot in that discovery's history.

During generation, replay-verified candidate receipts pass through the existing
discovery and variant projection owners. Returning the just-produced choices binds
the written files to that exact packet instead of replaying every candidate again.
Reopening on disk still performs independent admission. Within one admission,
candidate local authorities must match the enclosing admission's verified bytes
before their receipts are reused; identifiers alone are insufficient.

## Frozen inspection editions

`combine_design_discoveries` captures one read-only edition from disjoint
discovery jobs covering an explicit parent request grid. It requires unchanged
molecular permissions, effort and producer; empty jobs remain in coverage.
Captured preparations use the existing replay and handoff path. Writable
checkpoints and their independent continuation histories are not merged.
Aggregate negative replay remains explicit and separate from capture.

`freeze_design_choices` provides file-oriented capture and explicit read-only
recorded-source admission, without authorizing foreign-producer execution.
`AtlasEdition` and `load_atlas_edition` expose captured choices, molecular drawings
and original materials independently of live producer admission. They share the
selection and retrieval verbs while excluding new execution. See [ADR 0056](0056-inspectable-atlas-editions.md).
