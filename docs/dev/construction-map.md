# Construction workflow module map

Start from the user operation in [the documentation index](../index.md), then
choose its owner below. [Architecture](../../ARCHITECTURE.md) defines dependency
direction; this map locates the current construction workflow. Module size is
a warning signal, not a reason to separate one cohesive molecular derivation.

## Follow the primary user path

The public `construction` facade connects optional intent, complete choices,
selection, figures and materials. Browser and CLI handlers adapt that same path.
Use these owners before reaching for the lower-level discovery contracts below.

| Change | Owner relative to `src/hop_design/` | Boundary |
| --- | --- | --- |
| Stem, product and optional requirements | `design/construction/intents/resolve.py`, `context.py`, `constraints.py` | Resolve permissions without searching or choosing a preparation |
| Start, continue or reopen discovery | `design/construction/intents/execute.py`, `hairpins.py`, `hairpin_history.py` | Delegate to native search and preserve recorded coverage |
| Refine or compare complete choices | `design/construction/intents/query.py`, `refinement.py`, `comparisons.py` | Preserve request intent and exact selected identities |
| Parameter meaning and dependencies | `models/construction/variants/parameter_contract.py`, `parameter_catalog.py`, `applicability.py` | Units, measurement boundaries and applicable endpoints; no display-derived molecular facts |
| Descriptor and molecular similarity | `design/construction/navigation/molecular_descriptor.py`, `similarity.py`, `numerical/` | Project verified molecules; distance and layout do not establish construction validity |
| Frozen atlas capture and inspection | `design/construction/editions/capture.py`, `compact_capture.py`, `reader.py`, `authority.py` | Distinguish original molecular producer from current rendering |
| Shared glyphs and figure composition | `export/construction/molecular/`, `export/construction/survey/` | Render recorded facts and addresses without new chemistry |
| Browser selection and asynchronous preview | `commands/design/inspection.py`, `inspection_hover.py`, `inspection_worker.py`; `assets/design_explorer/` | Adapt public choices; keep preview separate from committed selection and own teardown |

Companions call public `hop_design.construction` operations and
`hop_design.api.runtime_identity`. They own selected inputs, captions and plate
composition. They must not depend on these implementation paths. The architecture
checker rejects lower-layer imports of both CLI registration and command adapters;
command adapters may compose other command adapters.

## Change the smallest owning layer

Paths below are relative to `src/hop_design/`.

| Responsibility | Owner | Keep outside it |
| --- | --- | --- |
| Strict external request meaning | `models/construction/` | File access, search execution and display policy |
| Molecular replay and literal geometry | Model-safe replay modules and `kernel/construction/` | User selection, study interpretation and report layout |
| Compile permitted preparation branches | `design/construction/discovery/branches.py`, `constraints.py`, `methods.py`, `terminals.py` | Packet publication, file loading and rendering |
| Preview a discovery request | `design/construction/discovery/prepare.py` | A second branch compiler or molecular solver |
| Required targets and a shared bounded schedule | `design/construction/discovery/targets.py`, `scheduling.py` | Silent relaxation, per-member independent budgets or preference scoring |
| Execute complete options and record coverage | `design/construction/options/` and `discovery/explore.py` | Selecting the user's preferred preparation |
| Assess a deliberate comparison | `design/construction/comparisons/` | Recomputing molecule facts from report labels |
| Explicit family admission, recovery and retrieval | `design/construction/families/` | Product-first search policy or study-specific membership |
| Admit selected authorities and bind exact member identities | `design/construction/families/set_members.py` | Set report assembly or discovery scheduling |
| Capture and publish portable inventories | `design/construction/packets/` | Family-reference policy or molecular admission |
| Project and render recorded products | `design/construction/projections/` and `export/construction/` | New molecular conclusions inferred from drawings |
| Public operation and CLI adaptation | `construction.py` and `commands/construction/` | Raw internal-model authoring or duplicated derivations |

Discovery preview compiles branches without searching. Execution consumes that
plan and records complete options, examined failures and unexamined coverage.
Comparison assessment uses verified facts at the requested stage. Retrieval
preserves explicit membership and exact preparation identities. These remain
separate operations even when one public command composes them.

The branch compiler is pure with respect to file I/O: it receives a strict request
and returns candidate requests and conflicts. Source loading, protected input
roots, packet identity and preview rendering stay in `prepare.py`. Adding a
permitted preparation transformation should therefore not require changing the
file/packet adapter. Complete molecular admission still owns whether a branch
actually produces the requested scaffold.

## Interface survey and completion search

The survey is an execution owner over the existing molecular compiler, not a
second chemistry implementation. Keep these reasons to change separate:

