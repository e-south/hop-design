# Explore variants and compare preparations

Inspect alternatives within a recorded discovery or edit result's permissions.
Queries filter recorded choices. Evaluation explicitly adds bounded results.
A comparison declares required members and shared controls before selection.

See the [conditional-variant walkthrough](../../guides/explore-conditional-variants.md)
for the sequence of calls, or return to the [Python API task index](../python-api.md).

## Conditional variant exploration

### Evaluate parameters and revise the envelope

`load_scaffold_exploration(result_directory)` verifies and loads a saved discovery
or edit result once and returns an immutable `ScaffoldExploration` receipt.
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

### Query the recorded variants

The returned `choice_space.axes` supplies the shared parameter definitions. Query v2
accepts `parameters=[{"key": "self_paired_arm_bp", "minimum": 7, "maximum": 8}]`
in addition to the v1 fields below. Integers use inclusive ranges; categorical
`values` use OR, with AND across keys. Selection and further evaluation remain
separate operations. See the [construction-envelope walkthrough](../../guides/explore-conditional-variants/construction-envelope.md#explore-the-construction-envelope).

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

### Teaching and overview drawings

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

### Pins, controls and exact selection

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
See the [walkthrough](../../guides/explore-conditional-variants.md).

`load_scaffold_variant_choices(pool, directory)` re-derives a saved choice packet
against the admitted pool. Export retains protection of both source and choices.

### Inspect one recorded molecular state

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

### Preview a variant without selecting it

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

### Inspect the complete preparation atlas

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

### Assess conditional comparison sets

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
[runnable example](../../../examples/molecular-editing/run.py) and
[molecular edit guide](../../guides/edit-folded-sequences.md). The local editor is a
thin CLI-owned transport over these same public operations.

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
See [compare scaffold families](../../guides/compare-scaffold-families.md) for input
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
See [the public walkthrough](../../guides/compare-scaffold-families.md#open-one-portable-comparison)
and [the report contract](../family-report.md) for inputs, verification, outputs and
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
[matching contract](../../architecture/decisions/0041-reference-bound-family-matching.md).

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
[comparison workflow](../../guides/specify-a-comparison.md) for stage, material,
coverage and rendering semantics.
