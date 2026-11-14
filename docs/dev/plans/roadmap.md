# HOP product roadmap

## Product direction

HOP discovers complete hairpin preparations around a supplied stem. This roadmap
maps the current checkout's capabilities and remaining work. For an installed
release, use its tagged documentation and record the runtime identity.

## Current workflows

The current workflows include complete scaffold discovery, stage-specific
comparisons, terminal hairpin requirements and explicit material reuse. Record
the runtime identity when using a source checkout between releases.

This version also includes [folded-sequence editing](../../guides/edit-folded-sequences.md):
exact loops, finite released-end placements and explicit method alternatives,
shared CLI/API retrieval, a local editor, and bounded exact expansion of a
degenerate stem.
Unrestricted nucleotide
editing, new chemistry, RNA prediction, destination validation, global optimization
and pooled-library guarantees remain outside that increment.

[Conditional variant exploration](../../guides/explore-conditional-variants.md)
adds browsing over admitted complete results: neighborhood choices narrow whole
products under fixed references and stage-qualified controls. The API, CLI and
single-molecule viewport share the query model; retrieval rechecks its constraints.
Repeated queries use immutable facts, while search expansion and control relaxation
remain explicit, separate operations.

The construction-envelope navigator adds paged permitted domains, including
words and geometries without completed preparations. Field-bound permission
revisions are previewed before explicitly bounded evaluation; replay retains
the original pool and the declared changes. The shared CLI/API/browser
contract keeps the supplied stem, receiving ends, material policies and
preservation controls fixed. The public open-domain example separates
molecular permissions from computation quotas. Its bounded results cover the
examined candidates; exhaustive satisfiability and joint optimization remain
separate questions. See [ADR
0051](../../architecture/decisions/0051-explicit-envelope-revisions.md).

Continuous molecular inspection keeps variant choice, processing state and camera
movement independent. Stage-qualified surroundings controls narrow supported
variants. Persistent recognition footprints and active cuts have separate
projections; verified correspondence follows a position while retaining copying,
material ancestry and ambiguity. Static SVG exports and the viewport consume the
same scene. Motion depicts correspondence between recorded states, not reaction
dynamics or predicted physical conformation.

## Published design-language contract