| Responsibility | Owner relative to `src/hop_design/` |
| --- | --- |
| Molecular domain, target addressing and execution limits | `models/construction/surveys/` |
| Joint recognition obligations and end-pair projection | `kernel/construction/release_constraints.py`, `release_pair_relation.py`, `release_pair_projection.py` |
| Consequential context grouping | `kernel/construction/source_context.py`; survey adaptation in `design/construction/surveys/completion/binding.py` |
| Frame reuse and fair resumable traversal | `design/construction/surveys/completion/frame_admission.py`, `geometry.py`, `execute.py` |
| Request-bound local populations | `design/construction/surveys/partitions.py`; request meaning stays independent of optional cache storage |
| Allocation among targets, geometries and sequence members | `design/construction/surveys/schedule.py`, `geometry_order.py`, `navigation/`, `completion/` |
| Transactional records and exact selected-witness admission | `design/construction/surveys/index.py`, `witness.py` |
| Conditional path projection and explicit selection | `design/construction/surveys/choices.py`, `selection.py`; rendering stays in `export/construction/survey/` |

Necessary relations cannot issue preparation identities. Complete compilation
still supplies route states and exact material identities. Reusing a relation,
reordering traversal or changing its storage must preserve molecular permissions,
correlations and the distinction between unsupported propagation and an empty
proved domain. Atlas inspection and retrieval must reconstruct the same
request-conditioned local page that discovery used.

