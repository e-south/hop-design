# HOP Design architecture

HOP Design is a standalone modular monolith: one repository, one Python
distribution, one public API, and no dependency on caller repositories.

## Product boundary

The deterministic core has two sibling compilation spines:

```text
HopSpec -> design derivation -> HopPlan -> HopBundle
MethodRequest -> resolve states -> MethodPlan -> MethodBundle
```

HOP owns its ontology, minimal DNA/IUPAC kernel, junction contracts, design
resolution, bounded processing-geometry discovery, explicit molecular-event
evaluation, paired non-payload stem context, route-material binding,
deterministic artifacts, typed workflow views, and integrity
verification. It does not own workspaces, runs, samples, observations,
experimental evidence, assay semantics, larger construct placement, private processing
catalogs, or private application profiles. Callers link their own records
through neutral external references.

The accepted construction-discovery graph is payload-first:

```text
final-payload specification + route family + requested endpoint
  |-> foldback local realizations
  |-> basal local realizations
  |-> source-partition realizations
  `-> endpoint materialization
                  |
                  v
       staged whole-route composition
                  |
                  v
       exact endpoint products and reversible projections
```

Local junction discovery owns only the sequence and reaction geometry at one
payload boundary. Source-partition discovery owns provisioned nickase subsets,
all actionable sites, denatured fragments, length selection, and the exact
required survivor relation. PCR handles, primer binding, Type IIS release, and
other endpoint periphery are route-materialization concerns. A study may run
these bounded operations independently. Complete composition uses only the
authorities explicitly present in its request.

The public construction entrypoint loads strict source files and verified
authorities, keeps replay models internal, and returns an opaque receipt:

```text
verified local receipts + explicit realization ids
  -> route-neutral exact design authority

strict construction source + separately verified HopBundle
  -> verified local authorities
  -> verified complete construction
  -> opaque receipt
  -> portable ConstructionBundle or neutral projection packet

strict construction source + matching HopBundle + selected local ids
  -> verify the exact local receipts and source relation
  -> evaluate and materialize one foldback-basal pair
  -> the same opaque receipt and portable authority
```

Product-first exploration adds a bounded orchestration path from the same product
request to complete scaffold options, comparative groups and explicit preparation
sets. It reuses local discovery, candidate continuation, verified portrait facts
and set admission. Packet capture/publication is shared infrastructure; family
reference policy and options grouping remain separate. See [ADR 0042](docs/architecture/decisions/0042-complete-scaffold-options.md).
Product-driven preparation branching and exact stage grouping are owned by
`design.construction.discovery`; [ADR 0043](docs/architecture/decisions/0043-product-driven-scaffold-discovery.md)
records its permission, identity and replay boundaries.
Within discovery, `branches.py` compiles permitted strict requests without file
I/O; `prepare.py` owns source loading and the preview packet. The
[construction module map](docs/dev/construction-map.md) locates the remaining
workflow responsibilities and focused test seams.

The source owns requests, exact materials, constraints, and bounds. The design
bundle owns design identity and encoding. The construction bundle embeds the
unchanged design authority needed for replay and owns only the complete-route
result and its inventory.

The local-to-design bridge admits only explicit selections from replay-verified
receipts. Its exact-junction design schema contains molecular components, not
search result ids, bounds, relaxation history, enzyme programs, or construction
chronology. PCR-bearing endpoints derive their basal component from local
evidence. Direct hairpin endpoints require explicit exact basal arms; the bridge
never invents that component. The bounded request executor composes existing
authorities under an explicit sole-witness policy and returns either a
preparation or a scoped handoff. Its summary is not a molecular authority.

Final-payload coordinates are shared authority. Source coordinates and source
segmentation belong to the selected route family. The current linear-source
family may use one contiguous source interval without making that layout a
global payload invariant.

## Product answers

Recorded edition capture lives in `design/construction/editions`. Ordinary
capture retains exact producer admission. The explicit `freeze_design_choices`
source contract admits a read-only checkpoint under its recorded producer,
reuses one reader across complete-witness retrieval, and returns only an immutable
edition. Molecular verification stays with the existing survey retrieval owner.
The original generator and current exporter have separate provenance; this
boundary grants no permission to continue or replay a foreign-producer search.

`DesignChoices.explain()` describes an admitted query without selecting a molecule
or starting search. Shared projection code in `variants/explanation.py` owns
product/preparation counts, scoped outcomes and applicable next actions. Native
scaffold queries use the same projection while retaining their full preservation
and neighborhood controls. CLI and browser adapters render these facts.

Parameter applicability lives beside the parameter definitions. It depends on the
supported route, including intermediate measurements, rather than on whether a
witness happens to contain a value. The optional-intent boundary rejects
inapplicable predicates; the lower-level query schemas remain unchanged.

## Layer direction

```text
models
  <- kernel and catalogs and deterministic encoders
  <- design use cases
  <- public API
  <- CLI command adapters and future agent adapters