The published `v0.1.0a8` design-language changes remain documented in the
[tagged source](https://github.com/e-south/hop-design/tree/v0.1.0a8/docs).
Later releases retain their own schemas and compatibility rules.

Compact checkpoint storage was released in `0.1.0a11`. The public
[storage guide](../../reference/interface-survey-search/checkpoint-storage.md)
defines migration, integrity and producer compatibility. A development checkout
does not inherit a released producer's permission to continue old checkpoints.

## Source capabilities

Each guide owns its examples and detailed contracts.

| Task | Guide |
| --- | --- |
| Define a product, discover preparations and retrieve oligos | [Design discovery](../../guides/discover-designs.md) |
| Compile exact or DNA IUPAC sequence anatomy | [Substrate spaces](../../guides/substrate-spaces.md) |
| Search local junctions and compose a complete route | [Construction](../../guides/compile-construction.md) |
| Explore a finite grid of cloning ends with checkpoints | [Interface surveys](../../guides/survey-interfaces.md) |
| Compare complete alternatives under shared controls | [Conditional exploration](../../guides/explore-conditional-variants.md) |
| Save coordinates, selection and drawing settings | [Saved preparations](../../guides/share-atlas-edition.md) |

The [module map](../construction-map.md) locates implementation and test owners.
[Search interpretation](../../discovery/overview.md) distinguishes permissions,
evaluation limits, supported constructions and exhausted domains.

## Implemented product workflows

### Complete product options before selection

[Complete scaffold exploration](../../guides/explore-scaffolds.md), controlled-set
grouping and explicit label retrieval are implemented.
The [delivery plan](scaffold-options.md) records acceptance and verification.
The same comparison intent carries shared controls through selection. New
molecular capabilities, joint search beyond the evaluated pool and persisted
continuation resumption remain separate work.

### Product-driven preparations

[Desired scaffold dimensions](../../guides/discover-product-scaffolds.md) now drive
explicitly permitted adapter and release-method branches in this version.
Exact stage grouping distinguishes hairpins from alternative preparations of one
released product. [Acceptance and verification](product-first-discovery.md) remain
with the delivery plan. This does not add joint molecular optimization or new chemistry.

### Explicit comparative sets

The [comparison brief](../../guides/specify-a-comparison.md) names required
members, shared properties and permitted preparation changes. Its versioned
grouped form requires identical stage products within scaffold groups and
different products between groups. Verified prior-product references and exact
loop words retain their molecular meaning through discovery and retrieval. The
[grouped-comparison plan](grouped-comparisons.md) owns delivery verification.
Public release remains a separate gate.

### Terminal forms, stage controls and prior-material reuse

The [terminal-scaffold delivery plan](terminal-scaffold-comparisons.md) records
high-level unpaired terminal requirements for the adapter-ligated hairpin,
explicit permitted tail sequences, stage-qualified non-loop controls,
required-member-first bounded scheduling and verified prior-material reuse.
These compose existing molecular authorities. They do not infer arbitrary tail
bases, certify assembly compatibility or make a stopped search exhaustive.

### Molecular organization of conditional exploration

The source implementation adds parameter roles and boundary semantics, explicit
request-fixed versus observed-constant status, and source-primer failure diagrams
shared by CLI/API exports and the explorer. Required primer footprints and
available source flanks remain separate; zero extents retain boundary anchors.

The preparation-bound `teaching` projection and `teaching.svg` now cover source/
association, hairpin and insert frames. Browser and static exports share exact
parameter locations; selected contacts expose source/adapter/class together.
A connected short-wide plot replaces the five axis menus, with local detail from
the molecular key and persistent receiving-interface context. Same-record agent
comparison favored the connected plot over three repeated regional strips.

Discovery v6 adds a finite joint receiving-end roster. Words, polarity, orientation
and placements remain one permission, with no undeclared crossed combinations.
Brushing existing evidence, changing permissions and requiring every member
remain distinct actions. Agent-operated browser and CLI/API tasks cover primer
failure, loop changes, zero-gap coverage and explicit end-pair retrieval. A fixed
comparison reference, processing state and zoom survive preparation changes.
Installed-wheel exports match source outputs for discovery, teaching, atlas and
retrieval. The full repository verification endpoint remains the delivery gate;
unfamiliar-user evaluation remains separate
from these software checks.

## Remaining product work

### Bounded scaffold completion

Upstream completion searches a caller-authored fixed-length IUPAC pattern or
an inclusive length range with an explicit base domain. Every examined length
and sequence retains its own disposition; a stopped prefix remains truncated.
Interface surveys additionally offer explicit `paired_scaffold_completions`:
preserve context length and sequence dependencies of basal pairing and the
released insert, then seek one exact handle completion per local group. Unknown
coordinate frames retain all context positions. A bounded resumable queue
interleaves unfinished completions with other local pairs and geometry; exact
initial-source site predicates can exclude conditional subsets. This does not
enumerate all unpaired hairpin sequences or all preparations, nor establish a
compact complete relation over the entire coupled construction problem.
Source-partition search still evaluates a supplied exact source. Constraint-directed
joint design of source sequence, cleanup-nick tiling, and a required fragment
partition remains unimplemented; bounded upstream enumeration alone is not
global scaffold design.

### Resumption within one local query

Checkpoints persist completed independent queries. A local query still assembles
its result in memory; partial-query coverage and realization streaming are not
persisted. Collection resumption does not remove this limit or make a truncated
query exhaustive.

### Bounded symbolic method assessment

Exact method compilation remains exact. A separate pool assessment must reason
over correlated DNA IUPAC domains and distinguish universally feasible,
possibly feasible, exhaustively infeasible, and truncated outcomes without
silently enumerating an unbounded pool.

### Interoperability mappings

SBOL and PROV may project stable HOP objects and typed relations after consumer
demand is demonstrated. They do not drive or replace the internal ontology.

## Release gate

Every prerelease requires:

- contract-first negative and replay tests;
- source and installed-package qualification, plus supported-Python CI;
- no unresolved high-severity correctness or information-architecture finding;
- wheel/sdist build, clean install, metadata, and source/wheel parity;
- protected-main tag ancestry and published SHA-256 checksums;
- no private application data or caller-repository dependency.

## Consumer adoption gate

A downstream system installs one immutable release artifact and preserves
verified features and identities without reconstructing molecular facts. Its
execution, review, and evidence policy remain independent of HOP's release gate.
Rollback is deployment of a prior coherent revision and pin, not a runtime fallback.

Public HOP documentation records these generic gates. Consumer-specific status,
repository SHAs, infrastructure blockers, and migration evidence remain in the
owning system.
