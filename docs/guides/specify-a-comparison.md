# Specify and retrieve a molecular comparison

Describe the molecular differences you need, which properties must agree, and
which preparation changes you permit. HOP discovers complete preparations,
assesses compatible sets and retains examined failures. Choose a displayed set
explicitly to retrieve its named preparations and consolidated oligos.

A **product** is the exact molecule at the stage you compare. A **preparation**
specifies its input oligos and ordered processing steps. Several preparations
can make the same product, and different hairpin intermediates can lead to the
same released insert. Choose the comparison stage before deciding which members
must agree or differ.

Start with the [runnable example](../../examples/scaffold-comparison/README.md).
It uses public synthetic inputs and produces substrate, preparation-alternative and grouped comparison sheets.

## Write a brief

`hop.comparison-brief/v1` embeds an ordinary
[scaffold discovery request](discover-product-scaffolds.md). The discovery request
specifies the desired endpoint, allowed geometry, available methods, material policies,
and branch and continuation budgets. The brief adds:

| Field | Meaning |
| --- | --- |
| `purpose` | `distinct_substrates` requires a different exact molecule per member; `preparation_alternatives` requires the same exact molecule and different preparations. |
| `required_members` | Named obligations with `dimensions` and/or `release_enzyme_id`. Each member must have a matching complete option. An empty list imposes no membership obligations. |
| `shared_properties` | Hairpin properties required to agree across the set. |
| `preserve_material_roles` | External material roles whose exact sequence and terminal chemistry must agree across members. |
| `max_group_evaluations` | Maximum complete assignments examined, separate from molecular discovery bounds. |
| `max_sets` | Maximum compatible sets returned (default 64). No returned set is automatically selected. |

Choose `discovery.comparison_stage` deliberately: `hairpin` or `endpoint`.
Four different hairpins can become two released inserts. Conversely, two methods
can produce the same exact insert through different hairpin intermediates.
Shared properties refer to the hairpin even when exact identity is assessed at
the later endpoint.

Allowed dimensions include `loop_nt`, `loop_side_paired_bp`,
`open_side_paired_positions`, `five_prime_unpaired_nt` and
`three_prime_unpaired_nt`. The terminal dimensions describe the hairpin, even when
the requested final product is a released insert. High-level terminal translation
currently supports the [adapter-ligated endpoint](discover-product-scaffolds.md).
The open-side count is a count of recorded paired
positions, not necessarily Watson–Crick base pairs. An allowed interval such as
3–8 nt permits discovery within that interval. To require every size, list six
named members. Missing geometry permissions are reported; HOP does not silently
expand them or remove an obligation.

```json
{
  "name": "loop3-open18",
  "dimensions": {"loop_nt": 3, "open_side_paired_positions": 18}
}
```

## Preview, execute, select

```bash
# Preview the brief, execute it, then select from its recorded comparison.
hop-design construction preview-comparison brief.json --out preview
hop-design construction execute-comparison brief.json --out comparison
hop-design construction select-comparison comparison \
  --set set-0001 --baseline loop3 --out selected
```

The preview names effective values, excluded intervals, inherited declarations
and explicit edits for conflicts. Direct-hairpin arms remain authored fixed
sequences; requesting a new dimension does not generate replacement arms.
Conflicting declarations return an unexecuted outcome with all members retained.

The report distinguishes a missing member in the evaluated pool from a failed
examined preparation and from unexamined coverage. Even complete examination of
this pool does not establish global impossibility. Assignment enumeration uses
canonical member names and option labels, without a privileged first reference.
Set labels indicate order, not scientific rank.

Read `comparison/report.pdf`, `report.md` and `summary.json`. The substrate sheet
shows whole hairpins and countable closing-region details. The preparation sheet
shows a common product and the different upstream molecules and materials.
Pairing diagrams show the specified architecture.

