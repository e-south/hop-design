# File facade, receipts and local construction

This part of ADR 0027 records the file boundary, public allowlist and receipt contracts
for local and complete construction.

Read the [parent decision](../0027-file-oriented-construction-facade.md) for its context
and the other topic records.

## Decision

`hop_design.construction` is the file-oriented construction facade. The caller
provides one strict `hop.construction-source/v8` JSON or YAML file and one
separate verified design-bundle path. HOP loads and verifies the design
bundle, discovers and verifies the declared foldback and optional basal
neighborhoods, derives the source ssDNA and source-preparation primers under
their declared policies, produces the exact source duplex, optionally binds
one selected replay-verified source partition, resolves PCR endpoint
auxiliaries under their declared policies, composes the route, and returns an
opaque `ConstructionCompilation` receipt. The receipt exposes supported
inspection and writing operations while keeping internal model constructors
private.

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
bundle, result identifier, realization identifier, projection choice, output
path, timestamp, or environment record. Direct, PCR, and clone-ready endpoints
have fail-closed structural requirements.

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
select facts from the typed trajectory using its existing schema and lineage.
Model constructors remain internal. `ProtectedRoot` retains an input
directory's filesystem identity across verification and protected publication.
Its mechanics remain in the existing publication owner; it is neither a
molecular model nor portable evidence. Selection references expose only the
source result identity, one accepted materialized-realization identity, and
canonical JSON. They remain non-authoritative: creating or loading one
requires a verified construction receipt, and loading cross-checks both
identities against that receipt. `LocalRealizationChoice` exposes immutable
inspection facts, including the achieved geometry and the family identity
required by compilation. Explicit filters and ascending preference keys
operate on recorded witnesses only; they neither search unenumerated sequences
nor certify a complete construction. The original receipt remains necessary to
compile a selected identity. `compare_constructions` consumes two verified
receipts and explicit accepted realization identities. It returns a read-only
Markdown comparison of recorded material, retained-sequence, processing-order,
and endpoint properties. It is not a serialized molecular authority, ranking,
or equivalence certificate. Source, result, projection, molecular-state, and
bundle-manifest constructors remain internal. Loading a portable construction
bundle performs both integrity and semantic replay, so the facade does not add
a redundant verify verb.

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
another molecular engine. See the [folded-sequence guide](../../../guides/edit-folded-sequences.md).

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
receipt. It verifies only the declared foldback or basal neighborhood. A complete
route still requires composition and its own verification.

Exhaustive foldback population discovery may return compact exact sequence sets
through `FoldbackSequenceSpace`. Its strict file request declares finite geometry
and execution bounds; every exact payload/geometry/strand case retains its raw
population, per-program support, and admitted union. Loading repeats complete
deterministic discovery. Computational exhaustion raises without a completed
receipt, and enzyme aliases cannot multiply sequence configurations. Explicit
member recovery uses ordinary full molecular realization for one case, sequence
rank, and supporting program. These operations retain local search
scope and keep internal model constructors private.

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

The source compiler reports complete, infeasible, or truncated discovery. This is
an intentional prerelease public-surface addition with no compatibility alias
for internal import paths.

`PreparedConstructionRequest` records translated input, not a verified molecular
receipt. `prepare_construction_request` shares one strict intent translator with
the CLI and expands to existing source contracts. See
[ADR 0037](../0037-product-request-authoring.md) for the authoring boundary.

`ConstructionRequestExecution` and `execute_construction_request`, `continue_construction_request` add an explicit
bounded continuation over those same authorities. Their report
summarizes the local results, design bundle and
any complete-construction
bundle retained in the delivery. See [ADR 0038](../0038-bounded-request-execution.md).
