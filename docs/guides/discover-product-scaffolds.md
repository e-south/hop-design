# Specify the scaffold, then choose its preparation

Run these repository examples from a [source checkout](install.md#work-from-source).
The commands use its locked environment throughout.

Start with the [runnable public example](../../examples/scaffold-discovery/README.md).
For a comprehensive four-base end domain with incremental checkpoints, use
[interface surveys](survey-interfaces.md). Its target catalogue is independent of
batch size; the small-roster workflow below retains its original limits.
A `hop.scaffold-discovery/v1` request embeds one ordinary
[product request](design-a-construction.md), desired scaffold ranges, permissions
for preparation changes, the comparison stage and two explicit search budgets.
The endpoint says what you intend to obtain. The comparison stage says which
molecules you want to distinguish, including hairpin intermediates of an insert.

For a folded primary-sequence editor, conditional end distances and exact-member
expansion of a small degenerate stem, use [molecular edits](edit-folded-sequences.md).

| Declaration | Meaning |
| --- | --- |
| `product` | Complete strict `hop.product-request/v1`, including stem, methods, material policies and local bounds |
| `scaffold` | Optional inclusive `loop_nt`, `loop_side_paired_bp`, `open_side_paired_positions` ranges, each with `minimum` and `maximum` |
| `preparation_changes.adapter_redesign` | `preserve` by default, or explicit `allow` to propose adapter annealing settings for requested open-side dimensions |
| `preparation_changes.release_enzyme_ids` | Optional 1–16 distinct characterized identities; each becomes a separate strict release branch |
| `comparison_stage` | Required `hairpin` or `endpoint` |
| `max_branches` | Examine 1–64 branches from the deterministic expansion, which cannot exceed 256 |
| `max_continuations_per_branch` | Examine 1–64 recorded local combinations in each branch |

`preview-scaffolds REQUEST --out NEW` performs no molecular search. Read its
`report.md` for effective dimensions, separate source and endpoint material
policies, explicit edits, conflicts and limits. `summary.json` retains both the
original scaffold request and inherited constraints. Their intersection remains
hard; loop and closing-region requests must intersect the base geometry domains.
A fixed adapter conflicts with redesign permission. HOP never silently replaces
it with a derived material or rewrites the input file.

With adapter redesign allowed, each permitted nick-to-stem offset contributes to
the candidate annealing setting. Proximal pairing can impose a larger achieved
span. Only complete construction establishes whether a candidate actually satisfies
the requested scaffold. Redesign does not guarantee a witness. Direct hairpins
have no downstream adapter-redesign or release step; preserve those settings and
use their existing basal-component declaration.

`discover-scaffolds REQUEST --out NEW` evaluates permitted branches. All other
hard constraints and material policies remain active. Exact failures, local
coverage and unevaluated combinations stay in the packet. Release alternatives
also set the matching basal end-generation role, without changing nickase roles.
Unknown, forbidden or reserved methods conflict before execution. Catalog
membership does not establish laboratory availability.

Open `report.pdf` for whole molecules, stage-specific products and changed
material roles. `report.md` links every complete option to its preparation and
branch request. Opening negative pages distinguish dimension mismatch, release
incompatibility and actionable-site conflict. A site rejection without recorded
coordinates is not a localized diagnosis. Successful branches are explicit
alternatives, not proven necessary or minimal repairs.

## Explore declared receiving-end pairs

Use `hop.scaffold-discovery/v6` with `receiving_end_pairs` for 1–64 explicit
`ProductEnds` records. Each record contains both `left` and `right`, each with
`cohesive_end_sequence`, `overhang_end`, site `orientation`, and
`payload_end_offset_bp`. The entire pair is one permission. Supplying two pairs
never authorizes crossed words or placements. Omit the roster to preserve the
single `product.ends` requirement. Do not also supply `end_placements`; put each
placement into its corresponding pair.

The public recipe declares AGTC/AGTC, CATT/AGTC and AGTC/AGCC at the original
6/6-bp placements, retaining polarity, site orientation and all other controls:

```bash
# Explore the declared receiving ends in the repository example.
uv run --locked python examples/scaffold-discovery/receiving_ends.py --out /tmp/hop-end-pairs.json
uv run --locked hop-design construction preview-scaffolds /tmp/hop-end-pairs.json --out /tmp/hop-end-preview
uv run --locked hop-design construction discover-scaffolds /tmp/hop-end-pairs.json --out /tmp/hop-end-options
uv run --locked hop-design construction edit-view /tmp/hop-end-options --evaluated --out /tmp/hop-end-review
```

The recipe writes a new request without editing its seed. Under these specific
permissions, AGTC/AGTC supplies a complete preparation. The other two pairs have
exhausted local basal domains and no complete preparation; this does not prove
global impossibility or a unique repair. CATT/AGCC is not declared. Selecting
those marginal words returns no compatible preparation, and further evaluation
rejects the empty joint-domain intersection instead of creating another pair.

Every evaluated branch retains its exact product request and changes. Catalog,
material-reuse and search bounds remain authoritative. Method alternatives can
cross the declared pair roster only through explicit existing method permissions;
the total expansion remains bounded at 256 branches, with at most 64 evaluated.
Use the ordinary conditional query and explicit preparation retrieval operations
on this result. The atlas remains bound to one complete preparation, including
when other requested pairs have no witness.

## Request the terminal form of a hairpin

Use `hop.scaffold-discovery/v2` for terminal requirements. The
[terminal example](../../examples/scaffold-discovery/terminal-form.json) requests
an actual `adapter_ligated_hairpin` endpoint with 6 unpaired 5-prime nucleotides
and 14 unpaired 3-prime nucleotides. These are recorded terminal tracts; terminal
chemistry and assembly compatibility are separate properties.

```bash
# Preview the requested hairpin terminal form before discovery.
uv run --locked hop-design construction preview-scaffolds examples/scaffold-discovery/terminal-form.json --out /tmp/terminal-preview
uv run --locked hop-design construction discover-scaffolds examples/scaffold-discovery/terminal-form.json --out /tmp/terminal-options
```

Set `scaffold.five_prime_unpaired_nt` and `scaffold.three_prime_unpaired_nt` using
inclusive `minimum`/`maximum` ranges. With `adapter_redesign: allow`, HOP proposes
pairing extents against the declared source and can shorten the existing adapter
tail by retaining its 5-prime prefix, including removing the entire tail. The
preview records that sequence policy and each exact adapter edit. It never
creates new tail bases from a requested length.

To permit different terminal sequences, supply the finite exact list
`preparation_changes.three_prime_tail_sequences`; an empty string permits no
tail. That list replaces the prefix-trimming choices and is intersected with the
required length. It requires explicit redesign permission. Fixed adapters remain
fixed; source and primer policies remain active. A fixed source can supply several
candidate stem occurrences, each requiring complete source-embedding verification.

In this example, high-level terminal requests 6/14, 6/8, 6/0 and 0/0 complete with
18, 18, 18 and 24 open-side paired positions respectively. Only the adapter changes.
The fully paired terminal example therefore cannot simultaneously retain an exact
18-position open-side requirement. Read preview conflicts before execution.

`preserve` retains the preparation settings and checks the achieved terminal
counts. Redesign translation currently supports the adapter-ligated hairpin
endpoint. Other product stages can retain their existing preparation controls;
their achieved hairpin dimensions remain independently checkable. Version 1
discovery rejects terminal declarations instead of adopting version 2 behavior.

The report shows whole hairpins with countable terminal enlargements, the resulting
pairing extent and material differences. Use explicit option labels with
`select-scaffolds`, including terminal dimensions in `--compare` or
`--shared` when applicable. The saved `set.json` remains portable;
retrieval regenerates its terminal comparison when those dimensions are declared.

## Interpret the comparison

`summary.json` groups exact products under `stage_groups.hairpin` and
`stage_groups.endpoint`; `molecules` selects the requested comparison stage.
Grouping uses oriented sequences, pairing contacts, topology, terminal chemistry
and interfaces. It ignores manufacturing origins and precursor cut coordinates.
It does not infer equivalence under strand permutations or predict physical
conformation, biological behavior or ligation efficiency. Preparation and
construction identities remain attached to every option.

The report may show two distinct hairpins leading to the same released insert.
That is a useful substrate contrast at the hairpin stage and an alternative
preparation comparison at the insert stage. Only the released molecule bears its
modeled cohesive ends. Equal dimensions alone never establish equality.

## Select and retrieve

Choose explicit labels from your saved packet and bind meaningful names:

```bash
# Retrieve the explicitly chosen scaffold preparations.
uv run --locked hop-design construction select-scaffolds /tmp/scaffold-options \
  --member loop3=branch-0001-option-0001-01 --baseline loop3 \
  --out /tmp/scaffold-selected
```

The label above belongs to the public example; inspect your own options first.
Repeat `--member NAME=LABEL` for a family. `--shared` requires achieved hairpin
properties to agree; `--compare` declares the intended contrasts. These existing
set controls concern the hairpin architecture. Exact endpoint grouping remains
separate in `stage-comparison.json`; it must not be inferred from shared dimensions.
There is no automatic winning design or joint optimization across an unexamined pool.

The selected set includes user names in drawings, `set.json`, exact preparation
paths and `oligo-uses.csv`, alongside stable identities. After moving the whole
folder, `select_construction_set("moved/set.json")` verifies and retrieves the
same members. The set's molecular contents remain authoritative; added stage
comparisons are projections from those verified records.

Preparation reports retain terminal chemistry, material specifications and
unresolved reaction, recovery and destination conditions. Modeled completion
is not laboratory validation. All output locations must be new and cannot
overlap captured inputs. The [Python facade](../reference/python-api.md) provides
`prepare_scaffold_discovery`, `discover_scaffolds` and `select_scaffold_options`
with the same behavior.
