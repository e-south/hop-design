---
doc_id: hop-schema-reference
title: Current schema identifiers
intent: Identify supported source-checkout document types, their purpose, and their input limits.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-10-09
doc_type: reference
journey:
  - compile
  - discover
  - method
  - verify
---

# Current schema identifiers

## Molecular comparisons

`hop.molecular-distance/v1` optionally declares regional edit treatment, end-word
comparison, numeric scales, constant-coordinate handling and nominal contact
semantics inside a molecular comparison basis. Omission preserves legacy
arithmetic and serialization. Basis versions v1/v2 distinguish complete-tail and
retained-tail descriptor scope independently of this distance policy. See the
[molecular comparison reference](molecular-comparison.md) for formulas and limits.

## Resumable interface surveys

`hop.interface-survey/v2` separates a four-base target domain and molecular
permissions from execution limits. Empty `targets` means all 256 left and right
words, or 65,536 ordered pairs. Optional exact word subsets are canonicalized and
crossed; placements remain explicitly paired. Geometry, methods, materials and
constraints use existing molecular models. The endpoint is a released duplex
insert. See the [authoring guide](../guides/survey-interfaces.md).

`hop.interface-survey-index/v1` is the metadata schema of a transactional SQLite
checkpoint with compressed content-addressed authorities. It binds the request,
producer and local/release evaluation limits. `hop.interface-survey-evaluation/v1`
records each continuation and next address. Derived operation outputs are
`hop.interface-survey-progress/v1`, `hop.interface-survey-inspection/v1`, and
`hop.interface-survey-verification/v1`. Only the verification operation replays
the whole recorded corpus; index inspection is not molecular evidence admission.

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
`hop.interface-survey-atlas-packet/v1`. Selected-witness replay establishes that
construction, not aggregate coverage or experimental performance.

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
selecting it. These are derived exploration records, not new molecular authorities.
See [conditional exploration](../guides/explore-conditional-variants.md).

`hop.scaffold-atlas-request/v1` binds result/query digests, a compatible complete
option and optional state-qualified molecular address. The `hop.scaffold-atlas/v1`
projection composes recorded inspections, transitions and exact material uses.
It separates displayed occurrence, material ancestry and comparison correspondence.
The create-only `hop.scaffold-atlas-packet/v1` contains the vector scene and captured
generating request; it is a projection, not a new molecular authority.

Its preparation-bound `hop.parameter-teaching/v1` projection covers source/
association, folded-hairpin and released-insert frames. Each parameter has an exact
location reference or explicit contextual/applicability status. The companion
`teaching.svg` shares these meanings with one-state inspection and the browser.
Required thresholds, achieved spans and zero-boundary anchors remain distinct;
see the [parameter coverage contract](molecular-parameters.md).

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

See [the edit workflow](../guides/edit-folded-sequences.md) for packets, stage
boundaries and runnable examples.

## Schema inventory