Selection replays the underlying molecular records and recomputes the
assessment before admitting a displayed set. `selected/set.json` is ordinary
portable membership. `selected/oligos.csv` and `oligo-uses.csv` retain exact
chemical specifications and all member roles. `selected/comparison/report.pdf`
shows the selected comparison. Move the entire selected directory together.
The baseline sets the reference for pairwise presentation.

To reuse an existing discovery with unchanged molecular permissions and bounds:

```bash
# Assess the requested comparison against the saved discovery.
hop-design construction assess-comparison brief.json discovery --out comparison
```

Only `comparison_stage` may differ from the saved discovery's permissions and
bounds. A v3 brief can assess its original, untargeted discovery or its exact
compiled required-first request. The assessment records which search was actually
performed; assessing old results does not create targeted-search evidence. A
prior-material binding requires discovery under the compiled fixed policies.

## Cross scaffold groups with preparation methods

Use `hop.comparison-brief/v2` with `purpose: grouped_substrates`. Each group names
required member slots whose exact molecules must agree at the comparison stage.
`between_groups: distinct` requires different products between groups. The groups
must partition all required members exactly once. Global shared hairpin properties
and preserved material roles continue to apply across the entire set.

```json
"groups": [
  {"name": "loop3", "members": ["loop3-bsai", "loop3-bsmbi"],
   "product_relationship": "identical"},
  {"name": "loop4", "members": ["loop4-bsai", "loop4-bsmbi"],
   "product_relationship": "identical"}
],
"between_groups": "distinct"
```

The complete [grouped example](../../examples/scaffold-comparison/grouped.json)
requires two loop sizes, each through BsaI and BsmBI. Its four hairpins yield two
released products. Changing the comparison stage to `hairpin` reassesses equality;
it does not transfer the endpoint conclusion to the intermediates.

```bash
# Execute the comparison across the declared scaffold and method alternatives.
hop-design construction execute-comparison \
  examples/scaffold-comparison/grouped.json --out comparison
hop-design construction select-comparison comparison \
  --set set-0001 --baseline loop3-bsai --out selected
```

The first sheet arranges scaffold groups as rows and preparation methods as
columns. Exact products align beside their preparations. A missing or incompatible
set retains its requested cells; a sole available option is not an assigned set.
More than two methods or groups continue on additional pages.

## Keep a previously chosen product

Add `product_reference` to any v2 group. For example, relative to a new brief:

```json
"product_reference": {
  "bundle_path": "selected/members/loop3-bsai/construction",
  "selection_path": "selected/members/loop3-bsai/portrait/selection.json",
  "stage": "endpoint"
}
```

Use one group to redesign preparations of one product, or a separate reference
for every scaffold group. The reference stage must match `comparison_stage`.
The construction and selection are verified and copied into the comparison
packet; an arbitrary molecular hash is not accepted. Change permitted methods
or material policies explicitly in `discovery`. Newly discovered products must
match the reference, even when they already agree with one another.

A selected packet retains these verified bundles and its portable brief under
`comparison/`. Reference paths in `comparison/request.json` are relative to that
file; the embedded request in `comparison-selection.json` uses paths relative
to the selected packet root. Move the entire directory together. Materials and
processing may change while product identity remains fixed.

## Specify loop composition as well as size

The [sequence example](../../examples/scaffold-comparison/loop-sequences.json)
compares `AAA` and `ATA` loops at the same length, through both methods.
`discovery.product.foldback.geometry.loop_sequences` is a finite permitted set
of exact words. Each v2 member's optional `loop_sequence` requires a particular
word. A permitted word is not an obligation until named in a required member.

Words use the continuous hairpin strand's 5′→3′ order, from its primary arm into
the loop toward its return arm. They must be exact DNA and agree with any
`loop_nt` declaration. Geometry must permit their lengths. Preview identifies
required words outside inherited domains instead of changing either declaration.

Loop words constrain the molecular placement domain before sequence enumeration,
then are checked against complete constructed hairpins. A stopped search retains
unexamined coverage. Member selectors operate within the inherited sequence
permissions and search bounds.

