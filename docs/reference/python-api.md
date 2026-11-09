# Python API

Use `hop_design.construction` to discover complete preparations and retrieve
materials. Follow the [worked tutorial](../guides/discover-designs.md) for runnable
CLI and Python examples, then use this reference for field and operation details.

- [Discover complete designs](#discover-complete-designs)
- [Inspect and share preparations](#frozen-atlas-editions-and-guided-exploration)
- [Compile sequence anatomy](#compile-and-integrity)
- [Search local construction regions](#payload-centered-construction)

## Discover complete designs

Use `hop_design.construction.discover_designs(intent, destination,
max_evaluations=64)` to find complete preparations around an exact stem. The
intended product is required; end words are optional. A named or supplied context
declares geometry, methods and materials. `resolve_design_request(intent)` returns
the authored intention and effective permissions without searching.

The returned `DesignChoices` connects `query`, `explain`, `select`, `sample`, `figure`,
`atlas` and `retrieve`. Pass one selection to both figures and retrieval.
`select` accepts a returned path or exact preparation identity. Filtering a
retained pool performs no search. `load_design_choices(directory)` reopens the
whole discovery directory and validates its request and producer bindings. Keep
the original HOP/Python producer environment for live results. For inspection
independent of that producer, [save a fixed preparation collection](../guides/share-atlas-edition.md)
before changing environments. `find_more` or
`continue_design_discovery` explicitly resumes discovery under the same permissions.

For a released insert, an intent can also name a verified preparation to try
first: `"prefer_preparation": {"bundle_path": "known/construction",
"selection_path": "known-selection.json"}`. Paths are relative to the intent
file, or to the working directory for a mapping. This orders discovery; it does
not fix materials, narrow the molecular envelope or import an existing result.
HOP captures the reference, locates its admitted sequence assignments, and runs
them through the ordinary complete compiler before continuing the broader search.
An incompatible reference is reported explicitly. The captured request and
checkpoint remain portable after the original reference moves. This preference
uses the `paired_scaffold_completions` search mode.

Exact-stem discovery also accepts `on_progress=observer` and
`should_stop=stop_check`, including on `choices.find_more(...)`. The observer
receives immutable `DiscoveryProgress` values (`hop.discovery-progress/v1`):
product, phase, committed evaluation count, count added by this call, execution
budget and final termination reason. These counts describe examined work, not a
percentage of the molecular space or a count of valid preparations.

The stop check returns a Boolean. Cancellation finishes the current molecular
evaluation and preserves the verified prefix for continuation. Inserts commit
each evaluation; hairpins publish a contiguous snapshot before reporting its
counts as checkpointed. If hairpin discovery stops before its first snapshot,
`DiscoveryCancelled` reports that outcome; the saved intent can still be passed
to `continue_design_discovery`. Observer errors propagate, with already committed
records retained. Feedback is invocation-local and does not change permissions,
saved search order or molecular identity. Callbacks should be brief; rendering
and network work belong outside them. Family allocation and staged permission
revision do not currently expose these callbacks.

An optional `objective={"kind": "diversity", "parameters": ["loop_nt"]}` prioritizes
contrasts within those permissions. The same contract supports insert, direct
hairpin and adapter-ligated hairpin discovery. `query()["search_objective"]` reports
the stage-specific dimensions and observed classes; continuation retains the
objective. See [scaffold alternatives](../guides/explore-scaffold-alternatives.md)
for supported dimensions and how search limits differ from molecular permissions.

`preview_design_revision(intent, changes)` and `choices.revise(changes)` return a
`DesignRevisionPreview` with explicit before/after declarations and conflicts.
Arm ranges, characterized methods, joint end placements and retained-length limits
can be revised without replacing the authored stem or hard requirements.
`load_design_revision(directory)` verifies and replays a saved preview. Calling
`preview.execute(new_directory, ...)` explicitly discovers under the captured
revision, keeping the original result untouched. `preview.write(directory)` only
saves the preview; it performs no search.

`explain(query=None)` returns a `hop.design-explanation/v1` value: requested
product, distinct product and preparation counts, up to five identified
preparations, scoped coverage, applicable parameters and next actions. It neither
selects a preparation nor runs a search. Parameter entries retain their stage,
units, dependencies, equivalent measurements, declared domain and observed values.
A missing observation is not an applicability decision.

The design boundary rejects release-only predicates for hairpin endpoints before
selection or export. Native survey and scaffold query formats remain supported;
`ScaffoldVariantChoices.explain()` describes the exact native query, including
its preservation controls. Its context identity names the admitted request digest.

Products are `released_insert`, `hairpin` (direct ssDNA hairpin), and
`adapter_ligated_hairpin`. Hairpin discovery delegates to the scaffold backend;
it resumes a verified prefix of up to 64 continuations. For these two endpoints,
`first_choices=N` on `discover_designs`, `continue_design_discovery` or `find_more`
returns after N new complete choices or the evaluation limit. `query()["execution"]`
records the requested effort, stopping policy and examined prefix. Failed attempts
remain in coverage. Each continuation writes an immutable snapshot; retrieval and
atlas export resolve earlier explicit selections against their original snapshot.
The insert backend retains its existing resumable evaluation batches and does not
accept `first_choices`. See the [introductory workflow](../guides/discover-designs.md).

For hairpin and insert choices, `preserve(reference, stage=..., except_neighborhood=...)`
returns a `hop.design-refinement/v1` query bound to the exact saved reference and
snapshot. It holds the other molecular neighborhoods at the named `hairpin` or
`endpoint` stage. It creates a new query rather than inheriting the filters used
to locate the reference; the original intent and selection remain unchanged.
Pass it to `query`, `explain`, `sample`, `select` or `figure`. The query reports
molecular and material changes separately. Preserved selections use
`hop.hairpin-design-selection/v2`; ordinary v1 selections retain their meaning.
Insert preservation uses `hop.insert-design-selection/v1`, wrapping the native
survey record and reference. Insert set selections use `hop.design-set-selection/v2`.
Both remain retrievable after continuation; exact membership and requirements are
reassessed instead of selecting a newly ranked set. Existing native survey and
hairpin selections keep their original contracts.

The atlas's `construction_cost` projection reports stage-specific added nucleotide
spans, exact order identities, shared roles and required terminal chemistry.
`construction-cost.json`, its report and CLI summary expose the same values.

`compare(request, query=None)` assesses explicit required members within the
admitted choices, using the existing comparison engine. A
`hop.design-comparison-request/v1` declares `stage`, `required_members` and
`max_group_evaluations`, with optional shared properties, material roles and
stage controls. It returns available sets, missing members and assessment
coverage without searching or selecting. A preservation query and comparison
must name the same stage.

`select_set(comparison, set_label=..., baseline=...)` re-assesses the saved
comparison and returns a `hop.design-set-selection/v1` value. Its named `members`
are ordinary exact selections usable with `figure` and `atlas`. Pass the whole
selection to `retrieve` for the verified set, oligos, chemistry and comparison
records. Retrieval validates membership and controls again. These operations
reject unsupported discovery backends explicitly; they do not relax controls or
convert missing members into optional ones. The
[loop comparison example](../guides/discover-designs.md#compare-loops-while-holding-the-scaffold)
shows the complete public lifecycle.

## Conditional variant exploration

`load_scaffold_exploration(result_directory)` admits a verified discovery or edit
result once and returns an immutable `ScaffoldExploration` receipt.
`evaluate_scaffold_parameters(pool, choices, max_branches=...,
max_continuations_per_branch=...)` returns a create-only
`ScaffoldParameterEvaluation`. It intersects v2 parameter selections with the
captured original envelope and retains the original pool alongside the additional
bounded results. Reload its written directory with `load_scaffold_exploration`,
then reissue the captured query using the new `result_digest`. Old preparation
labels and the fixed reference remain valid. Evaluation without a selected
parameter, stale choices or contradictory inherited restrictions raises.

`query_scaffold_parameter_domain(pool, choices, request)` returns a
`ScaffoldParameterDomain` page. The request names `key` and optional `length`,
`prefix`, `offset`, `limit` (at most 64). Domain permission and recorded complete
support are separate. Unfixed word domains require a permitted loop length.

`preview_scaffold_envelope_revision(pool, choices, revision_path_or_mapping)`
returns `ScaffoldEnvelopePreview`. `load_scaffold_envelope_revision(pool, directory)`
re-derives a saved preview and rejects stale or altered data.
`evaluate_scaffold_envelope_revision(pool, preview, max_branches=...,
max_continuations_per_branch=...)` returns `ScaffoldEnvelopeEvaluation`. It requires
a ready preview, preserves prior evidence and uses explicit changed permissions.
Reload its directory with `load_scaffold_exploration`; the revised request governs
future evaluations while the union retains historical preparations and their
original authorities. A conflict is never resolved by clearing a preservation
control. All writes are create-only.

The returned `choice_space.axes` supplies the shared parameter definitions. Query v2
accepts `parameters=[{"key": "self_paired_arm_bp", "minimum": 7, "maximum": 8}]`
in addition to the v1 fields below. Integers use inclusive ranges; categorical
`values` use OR, with AND across keys. Selection and further evaluation remain
separate operations. See the [construction-envelope walkthrough](../guides/explore-conditional-variants.md#explore-the-construction-envelope).

`query_scaffold_variants(pool, query_path_or_mapping)` returns
`ScaffoldVariantChoices`: `json_bytes` reads query facts immediately, while
`report_text` and `write(new_path)` create human/portable views when requested.
`primer_boundary_views` returns representative source-only SVGs grouped by
primer, required length and available length; every examined continuation remains
in `choice_space.primer_boundaries`. Portable exports include
`primer-boundaries.svg` when such failures exist. Each failure retains its result,
local realization identities, disposition ordinal and outcome path. Complete
alternatives are separate preparations from the same declared branch.

Axis definitions include `canonical_key`, `design_role`, `role`, `glyph_frame`, `representation`, `boundaries`,
`dependencies` and `equivalent_measurements`. Axis observations include
`observed_values`, `observed_variation`, `fixed_by_request` and `domain_status`.
Source forward/reverse primer required/available spans and required/achieved
adapter annealing have separate keys. These are stage-qualified measurements;
their presence as query coordinates does not make every quantity an independently
editable generating parameter.

`inspect_scaffold_atlas` and `inspect_scaffold_variant` also return the same
preparation-bound `teaching` projection and write `teaching.svg`. The drawing
shows the selected hairpin and, when present, the released insert for its ends and
gaps. Recognition footprints remain on the hairpin. Source/association, hairpin
and insert `frames` retain the coordinate meanings; only `scenes` are drawn.
Primer inputs and the processing sequence belong to the full atlas. Parameter entries
reference exact `parameter_locations` by `location_key`; nonspatial entries remain
contextual. A differing translated threshold retains its original domain and
sets `effective_requirement_differs`.

Atlas packets also write `overview.svg`: one compact, unsplit hairpin, used above
the parameter plot in the browser and selected figure exports. It retains the
hairpin bases and recognition footprints. Later release words and gaps are
projected through recorded ancestry and labeled as release coordinates; they are
not exposed hairpin ends. Translucent polygons connect located features to their
plotted axes. Detailed `teaching.svg` and readable pages remain separate exports.
The browser places these shared coordinates without deriving molecular meanings.

The strict `hop.scaffold-variant-query/v1` requires `result_digest`, `stage`
(`hairpin` or `endpoint`) and `focus` (`loop`, `closing`, `assembly`, `stem`,
`interfaces`). Optional `pins` name neighborhood and allowed `variant_ids`;
`controls` name stage and property (`non_loop_sequences`, `non_loop_pairing`,
`terminal_chemistry`, `product_identity`). Controls require a fixed `reference`
option label. Unknown fields, duplicate pins, unknown/wrong-stage variants and
stale result identities raise. Replacement alternatives omit only the focused
pin; `compatible_options` applies the complete query. Multiple products remain
unselected. Coverage and failed examined continuations retain their original scope.

`project_scaffold_variant(pool, choices, option_label=...)` returns a
`ScaffoldVariantView` with `json_bytes`, `svg_bytes` and create-only `write`.
Its preview must be compatible with the active query. It never changes the
reference or selects a product.
`select_scaffold_variants(result_directory, choices_receipt_or_directory,
members={name: option_label}, baseline=name)` re-admits the source, re-derives
choices and enforces all pins and controls before returning a `ConstructionSet`.
See the [walkthrough](../guides/explore-conditional-variants.md).

`load_scaffold_variant_choices(pool, directory)` re-derives a saved choice packet
against the admitted pool. Export retains protection of both source and choices.

`inspect_scaffold_variant(pool, choices, request_path_or_mapping)` returns
`ScaffoldInspection` with `json_bytes`, `svg_bytes` and create-only `write`.
Its strict `hop.scaffold-inspection-request/v1` names `result_digest`,
`query_digest`, one `option_label`, and `state`. State is `hairpin`, `endpoint`,
`source_material`, a semantic processing phase, or an exact ID from `molecular_state.available_states`.
Optional `focus` is `{state_id, strand_id, index}` with a zero-based nucleotide
index. Only recorded addresses are accepted. Inspection never edits the query.
Unknown/unavailable states, unknown addresses, stale identities and excluded or
ambiguous preparation labels raise. Each base carries its recorded ancestry,
paired addresses and neighborhood; absent correspondence is explicit.

`preview_scaffold_variant(pool, choices, request_path_or_mapping)` returns a
`ScaffoldVariantPreview` packet. Its strict request binds `result_digest`,
`query_digest`, observed `variant_id`, and `state` (default `hairpin`). Optional
`option_label` explicitly resolves a preparation. Outcomes are `preview_available`,
`preparation_choice_required`, `excluded_by_constraints`, `state_unavailable`, or
`state_ambiguous`. Candidates retain every compatible preparation even when products
are identical. Only `preview_available` contains `inspection` and `projection.svg`.
No outcome changes the query, reference, required set or selected membership.
Unknown variants and stale identities raise. `focus` requires `focus_option_label`;
transfer requires a unique exact material identity and coordinate, otherwise
`focus_transfer` explains why it was cleared. The request never expands search.

`inspect_scaffold_atlas(pool, choices, request_path_or_mapping)` returns
`ScaffoldAtlas` with `json_bytes`, `svg_bytes`, on-demand `pdf_bytes` and create-only
`write(destination, *, print_pages=True)`. Saved exports include seven-inch
PDF/SVG pages with nucleotide text at least 8 pt and annotations at least 9 pt.
Wide scenes continue at recorded coordinate boundaries; `print-layout.json`
records each panel's base ranges and physical dimensions. `print_pages=False` skips
print rendering for browser previews without changing the molecular summary. Its strict
`hop.scaffold-atlas-request/v1` binds result/query digests and one compatible
`option_label`, with optional `{state_id, strand_id, index}` focus. The shared
`hop.scaffold-atlas/v1` projection contains every recorded state, consecutive
transitions, exact material inputs, a declared/achieved envelope and optional
fixed-reference comparison. Binding annotations identify recorded versus derived
templates; they add no molecular states. `request.json` preserves the generating
request. Stale digests, excluded options and unknown addresses raise.

Preview requests accept `state: "all"`, returning `inspection.atlas` and an
`atlas_transitions` array for a supplied `view_from`. Browser and preview CLI use
`all` by default; Python retains the documented `hairpin` default. Each drawn
occurrence includes preparation, state, strand and index; ancestry and comparison
links have separate meanings. Neither atlas inspection nor camera movement changes
the query or explicit retrieval membership.

`compare_scaffold_variants(pool, choices, request_path_or_mapping)` assesses
required sets through the existing bounded comparison engine. The strict
`hop.variant-comparison-request/v1` binds `result_digest` and `query_digest`,
requires `required_members` and `max_group_evaluations` (1–100,000), and permits
`max_sets` (1–256; default 64). Each member has a unique `name` and a selector:
`dimensions`, `loop_sequence` or `release_enzyme_id`. Optional `shared_properties`,
`preserve_material_roles` and stage-qualified `stage_controls` apply to the set.
`purpose` defaults to `distinct_substrates`; `preparation_alternatives` requires
identical products at the query stage. `grouped_substrates` uses explicit `groups`
and `between_groups: distinct`. External product references remain in the verified
comparison-brief workflow. The original search permissions are inherited from the
admitted result, never re-authored by this operation.

The returned `ScaffoldVariantComparison` exposes compatible sets, missing members,
group coverage and unchanged molecular-search coverage; no set is selected.
`select_scaffold_variant_comparison(result_directory, comparison_receipt_or_directory,
set_label=..., baseline=...)` re-admits source, re-derives the conditional query,
re-assesses all requirements and retrieves exactly the named set. Its portable
output includes `variant-comparison/` and `variant-comparison-selection.json`.

Conditional choice summaries also expose `preparations`: actual recorded enzyme
methods and requested/achieved interface distances for each complete preparation.
Achieved distances come from cuts and stem boundaries. `interface_coverage`
reports declared joint branches, local absence, rejected continuations, unexamined
work and query exclusions. It does not infer a universal nearest placement.

## Molecular edits

The construction facade exposes `author_molecular_edit(path, loop_sequences=...,
end_placements=..., end_words=..., basal_nick_enzyme_ids=..., release_enzyme_ids=...)`.
Each optional domain is a tuple; `end_placements` is a tuple of integer
`(left_bp, right_bp)` pairs. At least one region must be explicitly edited.
`prepare_molecular_edit(edit_path)` previews a saved edit;
`execute_molecular_edit(edit_path)` evaluates it. Both preserve the original request.
`select_molecular_edit(packet, edit_digest=..., members={name: option_label},
baseline=..., shared_properties=...)` returns an ordinary portable construction set.

`prepare_sequence_family(path)`, `execute_sequence_family(path)` and
`select_sequence_family(packet, members=..., baseline=...)` expand and retrieve
required exact members of a bounded IUPAC stem domain. All these receipts expose
`json_bytes`, `report_text` and create-only `write(path)`. See the
[runnable example](../../examples/molecular-editing/run.py) and
[molecular edit guide](../guides/edit-folded-sequences.md). The local editor is a
thin CLI-owned transport over these same public operations.

Callers with independent installations can use the
[external command and artifact interface](external-artifacts.md). Its named
file operations preserve the authorities below while avoiding consumer Python
model imports.

The file-oriented operations in `hop_design.api` are
`resolve_linear_source_method_file(source)`,
`compile_linear_source_method_file(source, output)`, and
`verify_linear_source_method_file(bundle)`. They return the named method's
canonical authority report through the existing compiler and replay path.
`design_report(receipt)` serializes admitted design authorities and
producer-computed checks. `runtime_identity()` returns installation provenance
and the executing package-content digest. The
[external artifact reference](external-artifacts.md) defines their authored
inputs, lineage bindings, and the distinction between recorded evidence and
fresh execution.

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

## Payload-centered construction

All operations and receipts in this section use `hop_design.construction`.

- `execute_construction_request(path, *, design_id, continuation="sole-witness")`
  returns an opaque `ConstructionRequestExecution`. The continuation argument is
  required: this policy only continues when every required local search records
  one witness. It neither ranks nor relaxes the request. `json_bytes` contains
  the scoped outcome and exact producer identity; `report_text` explains what
  was obtained or why execution stopped. Create-only `write(destination)` saves
  inputs, local results, and any design, complete-construction and handoff
  artifacts. Expected absence is a report, not an exception; malformed input
  remains an error. Independent hairpin execution requires explicitly authored
  `hairpin_basal_component` arms. See the [execution decision](../architecture/decisions/0038-bounded-request-execution.md).
- `continue_construction_request(path, *, design_id, foldback_path,
  foldback_realization_id, basal_path=None, basal_realization_id=None)` returns
  the same `ConstructionRequestExecution` from explicit verified choices. It
  checks the local inputs against the saved authored request before compiling;
  the request supplies payload, endpoint, exact hairpin arms and material policies.
  PCR-bearing endpoints require both basal arguments; direct hairpins reject them.
- `prepare_construction_request(path, *, compare_to=None) -> PreparedConstructionRequest` expands a
  strict `hop.product-request/v1` file into the existing construction source.
  `source_json_bytes` exposes canonical input; `report_text` separates required,
  derived and unresolved values. Create-only `write(destination)` saves both
  authored and expanded inputs. `preview_json_bytes` / `preview.json` expose
  the coupled footprint, contact permissions, annealing minimum and material
  policies. An explicit `compare_to` request adds field differences and both
  footprints. The output contains expanded inputs for subsequent discovery and
  construction. See the [authoring decision](../architecture/decisions/0037-product-request-authoring.md).

For repeated questions, load one verified construction receipt and reuse it:

```python
# Re-admit the construction before projecting its atlas.
receipt = construction.load_verified_construction_bundle("saved/construction")
trajectory = construction.project_construction_trajectory(
    receipt, materialized_realization_id=receipt.materialized_realization_ids[0]
)
left = trajectory.inspect_end("left")
right = trajectory.inspect_end("right")
```

The selected ID above is an explicitly addressed result entry, not a preference.
The receipt is an admitted in-memory snapshot. Reload to inspect current disk
bytes; every load still checks integrity and repeats semantic replay. No
persistent verification cache is used. Malformed side/negative-index CLI
arguments fail before replay; product-dependent bounds require the verified
product. Bundle loading reconstructs its manifest from the fresh replay result
without replaying that same result a second time.

- `project_basal_source_panel(receipt, realization_id=...) -> bytes` emits the
  existing neutral molecular panel as canonical JSON for one verified local
  basal realization. It preserves source coordinates and exact local pairing
  facts; route selection is separate.

- `compile_construction(source_path, design_bundle_path=...) -> ConstructionCompilation`
- `compile_construction_from_local_realizations(source_path, design_bundle_path=...,
  foldback=..., foldback_realization_id=..., basal=None,
  basal_realization_id=None, source_partition=None,
  source_partition_realization_id=None) -> ConstructionCompilation`
  loads one strict file and a separate verified design authority, discovers
  local neighborhoods, composes the bounded whole route, and returns an opaque
  write-capable receipt. Direct endpoints accept one selected foldback;
  PCR-bearing endpoints require selected foldback and basal realizations. An
  optional verified source-partition selection is an exact route constraint,
  not another Cartesian search dimension.
- `compile_design_from_local_realizations(...) -> Compilation` replays one
  explicitly selected foldback realization and, for a PCR-bearing endpoint,
  one explicitly selected basal realization, then derives their exact
  route-neutral design authority. The operation accepts no direct endpoint,
  does not select a realization, and does not carry search ids or bounds into
  design identity.
- `discover_local_neighborhood(source_path) -> LocalNeighborhoodDiscovery`
  runs one strict foldback or basal neighborhood request and returns an opaque,
  replay-verified local family receipt. Large exact
  sequence domains may declare one canonical `sequence_partition`; each result
  remains complete only for that part, preserves molecular realization ids, and
  does not claim whole-domain payload compatibility.
- `load_verified_local_neighborhood(result_path) -> LocalNeighborhoodDiscovery`
  loads only the active foldback or basal family result schema and repeats exact
  deterministic discovery replay.
- `discover_basal_sequence_space(source_path) -> BasalSequenceSpace`
  evaluates a finite canonical basal domain, admits complete source contexts,
  then projects exact local sequence sets. Different enzyme programs or source
  contexts do not multiply the local count. Other pairing permissions raise.
  Computational exhaustion cannot return complete authority. See the
  [basal sequence-space guide](../guides/basal-sequence-space.md).
- `load_verified_basal_sequence_space(result_path) -> BasalSequenceSpace`
  repeats complete deterministic discovery before exposing `json_bytes`,
  `result_id`, `candidate_count`, and `admitted_count`. Create-only
  `write(destination)` retains the portable result. Explicit
  `member_json(case_id=..., rank=..., program_index=...)` recovers a complete
  source and molecular realization supporting the selected local sequence.
- `discover_foldback_sequence_space(source_path) -> FoldbackSequenceSpace`
  exhausts a finite foldback domain into compact exact sequence sets, retaining
  each examined enzyme program and its support. Raw and admitted counts use
  distinct payload/geometry/strand/sequence configurations; enzyme aliases do
  not multiply them. Computational exhaustion raises without returning a
  complete receipt. See the [sequence-space guide](../guides/foldback-sequence-space.md).
- `load_verified_foldback_sequence_space(result_path) -> FoldbackSequenceSpace`
  repeats complete deterministic discovery and requires exact result equality.
  The receipt exposes `json_bytes`, `result_id`, `candidate_count`, and
  `admitted_count`. Its `write(destination)` publishes a create-only directory;
  `member_json(case_id=..., rank=..., program_index=..., completion_rank=0)`
  recovers one exact molecular realization through a selected supporting program.
  `rank` addresses the retained arm/cap word; `completion_rank` addresses its
  locally admitted source-tail alternatives. The member reports
  `source_completion_count`. These ranks are addresses, not biological scores;
  later material checks can distinguish two completions of the same retained word.
- `list_local_realizations(receipt, cohesive_end=None, max_retained_overhead_nt=None,
  max_noncanonical_pairs=None, sort_by=()) -> tuple[LocalRealizationChoice, ...]`
  lists recorded local witnesses with their compilable family identity, typed
  geometry, retained sequence, enzymes, pairing classes, and adapter completion
  requirement. Filters do not rerun the search. Sort keys are ascending
  `retained_overhead_nt`, `noncanonical_pairs`, or `enzyme_count`, applied in
  caller-specified priority with stable ties. Pairing and end filters require
  basal evidence. Rows are immutable inspection values, not verified receipts;
  compilation still checks the selected identity against its original receipt.
- `discover_local_neighborhoods(source_paths, destination, resume=False,
  max_new_requests=None, batch_size=8) -> LocalNeighborhoodBatch` executes an
  explicit ordered collection of independent local requests. It publishes
  bounded immutable batches and replays saved results before resuming. The
  receipt exposes `planned_requests`, `completed_requests`, `finished`, and
  lazy replay through `iter_results()`. Its `report_json()` serializes the full
  `hop/local-batch-report/v1` result bodies within the existing 64 MiB execution
  document ceiling, including the CLI newline. Exceeding that limit raises
  without changing the checkpoint; `iter_results()` still provides individual
  receipts with `report_json()` and `write()` for separate access.
  Execution completion does not imply
  exhaustive coverage or feasibility of any individual request. See
  [checkpointed discovery](../guides/checkpoint-local-queries.md)
  for limits, persistence, and recovery semantics.
- `discover_source_partition(source_path) -> SourcePartitionDiscovery`
  enumerates canonical nonempty subsets of provisioned strand-exposure
  nickases, applies every actionable site, derives all denatured fragments,
  applies the declared length selection, and accepts only exact required
  survivor spans. The opaque receipt exposes exact search accounting and
  deterministic JSON/CSV bytes.
- `load_verified_source_partition(result_path) -> SourcePartitionDiscovery`
  safely reopens canonical result JSON and repeats molecular, candidate-space,
  completion, and identity replay before returning the same opaque receipt.
- `discover_construction_source_partition(receipt, policy_path,
  materialized_realization_id=..., combination_ordinal=...) -> SourcePartitionDiscovery`
  requires exactly one of the two selection keywords. It searches removal
  programs for an accepted construction or an examined PCR-bearing combination,
  deriving the prepared source and required surviving strands from verified
  molecular inputs. An examined candidate need not have passed endpoint
  validation; its returned partition does not confer route acceptance. The policy supplies
  enzymes, a fragment-length rule, and search bounds, not molecular overrides.
  It does not modify the route or choose a partition. See
  [checking source removal](../guides/select-construction-junctions.md#check-removal-for-a-selected-source).
- `load_verified_construction_bundle(path) -> VerifiedConstructionBundle`
  checks portable bytes and semantically replays the embedded design, local
  authorities, complete result, and root manifest.
- `select_construction_realization(receipt, materialized_realization_id=...) -> ConstructionSelection`
  creates a stable non-authoritative reference to one accepted exact route.
- `load_construction_selection(path, receipt=...) -> ConstructionSelection`
  safely loads a selection and cross-checks its result and realization against
  the supplied verified receipt.
- `project_foldback_feasibility(receipt) -> ConstructionProjection`
- `project_basal_feasibility(receipt) -> ConstructionProjection`
- `project_basal_minimum_overhead_matrix(receipt) -> ConstructionProjection`
- `project_retained_overhead_frontier(receipt, family=...) -> ConstructionProjection`
- `project_source_partition_certificate(receipt, realization_id=...) -> ConstructionProjection`
- `project_construction_navigation(receipt) -> ConstructionProjection` projects
  the unchanged complete summary plus only the additive accepted-route facts:
  typed geometry, retained overhead, cleavage-program enzyme IDs, retained
  non-payload sequence, and endpoint topology. It supports browse, filter, and
  explicit-sort workflows using the summary's accounting relation.
- `project_complete_construction_summary(receipt) -> ConstructionProjection`
- `project_construction_trajectory(receipt, materialized_realization_id=...) -> ConstructionProjection`
- `project_hairpin_portrait(receipt, materialized_realization_id=...) -> ConstructionProjection`
  shows the recorded joined hairpin, its stem and extensions, loop, contacts,
  joins and terminal chemistry. Later release ends remain a separately named
  stage. `write(path)` exports `projection.json`, `projection.svg`, a result-bound
  `selection.json` and the selected trajectory/materials under `preparation/`.
  It supports one contiguous intramolecular stem and loop; unsupported topology
  raises explicitly.
- `compare_constructions(left, right, left_realization_id=..., right_realization_id=...) -> str`
  returns a read-only Markdown comparison of two accepted routes from verified
  compilation or bundle receipts. It compares recorded molecular properties,
  not request text, and preserves both search statuses and selected identities.
  Unknown or rejected selections raise; raw model objects are not accepted.
  The operation reads recorded routes without ranking, writing or searching. See
  [comparing completed choices](../guides/compile-construction.md#compare-completed-choices).

The source document cannot author design or result identities. Receipts expose
bundle, result, and design-bundle identity; endpoint and status; accepted,
examined, and nominal counts; and accepted materialized-realization identities
rather than internal result models. `ConstructionCompilation.write(path)`
atomically persists the portable authority. Both construction receipt types
expose `report_json()`, which serializes the admitted manifest, result, byte
digests, and scalar accounting in the existing `hop/construction-report/v1`
format without reading published files again. Projection packets provide
canonical JSON, tidy CSV when defined, and SVG bytes; writing a
packet is atomic and create-only. A trajectory always requires an explicit
accepted realization identity.
`ConstructionProjection.inspection_text` gives the selected route overview.
`ConstructionProjection.inspect_end(product_end, base_index=None)` returns a
focused text explanation for `"left"` or `"right"` on a released duplex. The
optional keyword-only index is zero-based in that end's own 5′→3′ word; invalid
types, out-of-range indexes, earlier endpoints and non-trajectory projections
raise `ValueError`. The text reads recorded material origins and release cuts;
it neither reconstructs a route nor changes projection bytes. Structured facts
remain in `json_bytes`; use the text for reading and JSON for structured access.
For a trajectory, `ConstructionProjection.write(path, selection_reason=None)`
also exports `report.md`, `oligos.csv`, and `oligos.fasta`. The CSV retains required
terminal chemistry; FASTA contains sequences only. The optional nonblank reason
is caller-authored report text, not a molecular fact or a ranking. Other
projection types reject a supplied selection reason. Canonical projection bytes
and identities are independent of this text.
`ConstructionCompilation.write(...)`, `ConstructionProjection.write(...)`,
`ConstructionSelection.write(...)`, and `SourcePartitionDiscovery.write(...)`
accept optional `protected_root=path` for the verified input bundle. On macOS
and Linux this checks bundle exclusion and binds all staging and publication to
an opened parent directory, so later ancestor redirects cannot redirect those
writes. Protected publication fails explicitly on other platforms. Construction
compilation, projection, route-selection, and derived-partition commands supply
their input bundle automatically. Nested construction bundles retain staged
semantic verification before publication; artifact files use owner-only access.
Commands retain the input directory's identity from verification through
publication. A root replaced during verification fails; a later rename does not
transfer protection to a replacement at the old pathname. Direct Python callers
that pass a path capture its identity when the writer begins.
To retain protection across an earlier Python verification step, capture
`construction.ProtectedRoot.capture(path)`, verify the input, call the token's
`require_unchanged()`, and pass that token as `protected_root`. The token is
ephemeral filesystem identity, not a portable scientific artifact.
`ConstructionSelection.write(path)` writes canonical JSON to exactly one new
`.json` file path. A selection never changes or narrows the complete
construction authority.

Source-partition nick functions distinguish a retained-fragment boundary from
excluded-fragment cleanup. Canonical enzyme
subset order is replay metadata, not rank. PCR handles are outside this local
search.

See the [construction guide](../guides/compile-construction.md), the
[source-partition guide](../guides/discover-source-partitions.md),
[construction-bundle layout](construction-bundle-layout.md), and
[construction projection contracts](view-contracts.md#complete-construction-projections).

## Substrate spaces and design sets

All operations and public contracts in this section use `hop_design.spaces`.

- `preview_space(spec) -> SubstrateSpacePreview` validates one segmented
  authored arm, derives its paired arm, computes exact cardinality, and returns
  `ready`, `blocked`, or `invalid` without enumerating or writing.
- `compile_space(spec, destination=...) -> VerifiedHairpinDesignSet` expands a
  ready space exhaustively, compiles unchanged member `HopBundle` authorities,
  verifies the complete collection, generates review projections, and commits
  one new destination atomically.
- `load_verified_design_set(path) -> VerifiedHairpinDesignSet` verifies the
  collection inventory and identity, replays canonical enumeration, and loads
  every unique member through the existing semantic bundle verifier.

The exact facade allowlist also exposes `SubstrateSpaceSpec`,
`SubstrateSpacePreview`, `HairpinDesignSet`, and
`VerifiedHairpinDesignSet`. These names are not package-root re-exports.
`context` is descriptive review metadata and is excluded from collection
identity. V1 compilation is exhaustive or blocked; it never returns a
truncated authoritative set.

See the [design-set layout](design-set-layout.md) and
[substrate-space guide](../guides/substrate-spaces.md).

## Compile and integrity

- `create_spec(sequence=..., design_id=...) -> HopSpec` expands the named,
  versioned generic default into explicit references.
- `load_spec(path) -> HopSpec | ResolvedHopSpec` safely loads strict JSON/YAML
  by exact schema ID under a byte limit and rejects symlinks.
- `check(spec) -> CheckReport` aggregates expected feasibility diagnostics and
  raises for corrupt configuration.
- `compile(spec)` compiles one explicit spec.
- `compile(sequence=..., design_id=...)` is the observationally equivalent
  convenience path.
- `Compilation.write(path)` verifies and atomically writes a new bundle path;
  it refuses to replace an existing path.
- `verify_bundle(path)` validates safe paths, complete inventory, digests, root
  identities, strict spec/plan/provenance schemas, cross-artifact references,
  plan-derived FASTA, absence of unmanifested files, and a complete deterministic
  replay of the spec into the stored plan, artifacts, and manifest.
- `load_verified_bundle(path) -> VerifiedHopBundle` returns the strict semantic
  contents only after the same verification and replay succeed.

Provide exactly one of `spec` or `sequence`. `design_id` is only valid with
`sequence`. Expected infeasibility raises `InfeasibleDesignError` at compile;
invalid call shapes raise `TypeError`; corrupt bundles raise
`BundleIntegrityError`.

A `ResolvedHopSpec` compiles supplied foldback and basal components through an
explicit design derivation. A release projection requires explicit terminal-nick
geometry. Construction programs and named methods record their respective
molecular-state histories.
An optional `PairedStemExtensionRequest` records variable non-payload paired
context between the basal junction and payload stem.

## Payload records and variants

- `collect_payloads(records, duplicate_policy=...) -> PayloadCollection`
  consumes any iterable and records explicit `fail`, `dedupe`, or `keep`
  behavior for duplicate sequences. Duplicate record IDs always fail.
- `load_fasta_payloads(path) -> tuple[PayloadRecord, ...]` and
  `load_csv_payloads(path, id_column=..., sequence_column=...)` create the same
  strict records as inline input under explicit byte, record, and total-nt
  limits.
- `expand_payload(record, max_variants=...) -> PayloadExpansionResult` computes
  exact cardinality before allocation and raises `VariantBudgetExceededError`
  instead of truncating.
- `plan_design_space(space) -> DesignSpacePlan` computes Cartesian cardinality
  before row allocation, then returns one checked `ResolvedHopSpec` per bounded
  payload/foldback/basal/release combination without rendering bundles. Its
  explicit duplicate-final-sequence policy is `FAIL` or `KEEP`; it never drops
  combinations silently.

## Physical mechanics

Component evaluation and released-state projection use the design-language
root. Every `search_*` operation and its request, limit, and result contracts
use `hop_design.discovery`.

- `evaluate_foldback(request) -> FoldbackEvaluation`
- `search_foldback_arms(request, limits=...) -> FoldbackSearchResult`
- `evaluate_basal_pairing(request, constraints=...) -> BasalEvaluation`
- `search_basal_candidates(request, limits=...) -> BasalCandidateSearchResult`
- `search_basal_processing_geometries(catalog=..., request=..., limits=...) -> BasalProcessingGeometrySearchResult`
- `search_basal_processing_routes(basal_candidates=..., processing_geometries=..., limits=...) -> BasalProcessingRouteSearchResult`
- `search_released_foldback_geometries(catalog=..., request=..., limits=...) -> ReleasedFoldbackGeometrySearchResult`
- `search_released_foldback_precursors(request, limits=...) -> ReleasedFoldbackPrecursorSearchResult`
- `search_hairpin_junction_routes(released_precursors=..., basal_routes=..., limits=...) -> HairpinJunctionRouteSearchResult`
- `evaluate_paired_stem_extension(request) -> PairedStemExtension`
- `project_released_strand_state(request) -> ReleaseProjectionResult`
- `classify_motif_presence(sequence=..., motif=...) -> MotifPresenceReport`
- `scan_nicking_agent(sequence, agent=...) -> tuple[ResolvedNickSite, ...]`
- `scan_release_agent(sequence, agent=...) -> tuple[ResolvedReleaseSite, ...]`
- `search_nicking_placements(catalog=..., target=..., limits=...) -> NickingPlacementSearchResult`
- `search_foldback_precursors(request, limits=...) -> FoldbackPrecursorSearchResult`

For input requirements, result meanings and failure semantics, follow the
reference that matches the question:

- [component evaluation](component-evaluation.md) for foldback, basal, paired
  stem, released-strand projection, and compiler integration;
- [processing discovery](processing-discovery.md) for nick placement, exact
  precursor sequence, basal candidates, and terminal processing routes;
- [released-foldback routes](released-foldback-routes.md) for joint geometry,
  exact selected precursors, and active/surviving-strand continuity; and
- [workflow views](view-contracts.md) for renderer-independent projections.

Every bounded search requires explicit node and hit limits. Its status,
canonical order, physical measurements, caller selection, and downstream use
remain distinct claims.

## Linear-source method

All operations and public contracts in this section use `hop_design.methods`.

- `list_method_capabilities() -> tuple[MethodCapability, ...]`
- `resolve_linear_source_hairpin_pcr_materials(spec) -> LinearSourceHairpinPcrMaterialsPlan`
- `compile_linear_source_multinick_hairpin_pcr(request) -> LinearSourceMultinickHairpinPcrResult`
- `compile_linear_source_method_bundle(request) -> MethodCompilation`
- `load_verified_method_bundle(path) -> VerifiedMethodBundle`
- `verify_method_bundle(path) -> MethodBundle`

The capability query reports every named `MethodKind` in deterministic order,
with implementation availability and the exactness accepted by that method's
input contract. `exact_only` means callers must supply exact sequences;
`not_defined` means the unavailable method has no public request schema. The
query does not select a method, construct a request, or resolve one.

The material input records six sequence materials and whether ligatable 5′
phosphates are supplied or produced by a kinase step. The resolver checks
terminal primer binding. The bounded method compiler then resolves every nick,
fragment, selected strand, pair, bond, PCR boundary, facing restriction
product, and exact cohesive end. Expected infeasibility returns a `MethodOutcome`; corrupt contracts
raise validation errors. See the
[linear-source material reference](linear-source-method-materials.md) and
[method boundary](../methods/destination-neutrality.md). A complete request can be
written as a replay-verified method bundle containing the plan, trajectory,
FASTA, GenBank, and hairpin-encoding projection. Infeasible resolution raises
`MethodResolutionError` only when the caller requests that complete artifact
boundary; the lower-level compiler continues to return its typed outcome.

## Views

All operations and public contracts in this section use `hop_design.views`.

- `build_foldback_view(evaluation) -> WorkflowView`
- `build_foldback_junction_view(evaluation) -> WorkflowView`
- `build_released_workflow_view(state, foldback) -> WorkflowView`
- `build_basal_pairing_view(evaluation) -> WorkflowView`
- `build_basal_view(evaluation, nicked_strand=...) -> WorkflowView`
- `build_basal_source_panel(receipt, realization_id=...) -> ViewPanel`
- `build_method_trajectory_view(plan) -> WorkflowView`
- `render_workflow_svg(view) -> bytes`

The renderer consumes the typed view and performs no molecular derivation.
The same `hop_design.views` surface provides
`build_hairpin_junction_route_view(...)` and
`build_released_foldback_precursor_view(...)`; they are not package-root
exports.

`build_basal_source_panel` takes a verified local-neighborhood receipt and an
explicit local realization ID. It shows the source duplex, payload span,
nickase recognition sites, and nick boundary. A source-encoded recognition site
for later release is labeled separately; endpoint-supplied sites are omitted.
The panel does not assert strand removal, adapter joining, or future cleavage.
Unknown selections, non-basal receipts, and corrupt receipts raise `ValueError`.

The returned `ViewPanel` supports client figure composition or JSON export;
it is not a complete `WorkflowView` for `render_workflow_svg`. Both strand
sequences and feature coordinates are 5′→3′. Display the bottom track in reverse;
recognition spans use the source-top coordinate reference.

Stable package-root types cover payloads, design specs, coordinates, junctions,
processing agents, design results, and operator-facing errors. Discovery,
method, molecular-state, and view contracts live only on their named sibling
facades; the root does not forward them.

## Scaffold families and explicit comparative sets

`prepare_construction_family(path) -> PreparedConstructionFamily` previews named
variations within a base product request without searching.
`execute_construction_family(path, *, continuation="sole-witness") -> ConstructionFamilyExecution`
requires the explicit continuation argument and preserves every member outcome.
`select_construction_set(path) -> ConstructionSet` verifies explicit complete
selections and exports individually supported preparations, typed comparisons
and chemically deduplicated oligos with all member/role uses. All three expose
`json_bytes`, `report_text`, and create-only `write(destination)`. Their packets
preserve the underlying molecular records.
See [compare scaffold families](../guides/compare-scaffold-families.md) for input
fields, bounds, conflict handling, selection and interpretation.

`project_construction_comparison(left, right, *, left_realization_id,
right_realization_id) -> ConstructionComparison` returns content-bound
`hop.construction-comparison/v2` JSON through `json_bytes`; `report_text` is the
same human comparison as `compare_constructions`. `write(path.json)` creates
one new projection. Regional contacts are aligned locally; sequence equality
and coordinate equality are separate properties. Routes outside the hairpin
portrait domain retain preparation facts and an explicit unavailable-region
reason. Comparisons retain the recorded routes without ranking them.


## Portable scaffold comparison report

Use `project_construction_family_report` in Python or
`hop-design construction report-family` to turn a saved family into one portable
PDF/SVG report and preparation index. Optional `selection`, `baseline` and explicit
member `edits` preserve user intent without automatic selection or relaxation.
See [the public walkthrough](../guides/compare-scaffold-families.md#open-one-portable-comparison)
and [the report contract](family-report.md) for inputs, verification, outputs and
scope.


`author_construction_family(path) -> PreparedConstructionFamily` compiles a
strict scaffold comparison brief and preserves a portable copy of its base.
`reconcile_construction_family(path, *, source_member, outcome_path, member=None,
revised_request=None, preferred_loop_nt=None) -> ReconciledConstructionFamily` admits an exact complete
continuation into a new capture. An edited alternative requires a new `member`
and explicit revised roster. Original requests/outcomes are retained under
`history/parent/`; comparison, set selection and retrieval use the normal APIs.
No search, policy relaxation or automatic set selection occurs.


`preferred_loop_nt`, when supplied, records a caller-declared preference and must
match the selected complete hairpin. It never selects a local witness. Family
and set controls support unchanged non-loop sequences, region-local contacts
and joins; source oligo and primer changes remain separately visible. The set
summary and family report distinguish required verification from observed
agreement and missing evidence.

`match_construction_family(path, *, reference_member, reference_choice,
max_continuations) -> MatchedConstructionFamily` admits a saved family, fixes
an explicit complete reference and continues a bounded number of recorded local
witness pairs. Inspect `json_bytes` or `report_text`, then call `write(new_path)`.
Complete alternatives carry exact selection/preparation paths; the caller selects
or reconciles them explicitly. See the
[matching contract](../architecture/decisions/0041-reference-bound-family-matching.md).


## Product-first scaffold options

`prepare_scaffold_discovery(path) -> PreparedScaffoldDiscovery` previews a strict
`hop.scaffold-discovery/v1` through `/v6` request. Versions 2–5 add terminal-form
translation, required-target scheduling, joint placements and molecular parameter
restrictions. Version 6 adds a finite roster of joint receiving-end requirements;
each tuple preserves words, polarity, orientation and placement together.
See the [schema contracts](schemas.md#product-driven-scaffold-discovery).
`discover_scaffolds(path) -> ScaffoldDiscovery`
evaluates its bounded preparation branches through the ordinary options
evaluator. Hard scaffold requirements remain enforced against achieved states.
`select_scaffold_options(path, *, members, baseline, shared_properties=(),
compared_properties=(), stage_controls=(), reuse_prior_materials=None) -> ConstructionSet`
binds a mapping of user names to
explicit visible options and retrieves ordinary portable preparations.
Stage controls are `ResolvedStageControl` values with explicit member names;
`PriorMaterialReuse` names a verified preparation and exact material roles.
Both types, and `SelectedPreparationReference`, are exported by
`hop_design.construction`.
See the [public example](../../examples/scaffold-discovery/README.md) and
[active delivery boundary](../dev/plans/product-first-discovery.md).

`explore_construction_options(path, *, max_continuations) -> ConstructionOptions`
returns complete options before local selection. The explicit integer budget is
1–64 examined pairs; failures consume it. `json_bytes`, `report_text` and
`write(new_path)` expose the bounded inventory and molecular report.

`find_construction_option_sets(path, comparison) -> ConstructionOptionSets`
replays a saved options packet and groups its achieved molecules by declared
shared controls. Missing members are missing from this pool, not proven globally
impossible. Multiple shared backgrounds and preparations remain distinct choices.

`select_construction_options(path, *, option_labels, baseline,
shared_properties=(), compared_properties=(), comparison=None) -> ConstructionSet`
resolves explicit packet labels into exact preparations. Supply either a reusable
comparison request file or shared/compared property tuples. Comparison intent
requires exactly one selected option per requested member. Baseline remains
explicit. The ordinary returned set supports portable re-admission through its
`set.json`; no manual local or realization identifiers are required.

See [explore scaffolds](../guides/explore-scaffolds.md) and
[the ownership decision](../architecture/decisions/0042-complete-scaffold-options.md).

## Interface surveys

The `hop_design.construction` facade exposes these file-oriented operations:

- `evaluate_interface_survey(request_path, index_path, *, max_evaluations,
  local_nodes, local_realizations, release_site_pairs, navigation_nodes=256,
  navigation_frontier=4096, resume=False,
  max_checkpoint_bytes=1073741824) -> dict` advances an incremental batch.
  The request's `source_context_objective` selects exhaustive context words or
  one complete handle per paired-scaffold group. `enumeration_scope` preserves
  that distinction in progress and queries. The frontier bound limits pending
  completion work; reaching it leaves the target unresolved. See the
  [survey guide](interface-survey-search.md#complete-handles-without-enumerating-every-interchangeable-word).
- `inspect_interface_survey(request_path, index_path, *, offset=0, limit=100)
  -> dict` returns integrity-checked paginated evaluations and indexed coverage.
- `query_interface_survey(request_path, index_path, query=None) -> dict` filters
  compact complete-path coordinates while retaining declared values and context.
  The optional query is a mapping or path to `hop.interface-survey-query/v1`.
- `load_interface_survey_choices(request_path, index_path) -> InterfaceSurveyChoices`
  admits a consistent immutable snapshot for repeated `pool.query(query=None)`
  calls. Mapping queries do not reopen the checkpoint. Reload explicitly to see
  newly resumed evaluations. Every result includes its `snapshot_digest` and
  predicate `query_digest`. `pool.select(target=..., step=...,
  materialized_realization_id=..., query=None)` returns a query-bound selection
  mapping; `pool.sample(seed=..., query=None)` chooses among matching distinct
  complete preparations without new evaluation or relaxed requirements.
- `inspect_interface_survey_atlas(request_path, index_path, *, selection, reference_selection=None) -> InterfaceSurveyAtlas` replays one selected
  witness and projects every recorded state, material input and parameter location.
  An optional reference is independently admitted and replayed; both selection
  receipts, exact molecular/material differences and correspondence limits remain
  in the packet. It does not change target retrieval or search coverage.
  The packet exposes `json_bytes`, `svg_bytes`, on-demand `pdf_bytes`, and create-only
  `write(destination, *, print_pages=True)`. Print exports use the same stage-paginated
  drawing and physical-size contract as `ScaffoldAtlas`; browser previews omit them.
- `verify_interface_survey(request_path, index_path) -> dict` recomputes all
  recorded evaluations and returns replay-derived coverage.
- `upgrade_interface_survey(request_path, index_path, *, source_producer,
  destination, max_checkpoint_bytes=1073741824, on_replayed=None) -> dict` replays
  a stopped checkpoint into a new directory under the current producer.
  `source_producer` is the exact original producer mapping or its JSON/YAML path, not a compatibility
  override. Every saved result and continuation must match. Only freshly
  regenerated exclusion certificates may change producer identity. The original
  is preserved; the new directory contains `request.json`, `survey.sqlite`, and
  `transition.json`. The optional callback receives the completed replay count.
  A failed or interrupted replay publishes no destination. Keep the old runtime
  and checkpoint until the new checkpoint has been qualified for continuation.
- `retrieve_interface_survey_witness(request_path, index_path, *, selection,
  destination) -> VerifiedConstructionBundle` replays one exact witness and
  writes its portable construction, request and preparation into a new directory.

Selection accepts a mapping or path to `hop.interface-survey-selection/v1`.
The atlas and handoff both retain this exact document. Its snapshot describes the
pool when selected; appending evaluations does not invalidate an unchanged exact
record, request or predicates. The selection is a reference, not a replay certificate.

Input paths accept `str` or `Path`. Molecular permissions live in the request;
execution budgets do not remove targets. Inspection is not aggregate molecular
replay. See [the survey guide](../guides/survey-interfaces.md).

## Required molecular comparison operations

`prepare_scaffold_comparison(path) -> PreparedScaffoldComparison` previews a
strict `hop.comparison-brief/v1`, grouped `/v2`, or stage-controlled `/v3`.
Version 3 compiles member selectors into bounded required-first discovery and can
bind materials from a verified prior preparation. `execute_scaffold_comparison(path) ->
ScaffoldComparison` discovers complete options and assesses named obligations.
`assess_scaffold_comparison(brief_path, discovery_path) -> ScaffoldComparison`
reuses a replay-verified discovery with the same molecular request and bounds.

`select_scaffold_comparison(path, *, set_label, baseline) -> ConstructionSet`
replays a saved comparison, then retrieves an explicitly named compatible set.
All four operations return create-only portable packets. See the
[comparison workflow](../guides/specify-a-comparison.md) for stage, material,
coverage and rendering semantics.

## Required stem families through design intent

`resolve_design_request` accepts `hop.construction-family-intent/v1` and previews
bounded exact membership without searching. `discover_designs` returns the same
lifecycle with a required-member roster. Call `choices.member(name)` for the
ordinary query, select, figure, atlas and retrieval operations of one stem.
`choices.select_members({name: selection, ...}, baseline=name)` checks every
required stem and the declared shared flank/material controls. Pass its saved
selection to `choices.retrieve` for the consolidated portable set.

Family expansion and construction-set checks reuse the sequence-family owners.
Execution delegates to each endpoint's existing discovery backend. The original
`prepare_sequence_family`, `execute_sequence_family` and `select_sequence_family`
contracts remain available for native scaffold-discovery requests.

## Frozen atlas editions and guided exploration

`combine_design_discoveries(request, directories, destination) -> AtlasEdition`
captures one compact edition from 2–256 disjoint, stopped released-insert
discoveries. The explicit parent intent binds the unchanged stem and all molecular
permissions. The input target grids must cover its Cartesian end-pair grid exactly
once, with identical effort policies and current producer admission. Empty jobs
retain their coverage. The result is read-only; each original checkpoint remains
the continuation authority. See [independent jobs](../guides/share-atlas-edition.md#combine-independent-discovery-jobs).

`load_atlas_edition(directory) -> AtlasEdition` verifies an immutable inventory
of captured molecular packets, choices and material handoffs. It never loads a
live discovery or runs its producer. Create one with
`choices.freeze(destination, query=None, identities=None)` using the environment
that admits the live choices. Destinations are create-only.

`freeze_design_choices(directory, destination, *, query=None, identities=None,
include_landscape=False, compact=False, distance_policy=None,
comparison_weights=None, source_contract=None) -> AtlasEdition` is the
file-oriented equivalent used by `design freeze`. An explicit
`hop.recorded-design-source/v1` contract permits read-only compact capture of
an exact-stem released-insert discovery from its recorded producer. The contract
binds its full producer identity, snapshot and complete input bytes. The exporter
verifies existing molecular records without starting search, preserves the
original producer, and records its own identity separately. Ordinary loading,
continuation and replay retain exact producer admission. See
[recorded capture](../guides/share-atlas-edition.md#capture-a-recorded-discovery-with-an-updated-exporter).

Both objects expose `parameters(query=None)`, `families(query=None, stage="endpoint")`,
`sample(seed=..., strategy="families", stage="endpoint", history=())` and
`figure(selection=..., view="families", stage="endpoint", layout="auto")`.
Use `stage="hairpin"` to group the folded intermediate. Exact product identities
remain separate from structural families and preparation identities. A guided
sample receipt is accepted wherever an ordinary exact selection is accepted;
its inputs are replayed first. Default `sample(seed=...)` behavior is unchanged.

`parameters(query=None)` returns the same stage-qualified definitions and operation
guidance used by the browser and `design parameters`. Each definition includes
its canonical key, linked measurements, active `constraints` and `operations`
for `inspect`, `filter`, `revise`, `prefer`, `preserve` and `diversify`. Each operation
reports `available` and `reason`; applicable operations also identify the existing
revision field, search parameter or preservation arguments. Availability describes
the supported operation, not the existence of a matching preparation.
Per-feature ranking is currently unavailable. Frozen editions cannot change
permissions or initiate discovery. A reference-bound query is validated here
without scanning routes to verify preserved surroundings; that verification occurs
when the query is evaluated. For stem families, call `member(name).parameters()`
or pass `design parameters --member NAME`.

`view(selection, stage="all", reference_identity=None, camera=None)` records an
inspection. `restore_view(receipt)` validates snapshot, membership and stage before
returning the normalized receipt. It does not change the query or start search.
`presentation={"landscape": "similarity", "color": {"key": "left_gap"}}`
records an edition-wide numeric color view. Exact sequence highlighting uses,
for example, `{"key": "loop_word", "word": "AACA"}` for a recorded word.
These v5 receipts restore the browser lens and reproduce map colors through
`figure(selection=receipt)`. Color does not change eligibility or molecular identity.
An edition retains captured drawings and materials; comparison redrawing requires
a supported complete-route schema. Producer and current renderer identities stay
separate. See [the edition guide](../guides/share-atlas-edition.md).
