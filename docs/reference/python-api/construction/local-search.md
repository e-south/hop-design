# Discover local construction regions

Use `hop_design.construction` to find foldback or basal realizations before
compiling a complete route. Supply a strict local request. Inspect its recorded
witnesses and select exact identities for [route compilation](routes.md).
Local sequence spaces describe the declared finite domain, while source-partition
operations check which strands survive a removal program.

Return to the [Python API task index](../../python-api.md) for other operations.

## Local foldback and basal neighborhoods

- `discover_local_neighborhood(source_path) -> LocalNeighborhoodDiscovery`
  runs one strict foldback or basal neighborhood request and returns an opaque,
  replay-verified local family receipt. Large exact
  sequence domains may declare one canonical `sequence_partition`; each result
  remains complete only for that part, preserves molecular realization ids, and
  does not claim whole-domain payload compatibility.
- `load_verified_local_neighborhood(result_path) -> LocalNeighborhoodDiscovery`
  loads only the active foldback or basal family result schema and repeats exact
  deterministic discovery replay.
- `list_local_realizations(receipt, cohesive_end=None, max_retained_overhead_nt=None,
  max_noncanonical_pairs=None, sort_by=()) -> tuple[LocalRealizationChoice, ...]`
  lists recorded local witnesses with their compilable family identity, typed
  geometry, retained sequence, enzymes, pairing classes, and adapter completion
  requirement. Filters do not rerun the search. Sort keys are ascending
  `retained_overhead_nt`, `noncanonical_pairs`, or `enzyme_count`, applied in
  caller-specified priority with stable ties. Pairing and end filters require
  basal evidence. Rows are immutable inspection values, not verified receipts;
  compilation still checks the selected identity against its original receipt.

## Exact local sequence spaces

- `discover_basal_sequence_space(source_path) -> BasalSequenceSpace`
  evaluates a finite canonical basal domain, admits complete source contexts,
  then projects exact local sequence sets. Different enzyme programs or source
  contexts do not multiply the local count. Other pairing permissions raise.
  Computational exhaustion cannot return complete authority. See the
  [basal sequence-space guide](../../../guides/basal-sequence-space.md).
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
  complete receipt. See the [sequence-space guide](../../../guides/foldback-sequence-space.md).
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

## Checkpointed collections of local requests

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
  [checkpointed discovery](../../../guides/checkpoint-local-queries.md)
  for limits, persistence, and recovery semantics.

## Source partitions and removal programs

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
  [checking source removal](../../../guides/select-construction-junctions.md#check-removal-for-a-selected-source).

Source-partition nick functions distinguish a retained-fragment boundary from
excluded-fragment cleanup. Canonical enzyme
subset order is replay metadata, not rank. PCR handles are outside this local
search.

## Project local evidence

- `project_basal_source_panel(receipt, realization_id=...) -> bytes` emits the
  existing neutral molecular panel as canonical JSON for one verified local
  basal realization. It preserves source coordinates and exact local pairing
  facts; route selection is separate.
- `project_foldback_feasibility(receipt) -> ConstructionProjection`
- `project_basal_feasibility(receipt) -> ConstructionProjection`
- `project_basal_minimum_overhead_matrix(receipt) -> ConstructionProjection`
- `project_retained_overhead_frontier(receipt, family=...) -> ConstructionProjection`
- `project_source_partition_certificate(receipt, realization_id=...) -> ConstructionProjection`

See the [source-partition guide](../../../guides/discover-source-partitions.md) for a
complete removal workflow and the [projection contracts](../../view-contracts/complete-preparation-views.md#complete-construction-projections)
for packet contents.
