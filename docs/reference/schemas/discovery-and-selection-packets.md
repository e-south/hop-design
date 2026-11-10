# Discovery and selection packet contracts

Read the versioned input, result and projection contracts for discovery, conditional
inspection, explicit edits and selected comparisons.

Return to the [schemas reference](../schemas.md).

## Molecular comparisons

`hop.molecular-distance/v1` optionally declares regional edit treatment, end-word
comparison, numeric scales, constant-coordinate handling and nominal contact
semantics inside a molecular comparison basis. Omission preserves legacy
arithmetic and serialization. Basis versions v1/v2 distinguish complete-tail and
retained-tail descriptor scope independently of this distance policy. See the
[molecular comparison reference](../molecular-comparison.md) for formulas and limits.

## Resumable interface surveys

`hop.interface-survey/v2` separates a four-base target domain and molecular
permissions from execution limits. Empty `targets` means all 256 left and right
words, or 65,536 ordered pairs. Optional exact word subsets are canonicalized and
crossed; placements remain explicitly paired. Geometry, methods, materials and
constraints use existing molecular models. The endpoint is a released duplex
insert. See the [authoring guide](../../guides/survey-interfaces.md).

`hop.interface-survey-index/v1` is the metadata schema of a transactional SQLite
checkpoint with compressed content-addressed authorities. It binds the request,
producer and local/release evaluation limits. `hop.interface-survey-evaluation/v1`
records each continuation and next address. Derived operation outputs are
`hop.interface-survey-progress/v1`, `hop.interface-survey-inspection/v1`, and
`hop.interface-survey-verification/v1`. Only the verification operation replays
every saved evaluation; index inspection checks saved records without repeating
their molecular calculations.

`hop.interface-survey-query/v1` accepts up to 128 distinct registered parameter
predicates, using the same value/range validation as conditional exploration.
`hop.interface-survey-choices/v1` exposes declared domains, recorded complete paths,
conditional counts and exact target/step/realization addresses. Filtering does not
change permissions or evaluate new candidates. Missing witnesses remain unresolved
unless the declared search is proven exhausted; supported values outside the
current filter remain distinct. Preparation counts deduplicate exact identities;
separate record counts preserve repeated evaluations. Indexed plotting facts require aggregate replay
before using their coverage as evidence.

`snapshot_digest` identifies the admitted coordinate snapshot, including its
request, producer and evaluation history. All predicates over that snapshot keep
the same digest. Reloading after a committed evaluation creates a different
snapshot; filtering alone does not.

`hop.interface-survey-selection/v1` references the request digest, selection-time
snapshot digest, typed query and its digest, exact evaluation digest, target/step
address and materialized preparation identity. Both atlas and retrieval validate
the request, evaluation, identity and query before replaying the molecular authority.
The snapshot identifies selection context; it does not certify current coverage.
An unchanged selected record remains usable after appending evaluations. Seeded
sampling selects matching distinct preparation identities; it does not sample
unexamined possibilities or silently relax a predicate.

`hop.interface-survey-atlas/v1` binds one exact witness to its replayed molecular
atlas, parameter locations and teaching projection. Its create-only export uses
`hop.interface-survey-atlas-packet/v1`. Replay verifies the selected construction;
aggregate coverage requires whole-survey verification.

## Conditional exploration of complete results

`hop.scaffold-variant-query/v1` binds `result_digest`, `stage`, `focus`, an optional
fixed `reference`, neighborhood `pins` and stage-qualified `controls`. At most five
distinct neighborhoods can be pinned, each to 1–64 distinct observed variant IDs;
at most eight distinct stage/property controls are allowed. Controls require an
explicit reference. Unknown or wrong-stage variants are rejected.

