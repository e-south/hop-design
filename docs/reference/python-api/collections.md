# Create and reopen design collections

Use a substrate space when you need every member of a bounded authored design
set. Use an atlas edition to capture an existing discovery's choices, drawings
and materials for later inspection. The live discovery checkpoint remains the
authority for continuation.

Return to the [Python API task index](../python-api.md) for other operations.

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

See the [design-set layout](../design-set-layout.md) and
[substrate-space guide](../../guides/substrate-spaces.md).

## Frozen atlas editions and guided exploration

The operations in this section use `hop_design.construction`.

`combine_design_discoveries(request, directories, destination) -> AtlasEdition`
captures one compact edition from 2–256 disjoint, stopped released-insert
discoveries. The explicit parent intent binds the unchanged stem and all molecular
permissions. The input target grids must cover its Cartesian end-pair grid exactly
once, with identical effort policies and current producer admission. Empty jobs
retain their coverage. The result is read-only; each original checkpoint remains
the continuation authority. See [independent jobs](../../guides/share-atlas-edition.md#combine-independent-discovery-jobs).

### Capture and load an edition

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
[recorded capture](../../guides/share-atlas-edition.md#capture-a-recorded-discovery-with-an-updated-exporter).

### Inspect parameters, families and guided samples

The following shared operations apply to live `DesignChoices` and frozen
`AtlasEdition` objects.

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

### Record and restore an inspection

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
separate. See [the edition guide](../../guides/share-atlas-edition.md).