The [user mental model](../start/mental-model.md#what-makes-a-complete-preparation-valid)
separates permissions, compactness, allocation, computing limits and atlas
membership. Preserve that separation when changing the implementation:

- Strict models reject malformed or inconsistent requests before execution;
  expected molecular infeasibility remains a diagnostic, not a schema failure.
- Pure constraint kernels return admitted relations or scoped contradictions.
  They do not select a paper cohort or assign preparation quality.
- Scheduling changes which legal work runs next. Its priority must not become
  a molecular acceptance threshold, and a resource stop must not become an
  exclusion proof. Checkpoint admission binds the producer, request and limits.
- `projections/overhead/complete.py` measures retained endpoint DNA from verified
  ancestry. `editions/capture.py` records explicit membership over complete
  choices. Neither derives a score from UMAP coordinates or silently changes
  search permissions.

Applications own their scientific envelope, budget, selection rationale and
publication edition. CLI and browser adapters call the shared public facade;
neither should duplicate these policies in another solver or hidden default.

Focused seams are `test_survey_end_pair_relation.py`,
`test_release_recognition_masks.py`, `test_survey_frame_admission.py` and
`test_survey_factorized_navigation.py` under `tests/unit/`, plus
`tests/integration/test_survey_conditioned_recovery.py` for the selected trace,
atlas and preparation roundtrip. See
[ADR 0052](../architecture/decisions/0052-resumable-interface-surveys.md) for the
full coverage, limit and replay contracts. Add a solver candidate generator only
behind these existing request and compiler boundaries.

## Conditional exploration owner

`models/construction/variants/` owns strict choice intent.
`design/construction/variants/` separates admission, immutable regional facts,
conditional filtering, projection and retrieval. It reuses discovery admission,
stage identity, `comparisons/controls.py` regional ancestry and portable selection.
`commands/construction/variants.py` and the editor's `VariantSession` are thin
public-facade clients. See [ADR 0049](../architecture/decisions/0049-conditional-variant-exploration.md).

Inspection has an independent request: `variants/inspection.py` keeps the choice
query unchanged; `projections/inspection.py` owns exact addresses, recorded-state
ancestry and end neighborhoods; `export/construction/molecular/inspection.py`
renders those facts. `variants/comparison.py` adapts required member selectors to
the existing bounded grouping engine. `comparison_selection.py` re-admits and
re-assesses the saved decision before retrieval. CLI and browser adapters call
those public operations. See [ADR 0050](../architecture/decisions/0050-intent-preserving-inspection-and-comparison.md).

Use `test_scaffold_variant_query.py` for choice algebra,
`test_scaffold_variant_exploration.py` for admission/retrieval boundaries and
`test_variant_editor.py` for loopback interaction. `test_scaffold_inspection.py`
covers display/query independence and lineage; `test_variant_comparisons.py` covers
required membership, bounded coverage, material controls and altered receipts. The public
`examples/molecular-editing/conditional.py` recipe measures cold admission,
100 warm queries and retrieval separately; no global cache skips verification.

`variants/preview.py` resolves a supported variant to complete preparation
backgrounds without changing the query or selecting a set. Inspection preserves
the requested processing phase. Typed operation annotations and contact layout
belong in `projections/inspection_annotations.py` and `inspection_layout.py`;
`export/construction/molecular/inspection_overlays.py` draws those facts.
Persistent footprints live in `projections/inspection_sites.py`, separately from
operation timing. `inspection_correspondence.py` owns verified processing and
comparison links. The shared static scene is `molecular/inspection_scene.py`;
frontend continuity, motion, camera and molecular labels have separate modules.
The editor separates navigation, query editing, comparison and retrieval through
the same public operations. Preview and inspection tests cover ambiguity, phase
preservation, exact recognition spans, strand-specific cuts and contact layout.

The all-state contract is `models/construction/projections/atlas.py`.
`projections/atlas.py` composes existing recorded-state inspections, correspondence
and exact material uses; it derives no new chemistry. `variants/atlas.py` binds
that projection to the admitted pool and query. `atlas_comparison.py` attaches
fixed-reference correspondence, while `envelope.py` reports declared versus
achieved constraints. `molecular/atlas_layout.py` aligns scenes; `atlas.py`
composes the shared vector export. `label_layout.py` provides one collision domain
for recognition, cut, dimension and primer labels. Browser `atlas_view.js` consumes
the export, `local_choices.js` owns anchored conditional choices, and `camera.js`
changes only the view. None of these modules evaluates additional candidates.

`test_molecular_atlas.py` checks exact state composition, occurrence uniqueness,
primer-input context, stable focus, query preservation and CLI/API parity.
`tests/browser/atlas_camera.test.mjs`, `atlas_choices.test.mjs` and
`variant_motion.test.mjs` cover camera arithmetic, complete-route filtering,
state-qualified animation keys and superseded responses. Browser cache entries
remain bound to verified result/query/preview identities; retrieval re-admits.

## Focused checks, then the repository gate

Molecular editing composes the same machinery: `models/construction/molecular/edits.py`
binds stage/region changes to an original discovery request; `design/construction/edits/`
owns preview, execution, sequence projections and verified retrieval. Finite end
placements and basal nickase alternatives belong in `discovery/placements.py`,
and use the existing required-target scheduler. `commands/construction/editor/`
serves a loopback interaction through the public facade; it contains no chemistry.
Folded views and static plates remain export-owned. `sequence_families/` expands
a bounded stem domain into ordinary exact discovery requests and verifies complete
membership through the existing set/material contracts. `test_molecular_edits.py`,
`test_molecular_end_edits.py`, `test_molecular_editor_http.py` and
`test_sequence_family.py` cover these boundaries, including relocation and failures.

Use the existing contract tests nearest the changed behavior:

| Change | Focused tests under `tests/integration/` |
| --- | --- |
| Preparation branches and terminal requirements | `test_scaffold_discovery.py`, `test_terminal_scaffold.py` |
| Target scheduling and finite coverage | `test_required_member_search.py`, `test_scaffold_discovery_boundaries.py` |
| Stage relationships and shared controls | `test_grouped_comparison.py`, `test_stage_comparison_controls.py` |
| Prior materials and product preservation | `test_prior_material_reuse.py`, `test_comparison_product_reference.py` |
| Portable selections and family reporting | `test_family_report_boundaries.py`, `test_construction_set.py` |

Run a selected file with `uv run --locked pytest -q PATH`. Documentation metadata,
routes and headings are checked by `uv run --locked python scripts/check_docs.py`;
dependency direction by `uv run --locked python scripts/check_architecture.py`.
Choose the [verification boundary](performance.md#choose-the-verification-boundary)
for the changed responsibility. Repository-only checks and documentation use
focused integrity checks; molecular changes require source verification. Full
source/distribution verification remains required before merge or release.

## Maintenance boundary

Keep examples and public documentation independent of downstream study paths.
Plans retain delivery decisions; guides describe the usable operation; references
define contracts. The [roadmap](plans/roadmap.md) separates candidate capabilities
from remaining work and published artifacts. Generated `.artifacts/` and `build/`
content is verification output, not another source tree to refactor.

Review this map when adding an operation or moving a responsibility. Split a
renderer or validator only when it mixes reasons to change; preserve exact
sequence, chemistry, failure scope, coverage and serialization behavior during
structural cleanup. New molecular capabilities require a separate tested slice.

## Measure verification cost without weakening admission

Use [Measure construction performance](performance.md) for the public lifecycle
benchmark, receipt-reuse boundaries, cache lifetime and test staging. It separates
search, admission, retained queries and retrieval instead of treating total runtime
as one bottleneck.

The regression seams are `test_construction_bundle_replay_cost.py` for whole-route
and publication checks, `test_local_replay_scope.py` for bounded local proof reuse,
and `test_comparison_journey.py` for selected-set admission. All use the same
molecular authority as the public API and CLI.