`hop.scaffold-variant-query/v2` additionally accepts up to 128 distinct `parameters`.
Each selection has a canonical `key` and either distinct integer/string `values`
or inclusive integer `minimum`/`maximum` bounds. Booleans, floats, mixed value
types, duplicate keys and categorical ranges are rejected. Derived R constrains
A/D combinations. Positional keys follow `basal_source_base_N`,
`basal_adapter_base_N` or `basal_pair_class_N`, counting from ligation at N=0.
Parameters require v2 explicitly; v1 retains its original meaning.

`hop.scaffold-discovery/v5` adds the same parameter selections to the inherited
request. Local restriction compilation is bounded at 256 branches and 100,000
geometry visits; unsupported achieved-property restrictions remain explicit
post-construction checks. `hop.scaffold-parameter-evaluation-packet/v1` captures
an unchanged `previous/` pool, `additional/` discovery and the intersected request.
Admission replays both authorities and derivation. At most eight nested extensions
are admitted; coverage counts evaluation records rather than unique search-space
coverage. Parameter evaluation never relaxes the inherited constraints. Explicit envelope
revisions use a separate contract below.

`hop.scaffold-envelope-revision/v1` contains 1–64 distinct `changes`, each with a
whitelisted `path` and validated `value`. Unknown paths, locked product fields,
invalid domain values and duplicate edits fail. Preview exports use
`hop.scaffold-envelope-preview-packet/v1`; evaluation exports use
`hop.scaffold-envelope-evaluation-packet/v1`. Preview/evaluation summaries are
`hop.scaffold-envelope-preview/v1` and `hop.scaffold-envelope-evaluation/v1`.
The latter captures parent, explicit preview, targeted request and new discovery;
admission replays them before merging. The same eight-extension bound applies.

`hop.scaffold-parameter-domain/v1` projects a requested domain page;
`hop.scaffold-parameter-domain-packet/v1` captures query and page request.
Inputs name a registered `key`, offset ≥ 0 and limit 1–64. Only `loop_word` accepts
length (1–1024) and an uppercase A/C/G/T prefix; length must be permitted and at
least the prefix length. The projection's exact `total` is a decimal string.

`hop.scaffold-exploration/v1` describes an admitted immutable pool.
`hop.scaffold-variant-choices/v1` returns compatible complete products, preparation
labels, replacement variants, changes, exclusions and original coverage. Export
uses `hop.scaffold-variant-choices-packet/v1`. A
`hop.scaffold-variant-view/v1` projection and
`hop.scaffold-variant-view-packet/v1` export depict one explicit preview without
selecting it. These records derive from the admitted pool.
See [conditional exploration](../../guides/explore-conditional-variants.md).

`hop.scaffold-atlas-request/v1` binds result/query digests, a compatible complete
option and optional state-qualified molecular address. The `hop.scaffold-atlas/v1`
projection composes recorded inspections, transitions and exact material uses.
It separates displayed occurrence, material ancestry and comparison correspondence.
The create-only `hop.scaffold-atlas-packet/v1` contains the vector scene and captured
generating request. Its molecular facts derive from the recorded preparation.

Its preparation-bound `hop.parameter-teaching/v1` projection covers source/
association, folded-hairpin and released-insert frames. Each parameter has an exact
location reference or explicit contextual/applicability status. The companion
`teaching.svg` shares these meanings with one-state inspection and the browser.
Required thresholds, achieved spans and zero-boundary anchors remain distinct;
see the [parameter coverage contract](../molecular-parameters.md).

`hop.scaffold-variant-preview-request/v1` binds result/query digests, one observed
variant ID, a phase/role/state selector, optional explicit preparation, and optional
focus with its originating preparation. `hop.scaffold-variant-preview/v1` reports
compatible candidates and a separate inspection only after ambiguity is resolved;
`hop.scaffold-variant-preview-packet/v1` exports it create-only. Choice summaries
add per-neighborhood `variable`, `fixed` or `unavailable` status under the complete
query. These additive derived fields do not change the v1 query language. Saved
summaries are always re-derived and compared exactly; stale packets are rejected.