A specified loop can introduce a recognition site in a later copied duplex.
Read the reported enzyme, processing stage and recognition interval before
editing a method permission. A complete alternative is one examined way forward;
it does not prove that the original word is globally impossible under that enzyme.

## Specify stage controls and search required members first

`hop.comparison-brief/v3` accepts all three purposes above, and keeps the legacy
`shared_properties` checks on the hairpin. Use explicit `stage_controls` when a
requirement concerns the later product or only one named group:

```json
"stage_controls": [
  {"property": "non_loop_sequences", "stage": "endpoint", "scope": "set"},
  {"property": "non_loop_pairing", "stage": "endpoint", "scope": "set"},
  {"property": "terminal_chemistry", "stage": "hairpin", "scope": "group", "group": "aaa"}
]
```

Sequences and pairing outside the loop-derived region are separate requirements.
Released-product regions are located through recorded nucleotide ancestry; copies
of loop bases remain loop-derived. These checks do not infer correspondence from
similar strings. Missing or ambiguous ancestry, or fewer than two members, is
unassessed and cannot satisfy a required equality control. Portable selection
retains the named stage and explicit membership in `construction-set/v2`.

Execution of a v3 brief compiles its member selectors into
`hop.scaffold-discovery/v3` required targets. The original permitted domains remain
in `discovery/intent/request.json`; individual tasks narrow them explicitly.
Targets are canonicalized by their molecular selectors, independently of member
names. Identical tasks are merged, and a later overlapping target can reuse a
complete option. New member names do not allocate a new budget.

`max_branches` is the **shared cap on evaluated tasks**, including targeted and
optional work. Each task retains the declared local search limits and
`max_continuations_per_branch`. Canonical required tasks precede optional original
branches. This is a bounded ordering policy, not a promise to satisfy every member.
Preview exposes the plan; `search_schedule` records evaluated, reused and
unexamined tasks. Local quota stops, unexamined continuations and bounded set
assignments remain distinct. Earlier brief versions retain their original search
order and admission meanings.

## Reuse specific materials from a previous preparation

In v3, bind roles to one verified prior preparation for the whole requested set:

```json
"reuse_prior_materials": {
  "reference": {
    "bundle_path": "selected/members/aaa-bsai/construction",
    "selection_path": "selected/members/aaa-bsai/portrait/selection.json"
  },
  "roles": ["source_ssdna"]
}
```

HOP captures the reference and compiles the named materials into existing `fixed`
policies, including sequence and terminal chemistry. Primer reuse also retains
its declared annealing segment. Existing fixed specifications, chemistry, primer
bounds and adapter requirements are checked for conflicts. Complete construction
still determines compatibility with permitted methods; using the same source can
remove a method that previously produced the same insert from a different source.

Three requests have different meanings: `product_reference` preserves a previous
molecule; `preserve_material_roles` requires agreement among new members;
`reuse_prior_materials` requires equality to the specified old materials. The
comparison reports changes relative to that actual prior preparation. Selection
embeds the reference and rechecks the required roles when `set.json` is retrieved
after relocation.

## Obtain a hairpin itself

Use `product.endpoint: adapter_ligated_hairpin` to end the supported basal route
after adapter ligation. It requires basal geometry and
`product.materialization.adapter_ligation`, using the existing adapter policy
(`derive`, `constrain` or `fixed`). Omit `endpoint_auxiliaries`, release and
requested released ends. Source preparation still specifies its own primers.

This endpoint records the exact continuous strand, contacts, two covalent joins,
terminal chemistry and unresolved recovery conditions. It does not require
endpoint copying primers or a later release reaction. Merely comparing the
hairpin stage of an insert request continues to request an insert; it does not
produce an independent hairpin handoff. Neither endpoint demonstrates a hairpin
with exposed assembly sticky ends.

Preparation reports retain unresolved conditions beside the exact materials and
processing records.
