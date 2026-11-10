# Compile and inspect construction routes

Use `hop_design.construction` to compile a product request or compose exact
verified local selections into a complete route. An accepted route can then be
selected, inspected and exported with its materials. For the preceding search
operations, see [local construction regions](local-search.md).

Return to the [Python API task index](../../python-api.md) for other operations.

## Payload-centered construction

- `execute_construction_request(path, *, design_id, continuation="sole-witness")`
  returns an opaque `ConstructionRequestExecution`. The continuation argument is
  required: this policy only continues when every required local search records
  one witness. It neither ranks nor relaxes the request. `json_bytes` contains
  the scoped outcome and exact producer identity; `report_text` explains what
  was obtained or why execution stopped. Create-only `write(destination)` saves
  inputs, local results, and any design, complete-construction and handoff
  artifacts. Expected absence is a report, not an exception; malformed input
  remains an error. Independent hairpin execution requires explicitly authored
  `hairpin_basal_component` arms. See the [execution decision](../../../architecture/decisions/0038-bounded-request-execution.md).
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
  construction. See the [authoring decision](../../../architecture/decisions/0037-product-request-authoring.md).

### Compile from a construction source or local selections

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

### Load and select an accepted route

- `load_verified_construction_bundle(path) -> VerifiedConstructionBundle`
  checks portable bytes and semantically replays the embedded design, local
  authorities, complete result, and root manifest.
- `select_construction_realization(receipt, materialized_realization_id=...) -> ConstructionSelection`
  creates a stable non-authoritative reference to one accepted exact route.
- `load_construction_selection(path, receipt=...) -> ConstructionSelection`
  safely loads a selection and cross-checks its result and realization against
  the supplied verified receipt.

### Reuse one verified result

Import `hop_design.construction as construction` before running this example.

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
The receipt is the verified result held in memory. Reload to inspect current disk
bytes; every load still checks integrity and repeats semantic replay. No
persistent verification cache is used. Malformed side/negative-index CLI
arguments fail before replay; product-dependent bounds require the verified
product. Bundle loading reconstructs its manifest from the fresh replay result
without replaying that same result a second time.

## Inspect and compare complete routes

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
  [comparing completed choices](../../../guides/compile-construction.md#compare-completed-choices).

## Receipt contents and exports

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

### Read a selected route and its ends

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

### Protect verified inputs during publication

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

See the [construction guide](../../../guides/compile-construction.md), the
[source-partition guide](../../../guides/discover-source-partitions.md),
[construction-bundle layout](../../construction-bundle-layout.md), and
[construction projection contracts](../../view-contracts/complete-preparation-views.md#complete-construction-projections).
