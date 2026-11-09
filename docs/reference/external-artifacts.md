# External command and artifact interface

## Question answered and meaning

Invoke a selected HOP executable with explicit file arguments and consume its
JSON reports and published artifact directories. This interface avoids importing
HOP's Python models into the caller's environment. HOP derives and replays the
molecular records; the caller supplies the scientific question, acceptance rules,
and evidence records.

The executable runs in an independently installed environment. The caller
selects and records its immutable source revision and execution command; HOP
does not discover, install, or update another environment.

## Authored inputs and operations

Commands below emit one JSON report on stdout; errors return nonzero. `OUT`
must name a new directory outside any input bundle, including when paths pass
through symbolic links. Method request files must use `.json`; duplicate keys
are rejected before model validation. File arguments retain the schemas of the
[design](bundle-layout.md), [method](method-bundle-layout.md), and
[construction](construction-bundle-layout.md) authorities.

| Operation | Command |
| --- | --- |
| Identify the executing installation | `hop-design identity` |
| Derive a design without publication | `hop-design compile --spec SPEC --dry-run --report` |
| Publish a design | `hop-design compile --spec SPEC --out OUT --report` |
| Replay a retained single-design bundle | `hop-design verify BUNDLE --report` |
| Discover a local neighborhood | `hop-design construction discover-local REQUEST --out OUT` |
| Replay a local result | `hop-design construction verify-local RESULT_JSON` |
| Execute durable local discovery | `hop-design construction discover-batch REQUEST... --checkpoint DIRECTORY [--resume]` |
| Discover source partitions | `hop-design construction discover-partition REQUEST --out OUT` |
| Replay a source-partition result | `hop-design construction verify-partition RESULT_JSON` |
| Inspect exact local choices | `hop-design construction local-choices RESULT_JSON [--sort-by KEY]...` |
| Render one basal molecular panel | `hop-design construction basal-panel RESULT_JSON --realization-id ID` |
| Resolve a named method, including infeasibility | `hop-design method resolve-linear-source REQUEST_JSON` |
| Publish a complete named-method bundle | `hop-design method compile-linear-source REQUEST_JSON --out OUT` |
| Replay a retained named-method bundle | `hop-design method verify-linear-source BUNDLE` |

Selected-local compilation makes every source and selection explicit:

```text
hop-design construction compile-local-design
  --design-id ID --payload DNA --endpoint ENDPOINT
  --foldback RESULT_JSON --foldback-realization-id ID
  [--basal RESULT_JSON --basal-realization-id ID]
  [--hairpin-left-arm DNA --hairpin-right-arm DNA] --out OUT

hop-design construction compile-selected SOURCE
  --design-bundle BUNDLE
  --foldback RESULT_JSON --foldback-realization-id ID
  [--basal RESULT_JSON --basal-realization-id ID]
  [--source-partition RESULT_JSON --source-partition-realization-id ID] --out OUT

hop-design construction verify-complete BUNDLE

hop-design construction discover-construction-partition BUNDLE POLICY_JSON
  --combination-ordinal NUMBER --out OUT

hop-design construction project SOURCE --kind KIND --out OUT
  [--realization-id ID] [--selection-reason TEXT]
```

For `--endpoint ssdna_hairpin`, provide both exact basal-arm sequences with
`--hairpin-left-arm` and `--hairpin-right-arm`, each 5′→3′. Omit the basal discovery
selection. PCR-bearing endpoints instead require that basal selection and reject
the direct-hairpin arm flags.
`--sort-by` uses the existing ordered local-inspection preferences. A source
removal policy is applied only to the selected examined construction ordinal.
Basal panels select a `local_realization_id`; design and construction selection
instead uses the compilable `basal_realization_id` or `foldback_realization_id`.
These identities retain their existing distinct meanings.

Projection kinds are `foldback-feasibility`, `basal-feasibility`,
`basal-minimum-overhead`, `foldback-retained-overhead`,
`basal-retained-overhead`, `source-partition-certificate`,
`construction-summary`, `construction-navigation`, and
`construction-trajectory`. The last four use a partition result or construction
bundle as appropriate. A certificate and a trajectory require an exact
realization ID. Other projections reject that selector. A selection reason
applies only to a trajectory and must contain text. The trajectory directory
includes `report.md`, `oligos.csv`, and `oligos.fasta` alongside its existing
JSON/SVG projections; the caller's reason changes the report prose only.

## Derived values, identity, and lineage