```

- `models` contains strict data contracts and imports no higher HOP layer.
  Model-adjacent semantic replay modules may contain pure, deterministic
  construction validation when a serialized contract must reject molecular
  drift without importing a higher layer. They are internal authorities, not
  public use cases, and both producers and model validators call the same
  replay function where construction and validation share a derivation.
- `models/physical.py` is the model-safe authority for literal pair kinds,
  opposite-strand selection, and oriented nick/release geometry. Validators
  and kernels consume those pure derivations instead of restating them. A
  self-reverse-complement motif is one textual motif-presence match but still
  yields both oriented physical processing events.
- `kernel` owns reusable pure molecular primitives and content identity.
- `catalog` contains only generic, versioned public demonstration data.
- `export` encodes and verifies artifacts without owning scientific policy;
  renderers consume typed view state and do not recompute molecular state.
- `design` checks, resolves, and compiles through the lower layers.
  `compile.py` orchestrates use cases; `assembly.py` owns final plan and bundle
  construction; `bundle.py` replays spec-to-bundle semantics over the
  lower-level integrity reader; `result.py` owns the write-capable compilation
  result.
- A method bundle records how one named method request resolves into molecular
  states and products. It retains its own identity, separate from design
  identity; callers check its products against a destination.
- `api` is the package-root design-language operation facade. Thin top-level
  `spaces`, `construction`, `discovery`, `methods`, and `views` facades expose
  the scientist-facing workflow and specialized competency surfaces without
  adding derivation logic. `spaces` authors a bounded sequence space and
  returns existing member authorities rather than redefining their anatomy.
  `construction` accepts strict files plus a separately verified design bundle
  and returns opaque receipts rather than exporting the construction ontology.
- `cli` registers command families. Modules under `commands` adapt user input
  to public facades and contain no molecular derivations or authority models.

Construction discovery reuses the specialist discovery, molecular-state,
method, and view layers. Its shared local-neighborhood contract must not enter
the seven-name `hop_design.spaces` facade or inflate the package root. Foldback
and basal targets share result, completeness, relaxation, and identity
semantics while retaining family-specific geometry. Source partitioning is a
sibling authority rather than a basal-neighborhood subtype. Its public receipt
is exposed only through `hop_design.construction`.

Within each local family, `traversal.py` yields exact work units in canonical
geometry, strand, payload, and enzyme-program order. Traversal does not generate
sequence candidates or assert feasibility. The family kernel solves those
candidates; `discovery.py` owns evaluation limits, witness stopping, coverage,
and final result assembly. These internal work units are not serialized
authorities or additional public request types.

The foldback kernel solves finite independent arm/cap base domains and a
correlated source expression before materializing exact sequence solutions.
Both source orientations use that same domain; reverse complementation changes
the source expression and binding coordinates while preserving final-product
variables. The source tail removed by terminus cleavage retains its free base
variables instead of being fixed to the first permitted bases. `cardinality`
counts retained arm/cap assignments; `precursor_cardinality` counts joint retained
and variable-tail assignments before reaction-stage admission. Concrete
enumeration and partitions address the joint assignments. Neither count is an
admitted construction count.

The basal kernel likewise solves source and adapter placement domains before
concrete sequence enumeration. `kernel/construction/basal/domains.py` owns the
shared recognition masks, source and adapter coordinates, pairing permissions,
and exact materialization. Source context outside the retained local window
remains in this domain. Canonical-pair source masks incorporate adapter-side
base restrictions and future-end requirements; they describe placement choices,
not molecular admission. Concrete enumeration retains its source/adapter/context
order and sequence-partition ordinals, including noncanonical pair outcomes.

`models/construction/sequence_sets.py` owns strict, finite exact DNA sets over
independent bases. Reduced A/C/G/T decisions have canonical reachable postorder,
verified cardinality, exact membership, and lexicographic member recovery.
`kernel/construction/sequence_sets.py` constructs their unions, intersections,
and differences within explicit decision and operation budgets. Window projection
preserves exact substrings while existentially removing surrounding positions;
correlations within the retained window remain intact. Molecular admission must
precede projection when discarded context can affect reaction-site checks. The same set
serializes identically regardless of insertion order or redundant witnesses.
These sets describe nucleotide membership only. Construction authority requires
the molecular admission and complete request coverage layers below.

`kernel/construction/foldback/admission.py` applies ordered molecular admission
to one solved foldback domain and retains its exact joint source assignments.
Projection onto the arm/cap variables counts each retained word once if at least
one source completion passes. The joint relation remains available for later
primer, processing and complete-route checks; projection does not select a witness.
Concrete replay supplies the stage topology; shared source-span mappings retain
both duplex products after terminus cleavage. Shared recognition orientations,
cut availability, intended-binding matching, and operation-policy assessment
govern both concrete and compact evaluation. Recognition predicates preserve
repeated and complemented variable correlations. One representative assignment
provides topology and sequence-independent policy checks; its sequence-dependent
admission result does not classify other members. These internal admitted sets
do not establish coverage of a query roster or provide a portable construction
receipt. Selected members still materialize through ordinary molecular replay.

`models/construction/foldback_space.py` binds exact case populations and individual
program support to a finite request. `design/construction/foldback_space.py`
exhausts the geometry, exact payload, strand, and provisioned program roster;
its verifier recomputes every set and requires canonical result equality.
The file-oriented `FoldbackSequenceSpace` receipt is exposed only through
`hop_design.construction`. It preserves compact sets, exact raw denominators,
and program support without multiplying physical configurations by witnesses.
Selected members use the same full molecular realization authority as concrete
local discovery. The receipt covers local admission; complete material resolution
and route composition require their own checks.

Canonical basal populations use `models/construction/basal_space.py` and the
parallel `BasalSequenceSpace` public receipt. Shared basal domains retain the
full source through reaction admission; `basal_space_admission.py` applies the
ordinary nick program and shared reaction-site rules before window projection.
Each case unions local words across exact ends and enzyme support while retaining
admitted source sets for molecular recovery. Loading repeats complete discovery;
selected words recover a supporting source and pass ordinary basal realization.
Noncanonical pair permissions raise rather than being silently narrowed.
Computational limits belong to the shared sequence-set models; study budgets,
pooling across requests, plots, and selection policies remain caller-owned.

`scripts/check_architecture.py` enforces absolute and relative imports, maps the
root `api.py` and `cli.py` modules and the `commands` adapter layer explicitly,
and fails on unknown first-party layers. The root facade and serialization module are narrow documented
exceptions. The data-only `_facade.py` manifest keeps the package root readable;
the same architecture check requires every public root re-export and manifest
entry to agree. Add an abstraction only when a second real implementation or
consumer makes the seam necessary.

## Current product slices

Start with [complete-design discovery](docs/guides/discover-designs.md) around a
supplied stem. [Substrate spaces](docs/guides/substrate-spaces.md) provide a
separate workflow for compiling sequence anatomy. These journeys compose the
following surfaces.

0. **Construction interface.** Resolve optional molecular intent, discover
   complete preparations, inspect and select a result, then retrieve exact
   materials through the same CLI/API objects.

1. **Design language.** Exact and symbolic payloads, foldback and basal
   junctions, optional paired stem context, deterministic design derivation,
   and the feature-partitioned `HairpinEncodingInsert`.
2. **Discovery language.** Bounded placement, geometry, precursor, and junction
   queries. Results expose exact candidate identity, `canonical_ordinal`, and
   truthful completion evidence without selecting a candidate.
3. **Method language.** Exact materials and an ordered molecular-state history
   for one named method. The linear-source compiler derives all nicks,
   fragments, selections, pairings, ligation bonds, PCR products, restriction
   products, and cohesive ends.
4. **Provenance and verification.** Distinct design, construction, and method
   bundle claims; strict schema replay; byte verification; embedded design
   authority for construction replay; and an explicit design-method encoding-
   digest handoff.

Design derivation is non-temporal. Construction routes and named method plans
own their respective molecular chronology. Check method availability and request
feasibility separately from design compilation, then check the resulting product
against the caller's destination.

Discovery operations answer separate competency questions rather than one
global optimization problem. Canonical order is reproducible interoperability
metadata, not an objective score. Catalog warnings, empirical enzyme behavior,
procurement, application preference, and candidate selection remain caller
policy.

All exact physical pair kinds are deterministic functions of literal bases.
Watson-Crick complements, G:T wobbles, and hard mismatches do not change kind
when a policy accepts or rejects them. Every sequence-bearing method state is
stored 5′→3′ and preserves explicit coordinate lineage.

Construction-route chronology is an ordered list of reaction stages. All
concurrent operations in one stage resolve against the same pre-stage state;
site validity depends on molecular availability in that stage. Compactness is
an endpoint projection over retained non-payload sequence, not total source
length. Geometry and final-product grouping remain reversible projections over
exact realization authorities.

For a PCR-bearing linear-source route, the retained source prefix may extend
beyond the local basal pairing span. Its source-return arm is the reverse
complement of that complete prefix. Basal nicking removes the portion paired
upstream of the nick; any intervening bases toward the payload retain their
original complementary partners. The ligation adapter is a separate exact
material paired to the exposed source under its local and distal constraints.
The verified design may therefore occupy a nonzero subspan of
the PCR product, with outer source periphery and primer handles remaining
explicit.

HOP may emit neutral tidy data and diagram-ready molecular projections.
Client studies own scientific runs, observations, interpretation, and asset
promotion. Manuscript systems own accepted evidence snapshots, claims, and
figure composition. Neither consumer may drive HOP's molecular semantics.

The [documentation index](docs/index.md) mirrors these sibling surfaces.
Historical architecture choices and their amendments remain in the
[decision index](docs/architecture/decisions/README.md).
