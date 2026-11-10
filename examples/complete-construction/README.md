---
doc_id: hop-complete-construction-example
title: Obtain a preparation and inspect an end edit
intent: Reproduce public hairpin and released-insert cases with exact materials and an expected fixed-source rejection.
audience: [new construction users, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-09-27
doc_type: tutorial
---

# Obtain a preparation and inspect an end edit

This example turns a public 34-base loxP sequence into an exact preparation:
materials and a route that HOP can reproduce from its saved inputs. It uses
characterized enzyme actions, explicitly synthetic handles, and finite searches.

From a matching source checkout or unpacked source distribution:

```bash
python examples/complete-construction/run.py --out build/public-journey
python examples/complete-construction/run.py --case hairpin --out build/hairpin-only
hop-design construction inspect build/public-journey/released/construction --ordinal 0 --end left
hop-design construction list build/public-journey/fixed-source-edit/construction --status all --group-by none
hop-design construction compare build/public-journey/released/construction build/public-journey/redesigned-source-edit/construction --left-ordinal 0 --right-ordinal 0
```

In a source checkout, prefix commands with `uv run --locked`. The script uses
only installed public HOP interfaces. Each case uses `execute_construction_request`,
also exposed by `construction execute --continuation sole-witness`. It requires the source version that ships
this example; the older released wheel may not expose these capabilities.
`summary.json` records the executing package content digest and dependency
versions, separately from the package version. `manifest.json` binds every
output and the exact recipe and input bytes. The maintainer wheel gate runs
the same example from the source distribution against a clean wheel install.

Start with an accepted case's `portrait/projection.svg` to see the whole hairpin.
Its `selection.json` and `preparation/` directory identify the exact preparation
for that drawing. `summary.json` retains all outcomes, including rejections;
`handoff/projection.svg` is the full construction trace.
CSV retains terminal chemistry and all uses of a shared
oligo; FASTA alone is insufficient for ordering. `CASE/inputs/request.json` preserves the product request, and
`CASE/inputs/construction.json` records its expanded construction input, including explicit
edits. `CASE/inputs/intent.md` separates requirements from derived and unresolved
values. Edit `product-request.json` to author another public example.

| Case | Authored intent | Expected modeled outcome |
| --- | --- | --- |
| `released` | Left AGTC; right AGTC; 5′ overhangs; 6 paired bases from each end to the payload boundary | One released insert |
| `hairpin` | Author explicit basal arms and a hairpin preparation; omit downstream basal discovery and release | One hairpin, independently runnable with `--case hairpin` |
| `fixed-source-edit` | Left GATC; right AGTC; permit noncanonical contacts only at positions 6–9; fix the original source including chemistry | Rejected selected combination |
| `redesigned-source-edit` | The same edited product and contact permissions, with source redesign permitted | One released insert |

Both end words are read 5′→3′ on their own protruding strands. In the reference
route, canonical association contacts couple the two words. The edit explicitly
permits up to four noncanonical contacts in the future end footprint; HOP does
not silently relax pairing or required ends. The redesign returns one
alternative under the declared permissions.
For this single-offset geometry, the product-request translator propagates the
left word into the declared source contact positions. The user edits the end
once. Explicit source-base restrictions are intersected, and conflicts raise;
they are never overwritten. This local propagation is conditional on the
declared strand/material frame, while complete-route verification always checks
both required ends.

The searches stop after one local witness, an accepted exact junction solution,
and continue exactly one selected combination. Coverage is limited to that
witness and selected combination.
A changed payload, enzyme or geometry needs a new search.
An absent witness produces a scoped `CASE/report.md` and summary, preserving
the exact local result. Stopped searches remain unresolved; multiple witnesses
require explicit selection. If the reference preparation is unavailable, the
two material-comparison cases are recorded as not evaluated. The independent
hairpin request still runs. Malformed input remains an error.

The released-insert example declares 14-nt primer-binding lengths. The separate
hairpin endpoint uses a 10-nt forward binding span because its retained basal
component provides only that much non-payload sequence. The two preparations
have different intermediates. The request does not prescribe removal of discarded
source fragments; the caller supplies inventory, enzyme reaction prerequisites and
receiving DNA.

## Source definitions

The payload is the same public loxP reference recorded in the
[basal-junction example](../basal-junction/README.md#source-definitions).
The synthetic upstream and adapter handles are authored for this tutorial.

- [Thermo Scientific Nt.Bpu10I](https://www.thermofisher.cn/order/catalog/product/hk/en/ER2011)
  recognizes CC↓TNAGC and nicks the reference strand after two bases.
- [NEB recognition and cleavage definitions](https://www.neb.com/en-us/tools-and-resources/selection-charts/alphabetized-list-of-recognition-specificities)
  list Nb.BsrDI as GCAATG(none/0). The request uses the reverse-complement
  reference ↓CATTGC, so HOP's reference-strand cut offset is zero. This is the
  same characterized action in explicit strand coordinates.
- The same NEB table lists BsaI-HFv2 as GGTCTC(1/5): reference/complementary
  bond offsets 7/11 from the six-base recognition site's start.

For a comparative set, use [Specify and retrieve scaffold families](../../docs/guides/compare-scaffold-families.md).

For a direct hairpin family, run `family.py --endpoint hairpin --out NEW`.
For explicit choice after a stopped family, run `continue_family.py --out NEW`.
Both examples preserve requests and outcomes and retrieve a portable report.
`family.py` starts from a concise `comparison.json` brief: product, vary, hold,
explicit geometry permissions and finite bounds. See the
[family guide](../../docs/guides/compare-scaffold-families.md).

To recover a comparative set from complete but mismatched initial preparations:

```bash
uv run --locked python examples/complete-construction/match_family.py --out build/matched-family
```

Open `before/report.pdf`, `matching/report.md` and `comparison/report.pdf` in
that order. The caller fixes the reference and explicitly chooses a compatible
alternative. Original choices, incompatible alternatives and coverage remain
recorded; `selected/report.md` retrieves the preparations.
