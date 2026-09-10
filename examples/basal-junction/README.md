---
doc_id: hop-basal-junction-example
title: Find a basal junction beside a fixed substrate
intent: Run a characterized-enzyme search while preserving a public duplex payload.
audience:
  - new construction users
owner: HOP Design maintainers
status: active
last_verified: 2026-09-08
doc_type: tutorial
---

# Find a basal junction beside a fixed substrate

Can a nickase site and a later Type IIS site share the sequence beside an
unchanged substrate? This example uses a 34-bp loxP payload, Nt.BsmAI, and BbsI.
The payload is a public reference, not a special HOP target or an assay result.

From the repository root:

```bash
uv sync --locked
uv run python examples/basal-junction/search.py --out build/basal-junction
```

The command lists the accessible cohesive-end sequences. Open
`build/basal-junction/matrix/projection.svg` to inspect all 256 end choices in
readable blocks, including infeasible cells, or use `projection.csv` beside it
for the exact matrix. The replayable result is
`build/basal-junction/result/result.json`. Choose a different output directory
for another run; existing results are not overwritten.

## Change the question

Copy [request.yaml](request.yaml) and pass its path with `--request`.

- Replace the payload and set its foldback boundary to its length.
- Pin `cohesive_end_sequence` to an exact end, or leave `NNNN` to search all
  256 four-base possibilities.
- Keep `allowed_class: match` at every proximal position, or explicitly permit
  other pair classes away from the ligation-proximal position.
- Change the allowed nick offsets and retained sequence bound independently.

Both recognition sites are required in the source duplex. Nicking and later
Type IIS cleavage are separate operations. A local solution records a 15-nt
adapter-annealing requirement; this example does not complete that association,
the primer regions, or the rest of the construction. It predicts neither
enzyme performance nor physical recovery. For complete material inputs, see
the [construction guide](../../docs/guides/compile-construction.md).

## Source definitions

The [loxP reference sequence](https://academic.oup.com/nar/article/33/13/e118/1094852)
has two 13-base arms around an eight-base spacer. The separate
[spacer-space example](../loxp-spacer.yaml) varies that spacer; this exact-payload
junction search does not establish compatibility across those variants.

[NEB's Nt.BsmAI definition](https://www.neb.com/en-us/products/r0121-ntbsmai)
is `GTCTC(1/none)`: a reference-strand cut at boundary 6 from the motif start,
with no complementary-strand cut. The
[BbsI definition](https://www.neb.com/en-us/tools-and-resources/selection-charts/alphabetized-list-of-recognition-specificities)
is `GAAGAC(2/6)`, giving motif-start boundaries 8 and 12. These are recognition
and cleavage specifications, not buffer, kinetics, or procurement recommendations.