Reports contain ordinary JSON. Design,
local-result, partition, method, and construction reports carry their existing
canonical authorities and SHA-256 byte bindings. Explicit metadata exposes
producer-computed dispositions, counts, and identifiers; the caller need not
duplicate molecular derivation to inspect them. Publication uses the existing
atomic writers and does not add report files to, or reseal, a bundle.
Construction reports serialize the admitted in-memory snapshot, so later file
replacement cannot mix unverified contents with the verified identities.
Selected constructions, route references, projections, and derived source
partitions publish outside their verified input bundle through an opened parent
directory. Commands capture the input directory's filesystem identity before
verification and reject replacement across that admission. Publication checks
output ancestry against the captured identity even if the admitted input is
later renamed. On macOS and Linux,
publication remains bound to that directory if an ancestor pathname is replaced
or redirected. An output already redirected into the input bundle fails before
creating children. Protected publication fails explicitly on unsupported
platforms and retains create-only destination semantics.
Selected construction bundles still undergo staged semantic verification before
publication. Their nested files and single-file references use owner-only access.

The complete `discover-batch` stdout report is limited to the existing 64 MiB
execution-document ceiling, including its envelope, separators, and newline.
HOP budgets serialized UTF-8 bytes while replaying results individually; it
does not accumulate every decoded authority. An oversized report fails with
no partial stdout after discovery has retained its complete checkpoint.
`--resume` preserves that checkpoint and applies the same report limit. Use
`LocalNeighborhoodBatch.iter_results()` for individual results, then each
receipt's `report_json()` or `write()` to retain or inspect it separately.

`identity` returns `hop/runtime-identity/v1`, distribution and dependency
versions, a digest of the executing package's Python source bytes, supported
report schemas, and available installation provenance. Git source metadata
records its commit; archive metadata records available hashes. Local source
locations and URL credentials are not exported. Installation metadata and the
actual package-content digest are separate facts: a source declaration alone
does not prove that installed bytes are unmodified.

Public file-oriented Python operations are
`hop_design.api.resolve_linear_source_method_file`,
`compile_linear_source_method_file`, and `verify_linear_source_method_file`.
They use the same method model validators and deterministic compiler as the
existing method facade. `design_report` serializes an admitted design receipt;
`runtime_identity` reports the executing installation.

## Invariants and claim made

A successful discovery or compilation command performs the existing producer
operation. A successful verification command checks retained artifact
integrity and performs deterministic semantic replay. Discovery truncation and
infeasibility remain explicit outcomes, with unchanged enumeration bounds.
Complete method publication requires a complete plan;
method resolution preserves expected infeasibility as a JSON outcome.

## Retained reports and failure semantics

A caller may retain the command report with its exact input/output digests and
execution provenance. A later parser can inspect the retained report without
executing HOP. The parser can check schema, digests, and byte consistency.
Report provenance must identify the execution; self-consistent bytes alone
cannot authenticate it. For a fresh semantic replay, run the producer's
verification command.

Missing executables, invalid request schemas, invalid selectors, corrupt
authorities, and existing output directories fail explicitly. If the selected
runtime is unavailable, restore it before replay. Historical frozen
clients may retain their original environment requirements as evidence;
they do not define a current consumer installation dependency.

## Capture a recorded discovery with an updated exporter

To package an existing released-insert discovery after updating HOP, supply an
explicit source contract. This operation reads recorded preparations; it does
not resume the search or authorize execution under a different generator.

```bash
# Bind the original producer when an updated exporter captures old records.
hop-design design freeze designs --compact --source-contract source.json --out recorded-edition
```

The same operation is available as
`construction.freeze_design_choices("designs", "recorded-edition", compact=True,
source_contract="source.json")`. Without `source_contract`, ordinary producer
admission applies. Use `include_landscape=True` or `--include-landscape` to fit
coordinates with the exporter's numerical environment.

`source.json` uses `hop.recorded-design-source/v1`. It binds the original complete
producer identity, the recorded `snapshot_digest`, and a `files` mapping with
SHA-256 digests and byte sizes. Bind `survey.sqlite`, `effort.json`, every file
in `intent/`, and every file in `revision/` when present. Obtain these bindings
from the recorded generator and completed source, before changing environments.
They are input identity checks, not evidence of exhaustive discovery.

Stop writers before capture. HOP rejects SQLite sidecars, changed inputs,
symlinks, mismatched producers and unsupported molecular records. It admits one
read snapshot, verifies every retrieved preparation through the existing
molecular checks, and rechecks source bindings before publishing. Failure
publishes no edition. The returned object is an immutable `AtlasEdition`.

The edition keeps the original producer and binds `capture-origin.json` with
the source contract and current exporter identity. Aggregate discovery replay
remains a separately recorded operation. This import supports exact-stem
released-insert discoveries, compact capture and ordinary parameter filters;
use the original producer for family or preservation-query capture.