This table describes the unreleased `v0.1.0a9` candidate, including construction
schemas. For the published `v0.1.0a8` wheel, use its
[tagged reference](https://github.com/e-south/hop-design/blob/v0.1.0a8/docs/reference/schemas.md).
The package version alone does not distinguish post-release source changes.

| Schema ID | Root model | Purpose |
| --- | --- | --- |
| `hop.construction-request-preview/v1` | non-authoritative authoring preview | Request digest, end footprint, explicit pairing permissions, annealing minimum and optional reference diff; no search or feasibility claim |
| `hop.request-execution-report/v1` | non-authoritative outcome report | Scope, stage, local coverage, selected continuation and pointers to preserved authorities; not a molecular result schema |
| `hop/substrate-space/v1` | `SubstrateSpaceSpec` | One labeled fixed-and-variable authored payload arm with an optional question |
| `hop.hairpin-design-set/v2` | `HairpinDesignSet` | Complete content-addressed digital design-set manifest |
| `hop.molecular-substrate-space/v1` | `MolecularSubstrateSpace` | Normalized per-position molecular authority for one substrate space |
| `hop.design/v2` | `HopSpec` | Named generic design intent |
| `hop.resolved-design/v2` | `ResolvedHopSpec` | Explicit caller-supplied components and design derivation |
| `hop.plan/v3` | `HopPlan` | Immutable compiler-owned design derivation and encoding |
| `hop.bundle/v2` | `HopBundle` | Content-addressed design artifact manifest |
| `hop.provenance/v2` | `ProvenanceRecord` | Compiler and design-reference lock |
| `hop.resolved-design-space/v2` | `ResolvedDesignSpace` | Bounded composable payload and component axes |
| `hop.design-space-plan/v2` | `DesignSpacePlan` | Renderer-free checked Cartesian review table |
| `hop.processing-catalog/v1` | `ProcessingCatalog` | Caller-supplied nicking and release agents |
| `hop.foldback-precursor-search/v1` | `FoldbackPrecursorSearchRequest` | Exact precursor materialization after placement |
| `hop.basal-candidate-search/v2` | `BasalCandidateSearchRequest` | Bounded basal arm domains and explicit heuristic-index policy |
| `hop.basal-processing-geometry-request/v1` | `BasalProcessingGeometryRequest` | Terminal processing geometry query |
| `hop.basal-processing-route-search-result/v2` | `BasalProcessingRouteSearchResult` | Bounded basal pair and processing join |
| `hop.released-foldback-geometry-request/v1` | `ReleasedFoldbackGeometryRequest` | Cross-agent foldback target and boundary window |
| `hop.released-foldback-geometry-search-result/v1` | `ReleasedFoldbackGeometrySearchResult` | Replayable geometry domains and completion evidence |
| `hop.released-foldback-precursor-search-request/v1` | `ReleasedFoldbackPrecursorSearchRequest` | Selected geometry and caller precursor domain |
| `hop.released-foldback-precursor-search-result/v1` | `ReleasedFoldbackPrecursorSearchResult` | Bounded exact precursor materialization |
| `hop.hairpin-junction-route-search-result/v2` | `HairpinJunctionRouteSearchResult` | Bounded continuity join across junction processes |
| `hop.construction-source/v8` | public file source | Strict foldback, optional PCR-basal, source-ssDNA preparation, endpoint-auxiliary resolution policies, whole-route constraints, and finite enumeration; the design bundle remains a separate verified path |
| `hop.source-partition-request/v2` | public file source | Exact source duplex, payload mapping, caller-provisioned enzyme domain, required survivor spans, preferred-to-absolute sacrificial-fragment maximum ladder, and finite subset-enumeration bounds |
| `hop.source-partition-policy/v1` | public file source | Enzyme provisioning, fragment-length rule, program width, and search bounds; the selected construction supplies the exact source and required survivors |
| `hop.source-partition-result/v2` | public discovery result | Replay-verified nick sites, full two-strand fragment certificates, threshold assessments, selected survivors, candidate dispositions, nick functions, and truthful completion status |
| `hop.source-partition-certificate/v1` | public construction projection | One explicitly selected, full-span two-strand fragment certificate with exact cleavage-boundary causes and the complete preferred-to-absolute threshold ladder |
| `hop.final-payload/v1` | internal construction model | Final-product payload coordinates, authored reference strand, boundaries, and derived pairing authority |
| `hop.local-neighborhood-request/v7` | internal construction model | Finite foldback or PCR-basal geometry domain, route, local endpoint, enzyme policy, retained-overhead ceiling, and search bounds |
| `hop.neighborhood-discovery-result/v6` | internal construction model | Shared retained-overhead accounting, geometry grouping, provenance, completion, feasibility, and termination semantics |
| `hop.foldback-neighborhood-result/v5` | portable local construction result | Replayable exact duplex foldback realizations with nick-strand, source-orientation, molecular lineage, and retained-overhead authorities |
| `hop.foldback-sequence-request/v1` | public file source | Payload, finite geometry domain, enzyme policy, retained-path ceiling, and explicit compact execution bounds |
| `hop.foldback-sequence-result/v2` | portable local construction result | Complete retained populations and joint source assignments, raw retained denominators, placement exclusions, program support, and deduplicated retained unions |
| `hop.foldback-sequence-member/v2` | public member report | Selected retained sequence, supporting program and indexed source-tail completion recovered through full molecular realization |
| `hop.basal-sequence-request/v1` | public file source | Payload, canonical basal geometry, endpoint, enzyme policy, local-span ceiling, and compact execution bounds |
| `hop.basal-sequence-result/v1` | portable local construction result | Complete local populations, raw denominators, full-source support, and deduplicated local unions |
| `hop.basal-sequence-member/v1` | public member report | A selected local word and supporting source recovered through ordinary basal molecular realization |
| `hop.sequence-set/v1` | embedded exact DNA set | Canonical reduced A/C/G/T decisions, exact cardinality, and recoverable independent-base membership |
| `hop.basal-neighborhood-result/v7` | portable local construction result | Replayable basal nick and proximal adapter-pairing realizations with retained-overhead, annealing-completion, and optional future-release obligations; full adapter materialization and PCR chronology remain whole-route concerns |
| `hop.construction-discovery-request/v7` | internal construction model | Verified design reference, local and optional selected source-partition references, source-ssDNA preparation policy, endpoint-auxiliary resolution policies, optional endpoint release, route constraints, and composition bounds |
| `hop.construction-space-result/v9` | internal construction model | Complete examined composition prefix, typed preparation-constraint diagnostics, source-preparation and selected-partition authorities, resolved exact endpoint auxiliaries, exact accepted routes, endpoint products, material accounting, grouping, and claim boundary |
| `hop.construction-bundle/v6` | portable construction manifest | Content-addressed complete-construction result with source-preparation, selected-partition, and resolved-auxiliary authorities plus embedded verified design authority |
| `hop.foldback-feasibility-landscape/v5` | public construction projection | Every exact foldback realization from one unpartitioned search with its physical nick strand, source orientation, and achieved construction dimensions |
| `hop.foldback-feasibility-landscape/v6` | public construction projection | Every exact foldback realization from one declared sequence-domain part, with its part scope and achieved construction dimensions |
| `hop.basal-feasibility-landscape/v6` | public construction projection | Every exact basal realization from one unpartitioned search with its local nick, proximal pairing, annealing-completion, retained-overhead, warning, and optional future-release facts |
| `hop.basal-feasibility-landscape/v7` | public construction projection | Every exact basal realization from one declared sequence-domain part, with its part scope and local boundary obligations |
| `hop.basal-minimum-overhead-matrix/v3` | public construction projection | Proven local retained-overhead minima, complete infeasibility, or unresolved status for every declared basal nickase by future-release action cell |
| `hop.basal-minimum-overhead-matrix/v4` | public construction projection | The same basal cell relation for one declared sequence-domain part, with its exact part scope |
| `hop.foldback-overhead-frontier/v1` | public construction projection | Examined foldback retained-overhead levels from one unpartitioned search with complete or partial accounting |
| `hop.foldback-overhead-frontier/v2` | public construction projection | Examined foldback retained-overhead levels from one declared sequence-domain part with complete or partial accounting |
| `hop.basal-overhead-frontier/v1` | public construction projection | Examined basal retained-overhead levels from one unpartitioned search with complete or partial accounting |
| `hop.basal-overhead-frontier/v2` | public construction projection | Examined basal retained-overhead levels from one declared sequence-domain part with complete or partial accounting |
| `hop.complete-construction-summary/v5` | public construction projection | Lossless disposition, grouping, required external material, failure, and truncation relation over one verified complete result |
| `hop.construction-navigation/v2` | public construction projection | Summary v4 plus accepted-route geometry, retained-overhead accounting, cleavage-program enzyme IDs, retained non-payload sequence, endpoint topology, and reversible geometry membership |
| `hop.complete-construction-trajectory/v5` | public construction projection | One explicitly selected accepted realization with its source preparation, selected source-partition certificate when present, and exact molecular chronology |
| `hop.construction-selection/v1` | non-authoritative construction reference | One accepted materialized realization bound to its verified source result |
| `hop.hairpin-portrait/v1` | public construction projection | One selected joined hairpin with actual pairing geometry, joins, terminal chemistry and separately staged release interfaces |
| `hop.linear-source-hairpin-pcr-materials/v1` | `LinearSourceHairpinPcrMaterialsSpec` | Six method oligos and ligation-end preparation |
| `hop.linear-source-hairpin-pcr-materials-plan/v1` | `LinearSourceHairpinPcrMaterialsPlan` | Derived terminal bindings and material handoff |
| `hop.linear-source-multinick-hairpin-pcr-request/v1` | `LinearSourceMultinickHairpinPcrRequest` | Exact method inputs, agents, selection, and projection |
| `hop.linear-source-multinick-hairpin-pcr-plan/v2` | `LinearSourceMultinickHairpinPcrPlan` | Complete molecular-state and product derivation with a replayable restriction agent |
| `hop.linear-source-multinick-hairpin-pcr-result/v2` | `LinearSourceMultinickHairpinPcrResult` | Orthogonal method outcome and optional plan |
| `hop.method-bundle/v2` | `MethodBundle` | Content-addressed method plan and artifacts |
| `hop.workflow-view/v1` | `WorkflowView` | Renderer-independent panels and tracks |
| `hop.recorded-design-source/v1` | `RecordedDesignSource` | Original producer, snapshot, SHA-256 and byte-size bindings for explicit read-only compact capture |
| `hop.recorded-capture-origin/v1` | capture provenance | Source contract and separately identified exporter; bound by the immutable edition manifest |

The construction source, source-partition request/result, construction bundle,
and generated construction projection schemas are active external contracts through
`hop_design.construction`. The request and result schemas in that pipeline are
active replay authorities but remain internal: callers do not construct or
import their raw models through the public facade.

The optional `whole_route_constraints.hairpin_scaffold` object specifies
inclusive `minimum`/`maximum` ranges for `open_side_paired_positions`,
`loop_side_paired_bp` and `loop_nt`. Missing dimensions are unconstrained;
equal boundaries are exact values. It is carried into complete request identity.
An out-of-range complete candidate has rejection code
`hairpin-scaffold-outside-request`, exact `scaffold_mismatches`, and retained
`scaffold_rejection_candidates` for replay. Empty optional fields are omitted,
preserving existing unconstrained request/result bytes. Older readers that
do not support these fields reject them; no compatibility conversion occurs.

Authored construction and local-neighborhood source documents are limited to
one megabyte. Public local-neighborhood requests may declare at most 100,000
search nodes and 100,000 realizations. Portable local-neighborhood result JSON
is bounded separately at 64 MiB because it records complete candidate,
rejection, and replay evidence. Result loading enforces the embedded execution
limits before replay. Searches that would exceed either envelope may use a
declared canonical `sequence_partition` of 2 through 256 parts. Every part is a
replayable local authority over a deterministic, disjoint portion of the exact
sequence domain; realization and construction-problem identities remain
unchanged. A part may be complete for its declared domain but reports
whole-domain payload compatibility as `not_computed`. Partitioning is
incompatible with all-member compatibility constraints. A caller must
verify every ordered part, reject truncation,
and prove pairwise-disjoint realization membership before describing the family
as an exhaustive aggregate. HOP never silently narrows or publishes an
undeclared partial local authority.

`hop.foldback-nucleotide-exemplar/v1` and
`hop.foldback-geometry-count-table/v1` are reserved projection identifiers in
the foldback inventory. No current public model, renderer, or reader accepts
them, and an inventory entry marked `not_generated` is not an artifact claim.

Serialized documents use the JSON key `schema`. Exact IDs are dispatch
contracts: unknown or retired versions fail and are never interpreted as the
nearest known schema. Public models are strict, frozen, and reject unknown
fields. HOP provides no old-version readers, aliases, or artifact-name fallback.

Current basal future-release and complete release-side requirements mandate
`payload_end_offset_bp`. The source, local request, embedded neighborhood,
family result, complete request/result/bundle, and dependent projection schemas
bind this coordinate contract explicitly. Historical artifacts require their
recorded producer; the current runtime does not supply a missing zero offset.

`hop.load_spec(path)` accepts only `.json`, `.yaml`, and `.yml`, and only the
two current single-design authored schemas. The scientist-facing CLI dispatches
`hop/substrate-space/v1` explicitly through `hop_design.spaces`; it does not
extend the single-design loader or guess from fields. Design spaces, catalogs,
plans, bundles, and workflow views use their own strict models or integrity
operations.

Breaking-history rationale belongs in the [decision index](../architecture/decisions/README.md),
not in the active schema contract.

The listed construction schemas form one fail-closed cut and accept no retired
source, request, result, or bundle version. The named-method v1 material
schemas remain a separate exact-method contract and retain their exact oligo
fields.

The current development cut uses construction-space-result v9 and complete-route
implementation 11. Released inserts carry `release_evidence` with a source-anchored
hairpin-core projection in the PCR parent, the actual released union, and the
retained span on each parent strand. These are distinct coordinate records: a
release may retain additional construction sequence or remove outer core bases,
while preserving both supplied-stem copies and the intervening foldback on both
strands. Unreleased endpoints retain their endpoint `encoding_projection`.
Supplying both forms, neither form, or the retired clone encoding-only form fails.

Replay independently derives the core occurrence from the source and primer
extension, and the retained spans from the four cuts. PCR sequence-fate spans
follow those per-strand retention boundaries. Complete summary v5 still seals
violated preparation constraints into replay; diagnostics report evaluated
constraints, not minimal conflicts or necessary repairs. Retired v8/implementation
10 bundles require their recorded producer or regeneration from preserved inputs.
Do not relabel old authorities. See [ADR 0053](../architecture/decisions/0053-separate-hairpin-core-and-insert-release.md).

Scaffold-family inputs use `hop.construction-family/v1`: one strict product
request, 1–64 explicitly named variations, shared properties, optional display
preferences and aggregate execution bounds. `hop.construction-family-preview/v3`
and `hop.construction-family-result/v1` summarize expansion and per-member
execution; `hop.construction-family-packet/v1` hashes packet artifacts. A packet
manifest excludes itself. Existing local/design/construction authorities retain
molecular and coverage meaning.

`hop.construction-set/v1` names explicit complete selections, baseline, shared
and compared properties. `hop.construction-set-summary/v2` binds resolved
identities and properties; `hop.construction-set-packet/v1` inventories portable
member authorities, portraits, preparations, comparisons and consolidated
chemical order specifications. Absolute input paths are not part of set identity.
Reopening portable membership repeats authority verification. No set-manifest
reader is introduced as an alternative to that replay.

`hop.construction-comparison/v2` binds two exact selections and recorded property
differences, including region sequences, absolute spans, local contacts and
material-role changes. The human label and machine field are separate entries.
The projection is derived evidence, not a complete molecular authority.


`hop.scaffold-comparison/v1` compiles a product/vary/hold brief to the existing
family request. `hop.construction-family-result/v2` records explicitly reconciled
continuations and parent lineage; ordinary execution remains v1. Report v3 adds
separate family/selected-set molecular controls and explicit recovery facts. Molecular authority
schemas and IDs remain unchanged. See [ADR 0039](../architecture/decisions/0039-scaffold-comparison-and-revision.md).


The family and set shared-property vocabulary also accepts `non_loop_sequences`,
`regional_contacts` and `regional_joins`. These bind region-local molecular facts
and stage, independently of absolute-coordinate movement and preparation changes.
Set summary v2 uses set identity version 2. Report v3 keeps required agreement,
observed agreement, differences and missing evidence distinct. Existing immutable
family and molecular records are not rewritten; regenerate only derived views.
See [ADR 0040](../architecture/decisions/0040-explicit-comparison-controls.md).

`hop.construction-family-preview/v3` records all dimension-level conflicts with
canonical declaration paths and explicit edit options. Its `preview.svg` depicts
intent, not a completed molecule. Earlier previews remain historical artifacts.
`hop.family-matching-result/v1` records the declared complete reference,
original and continued choices, shared-property agreement and bounded coverage.
`hop.family-matching-packet/v1` hashes its portable evidence inventory; underlying
molecular authorities remain unchanged. See
[ADR 0041](../architecture/decisions/0041-reference-bound-family-matching.md).


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
branch/continuation evaluation. The [request contract and workflow](../guides/discover-product-scaffolds.md)
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
impossibility. See the [bounded receiving-end example](../guides/discover-product-scaffolds.md).

`hop.scaffold-discovery-preview-packet/v1` preserves the authored request and
`hop.scaffold-discovery-preview/v1` effective requirements and unevaluated branches.
`hop.scaffold-discovery-packet/v1` adds complete inner options, failures and the
`hop.scaffold-discovery-result/v1` summary. Admission rederives the preview and
replays each inner authority before named selection. Product-stage hashes are
comparison keys, not replacements for construction identities. The selected
ordinary set may also contain `hop.selected-scaffold-stages/v1` as a projection
of its verified molecules and explicitly named membership. See
[ADR 0043](../architecture/decisions/0043-product-driven-scaffold-discovery.md).

## Comparison briefs and independent hairpin endpoints

`hop.comparison-brief/v1` embeds a strict scaffold discovery and declares purpose,
required membership, shared hairpin properties, preserved material roles and
bounded assignment evaluation. `hop.comparison-preview/v1` and
`hop.comparison-preview-packet/v1` preserve its effective domains and conflicts.
`hop.scaffold-comparison-result/v1` records verified option groups, missing
members, failures and coverage; `hop.scaffold-comparison-packet/v1` inventories
the embedded discovery and reports. `hop.comparison-selection/v1` records the
explicit chosen set alongside ordinary portable construction-set membership.
These are derived views. See [ADR 0044](../architecture/decisions/0044-molecular-comparison-briefs.md).

The endpoint vocabulary includes `adapter_ligated_hairpin`, which requires
`materialization.adapter_ligation` and excludes endpoint PCR auxiliaries and
release. The optional field is absent from serialized requests when unused.
See [ADR 0045](../architecture/decisions/0045-adapter-ligated-hairpin-endpoint.md).

`hop.comparison-brief/v2` adds explicit groups with identical stage products within
groups and distinct products between groups. It accepts verified per-group
product references and exact-loop member selectors. The v1 purposes retain their
meaning. Optional finite `loop_sequences` in foldback geometry generate exact
`loop_sequence` targets; omitted fields retain previous serialization. See
[ADR 0046](../architecture/decisions/0046-grouped-scaffold-comparisons.md).

`hop.comparison-brief/v3` adds stage-qualified regional controls over the whole
set or a named group, required-first discovery and verified prior-material reuse.
Regional sequence and pairing controls use recorded nucleotide ancestry at the
requested stage; missing or ambiguous correspondence remains unassessed.
Terminal chemistry is assessed separately. Prior-material bindings compile to
existing fixed policies without overriding inherited requirements. See
[ADR 0048](../architecture/decisions/0048-stage-controlled-required-panels.md).

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
