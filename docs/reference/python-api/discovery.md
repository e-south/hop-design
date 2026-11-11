# Discover complete preparations

Start with an exact stem and an intended product. Discovery returns complete
preparations: exact molecules, materials and processing steps. Use the returned
choices to inspect the recorded pool, select a preparation, and retrieve its
materials. The native scaffold and interface-survey APIs below expose their
own request and checkpoint contracts.

Follow the [worked tutorial](../../guides/discover-designs.md) for a complete example,
or return to the [Python API task index](../python-api.md).

## Discover complete designs

Use `hop_design.construction.discover_designs(intent, destination,
max_evaluations=64)` to find complete preparations around an exact stem. The
intended product is required; end words are optional. A named or supplied context
declares geometry, methods and materials. `resolve_design_request(intent)` returns
the authored intention and the permissions obtained after resolving its context,
without searching.

The returned `DesignChoices` lets you filter recorded preparations with `query`,
read their meaning and coverage with `explain`, choose one with `select` or
`sample`, and export it with `figure`, `atlas` and `retrieve`.
Pass one selection to both figures and retrieval.
`select` accepts a returned path or exact preparation identity. Filtering a
retained pool performs no search. `load_design_choices(directory)` reopens the
whole discovery directory and validates its request and producer bindings. Keep
the original HOP/Python producer environment for live results. For inspection
independent of that producer, [save a fixed preparation collection](../../guides/share-atlas-edition.md)
before changing environments. `find_more` or
`continue_design_discovery` explicitly resumes discovery under the same permissions.

### Try a known preparation first

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

### Progress and cancellation

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

### Search objectives and permission revisions

An optional `objective={"kind": "diversity", "parameters": ["loop_nt"]}` prioritizes
contrasts within those permissions. The same contract supports insert, direct
hairpin and adapter-ligated hairpin discovery. `query()["search_objective"]` reports
the stage-specific dimensions and observed classes; continuation retains the
objective. See [scaffold alternatives](../../guides/explore-scaffold-alternatives.md)
for supported dimensions and how search limits differ from molecular permissions.

`preview_design_revision(intent, changes)` and `choices.revise(changes)` return a
`DesignRevisionPreview` with explicit before/after declarations and conflicts.
Arm ranges, characterized methods, joint end placements and retained-length limits
can be revised without replacing the authored stem or hard requirements.
`load_design_revision(directory)` verifies and replays a saved preview. Calling
`preview.execute(new_directory, ...)` explicitly discovers under the captured
revision, keeping the original result untouched. `preview.write(directory)` only
saves the preview; it performs no search.

### Explain recorded choices

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

### Endpoint-specific continuation

Products are `released_insert`, `hairpin` (direct ssDNA hairpin), and
`adapter_ligated_hairpin`. Hairpin discovery delegates to the scaffold backend;
it resumes a verified prefix of up to 64 continuations. For these two endpoints,
`first_choices=N` on `discover_designs`, `continue_design_discovery` or `find_more`
returns after N new complete choices or the evaluation limit. `query()["execution"]`
records the requested effort, stopping policy and examined prefix. Failed attempts
remain in coverage. Each continuation writes an immutable snapshot; retrieval and
atlas export resolve earlier explicit selections against their original snapshot.
The insert backend retains its existing resumable evaluation batches and does not
accept `first_choices`. See the [introductory workflow](../../guides/discover-designs.md).

### Preserve molecular neighborhoods

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

### Compare and retrieve required sets

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
[loop comparison example](../../guides/discover-designs/require-comparative-preparations.md#compare-loops-while-holding-the-scaffold)
shows the complete public lifecycle.

## Product-first scaffold options

`prepare_scaffold_discovery(path) -> PreparedScaffoldDiscovery` previews a strict
`hop.scaffold-discovery/v1` through `/v6` request. Versions 2–5 add terminal-form
translation, required-target scheduling, joint placements and molecular parameter
restrictions. Version 6 adds a finite roster of joint receiving-end requirements;
each tuple preserves words, polarity, orientation and placement together.
See the [schema contracts](../schemas/discovery-and-selection-packets.md#product-driven-scaffold-discovery).
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
See the [public example](../../../examples/scaffold-discovery/README.md) and
[active delivery boundary](../../dev/plans/product-first-discovery.md).

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

See [explore scaffolds](../../guides/explore-scaffolds.md) and
[the ownership decision](../../architecture/decisions/0042-complete-scaffold-options.md).

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
  [survey guide](../interface-survey-search/molecular-domain-and-completion.md#complete-handles-without-enumerating-every-interchangeable-word).
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
- `migrate_interface_survey(request_path, index_path, *, destination,
  max_checkpoint_bytes=1073741824, minimum_free_bytes=0, should_stop=None,
  on_converted=None) -> dict` converts a stopped checkpoint into compact storage
  without repeating historical discovery. It preserves the source, identities,
  selections and original creators. The callback receives converted object count
  and decoded bytes; a true stop request cancels publication. Cross-producer
  conversion requires a shipped compatibility declaration. See
  [storage and recovery](../interface-survey-search/checkpoint-storage.md).
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
replay. See [the survey guide](../../guides/survey-interfaces.md).

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