## Molecular edits and bounded exact families

`hop.molecular-edit/v1` contains an original scaffold request, its canonical
validated-model SHA-256 digest, and one or two distinct stage/region edits.
`loop` at `hairpin` accepts exact distinct `sequences`; `released_ends` at
`released_insert` accepts finite `placements` (`left_bp`, `right_bp`), optional
oriented `ends`, and explicit `basal_nick_enzyme_ids`/`release_enzyme_ids`.
Neither edit changes unmentioned hard constraints or work quotas.

`hop.scaffold-discovery/v4` adds `end_placements` and
`preparation_changes.basal_nick_enzyme_ids`. Required targets can additionally
select `end_placement` or `basal_nick_enzyme_id`. Finite cross-products reuse the
required-first scheduler; each strict branch retains ordinary molecular admission.
Existing v1–v3 meanings are unchanged.

`hop.folded-sequence-view/v1` contains a verified hairpin portrait, region-local
sequence correspondence, separate pairing-relationship agreement, changed material
roles, the exact endpoint product and strand-wise endpoint sequence differences.
Position correspondence can be ambiguous; equality of dimensions is not sequence
equality. Views are projections, reconstructed from authorities at retrieval.

`hop.sequence-family/v1` contains `base_request`, same-length IUPAC `stem_domain`,
`max_members` (1–64), `max_total_branches` (1–1024), `shared_properties` and
`shared_material_roles`. Cardinality is checked before enumeration. Every exact
expansion is required. `non_stem_sequences` is a construction-set shared property
over the hairpin loop and both flanks; paired stem arms remain derived. Shared
material roles use the ordinary exact material-reuse contract. Missing members
cannot be silently omitted during family selection.

See [the edit workflow](../../guides/edit-folded-sequences.md) for packets, stage
boundaries and runnable examples.
## Complete scaffold option packets

`hop.construction-options/v1` indexes the original product request, producer,
local coverage, examined outcomes and complete option identities. Its
`hop.construction-options-packet/v1` inventory contains ordinary local and
complete authorities, generated molecular projections and a PDF report.

`hop.scaffold-comparison/v1` declares 2–64 named members with distinct dimension
combinations and explicit shared properties. Allowed dimensions are `loop_nt`,
`loop_side_paired_bp` and achieved `open_side_paired_positions`. Members must use
the same dimension keys; varying a property that is also required shared is an
error. This contract queries achieved products and introduces no new local
molecular degree of freedom.

`hop.construction-option-sets/v1` records complete/incomplete groups over an
admitted evaluated pool, per-member option labels, shared values and retained
coverage. `hop.construction-option-sets-packet/v1` inventories that comparison
request and report. It is not a molecular authority or automatic selection.
Explicit retrieval returns the existing construction-set packet, with optional
`selected-intent.json` recording requested names and chosen labels.

## Product-driven scaffold discovery

`hop.scaffold-discovery/v1` embeds one product request, optional desired scaffold
ranges, explicit preparation-change permissions, a comparison stage and bounded
branch/continuation evaluation. The [request contract and workflow](../../guides/discover-product-scaffolds.md)
define each field and conflict rule.

`hop.scaffold-discovery/v2` adds permission-aware translation of terminal
unpaired-length requirements for adapter-ligated hairpins. Desired lengths are
inclusive ranges; achieved counts derive from the verified pairing boundaries.
Chemistry remains separate. Explicit tail sequences are optional; length alone
does not authorize invented bases. Version 1 retains its original meaning.

`hop.scaffold-discovery/v3` adds name-independent required selectors and a
deterministic required-first schedule under the shared branch budget. The saved
request retains its permitted domain. Evaluated, reused and unexamined tasks,
local search and continuation coverage remain separate records.

`hop.scaffold-discovery/v6` adds optional `receiving_end_pairs`: 1–64 distinct
`ProductEnds` tuples, each containing both end words, polarities, site orientations
and paired end-to-stem placements. It requires a released-insert request and cannot
coexist with `end_placements`; placements belong inside each tuple. The existing
branch/continuation budgets still apply. Marginal axis values do not authorize
undeclared crossed pairs, and exhausted local outcomes do not establish global
impossibility. See the [bounded receiving-end example](../../guides/discover-product-scaffolds.md).

`hop.scaffold-discovery-preview-packet/v1` preserves the authored request and
`hop.scaffold-discovery-preview/v1` effective requirements and unevaluated branches.
`hop.scaffold-discovery-packet/v1` adds complete inner options, failures and the
`hop.scaffold-discovery-result/v1` summary. Admission rederives the preview and
replays each inner authority before named selection. Product-stage hashes are
comparison keys, not replacements for construction identities. The selected
ordinary set may also contain `hop.selected-scaffold-stages/v1` as a projection
of its verified molecules and explicitly named membership. See
[ADR 0043](../../architecture/decisions/0043-product-driven-scaffold-discovery.md).

## Comparison briefs and independent hairpin endpoints

`hop.comparison-brief/v1` embeds a strict scaffold discovery and declares purpose,
required membership, shared hairpin properties, preserved material roles and
bounded assignment evaluation. `hop.comparison-preview/v1` and
`hop.comparison-preview-packet/v1` preserve its effective domains and conflicts.
`hop.scaffold-comparison-result/v1` records verified option groups, missing
members, failures and coverage; `hop.scaffold-comparison-packet/v1` inventories
the embedded discovery and reports. `hop.comparison-selection/v1` records the
explicit chosen set alongside ordinary portable construction-set membership.
These are derived views. See [ADR 0044](../../architecture/decisions/0044-molecular-comparison-briefs.md).

The endpoint vocabulary includes `adapter_ligated_hairpin`, which requires
`materialization.adapter_ligation` and excludes endpoint PCR auxiliaries and
release. The optional field is absent from serialized requests when unused.
See [ADR 0045](../../architecture/decisions/0045-adapter-ligated-hairpin-endpoint.md).

`hop.comparison-brief/v2` adds explicit groups with identical stage products within
groups and distinct products between groups. It accepts verified per-group
product references and exact-loop member selectors. The v1 purposes retain their
meaning. Optional finite `loop_sequences` in foldback geometry generate exact
`loop_sequence` targets; omitted fields retain previous serialization. See
[ADR 0046](../../architecture/decisions/0046-grouped-scaffold-comparisons.md).

`hop.comparison-brief/v3` adds stage-qualified regional controls over the whole
set or a named group, required-first discovery and verified prior-material reuse.
Regional sequence and pairing controls use recorded nucleotide ancestry at the
requested stage; missing or ambiguous correspondence remains unassessed.
Terminal chemistry is assessed separately. Prior-material bindings compile to
existing fixed policies without overriding inherited requirements. See
[ADR 0048](../../architecture/decisions/0048-stage-controlled-required-panels.md).

`hop.construction-set/v2` preserves resolved control membership and optional
embedded prior-material references for replay after relocation. Earlier set and
comparison versions retain their existing meanings; `shared_properties` continues
to refer to hairpin architecture.

## Optional-intent stem families

`hop.construction-family-intent/v1` uses the same product, context, optional ends,
scaffold and method fields as `hop.construction-intent/v1`. Its `stem_arm` permits
IUPAC symbols; `max_members` (1–64) and `max_total_evaluations` (1–1024) are required.
Optional `shared_properties` and `shared_material_roles` constrain explicit set
selection. Expansion cardinality is checked before creating search output.

`hop.design-family-preview/v1` records every required exact stem and its resolved
request. `hop.design-family-choices/v1` retains per-member results and missing
members. `hop.design-family-selection/v1` binds the request digest, baseline and
exact selection of every required member. Its digest detects edited membership;
retrieval still verifies each native preparation and all shared requirements.
