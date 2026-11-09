# Edit the molecule, then choose its preparation

Run these repository examples from a [source checkout](install.md#work-from-source).
The commands use its locked environment throughout.

Start from an ordinary [scaffold request](discover-product-scaffolds.md). Use the
[public example](../../examples/molecular-editing/README.md) to compare GAAA and
TTTC loops, inspect every exact base in its folded architecture, and retrieve
explicit preparations.

For exploration among complete supported options, use the
[conditional variant view](explore-conditional-variants.md). It shows one molecule,
keeps a stable comparison reference and exposes supported neighborhood alternatives
without nucleotide-entry fields. Browsing, evaluating new requests and relaxing
requirements remain separate actions.

Exact authored requests remain available through the operations below. The legacy
`edit-view REQUEST --out NEW` authoring mode also remains available; it is separate
from `edit-view RESULT --evaluated --out NEW`, which browses existing verified results.

Purple positions mark substitutions and green positions mark additions. Ambiguous
alignments retain exact regional words without inventing unique positional
correspondence. Pairing relationships and paired-base identities are distinct.

## Author exact requests through CLI/API

```bash
# Prepare the named loop alternatives as explicit molecular edits.
uv run --locked hop-design construction prepare-edit examples/molecular-editing/request.json --loop GAAA --loop TTTC --out /tmp/hop-edit
uv run --locked hop-design construction evaluate-edit /tmp/hop-edit/edit.json --out /tmp/hop-alternatives
```

The report names complete options. Pass the recorded edit digest, explicit
`--member NAME=OPTION` bindings and `--baseline NAME` to `select-edit` with a new
`--out` directory. Use `--shared non_loop_sequences` when it is required, rather
than assuming shared dimensions establish shared sequences. The
[runnable API recipe](../../examples/molecular-editing/run.py) performs this
journey with an explicit unique match for each requested loop.

An edit captures the original validated request and its digest, stage and region.
Unedited geometry, material policies, forbidden/reserved enzymes and search
quotas remain active. Selection replays the saved constructions and reconstructs
their sequence views; rehashing altered annotations cannot make them authoritative.

## Compare conditional end placements

In the editor, expand **Released ends & permitted methods** and enable the edit.
Enter paired gaps as `LEFT:RIGHT` values in base pairs. End words are always read
5-prime to 3-prime on their own protruding strand; orientation and polarity remain
as authored. These are ends of the **released duplex insert**, not exposed ends
on the hairpin intermediate.

```bash
# Compare end placements under the stated basal-nick permissions.
uv run --locked hop-design construction prepare-edit examples/molecular-editing/request.json --placement 6:6 --basal-nick example:enzyme/nb.bsrdi@1 --basal-nick example:enzyme/nb.btsi@1 --out /tmp/hop-method-edit
```

Repeat `--placement` for finite comparisons, such as `0:0`, `3:3` and `6:6`.
Use `--left-end`, `--right-end` and repeated `--release` options for explicit
interface/method changes. The inherited evaluation quota still applies; increase
it in the base request when you intend to examine more combinations. Never infer
an impossibility from an unexamined branch. The summary records all requested
pairs and nondominated complete pairs **examined**; a unique closest pair is
reported only if one dominates the other observed pairs. There is no global
minimum claim. Detailed failures retain their local or complete-route scope.

Changing a nickase can change the substrate even at identical dimensions and end
words. The example's Nb.BsrDI/Nb.BtsI comparison retains a paired substitution in
the released insert. Inspect the endpoint sequence differences as well as the
hairpin and changed source/adapter roles. Unchanged primer sequences do not make
the resulting substrate identical.

## Expand a small degenerate stem into an exact family

```bash
# Preview a finite exact expansion of the degenerate stem.
uv run --locked hop-design construction preview-sequence-family examples/molecular-editing/sequence-family.json --out /tmp/hop-sequence-preview
uv run --locked hop-design construction evaluate-sequence-family examples/molecular-editing/sequence-family.json --out /tmp/hop-sequence-family
```

The family request holds one exact base preparation request and a same-length
IUPAC `stem_domain`. `max_members` (at most 64) and `max_total_branches` bound work
before expansion. Every expansion is required. Each paired arm is derived, and
every exact request retains the original material policies. The one-N example
requires four exact stems, shared non-stem sequence and specified unchanged
adapter/primer roles. Source oligos may differ because their stem differs.

`select-sequence-family` requires an explicit `--member MEMBER=OPTION` for every
required member, a `--baseline`, and a new `--out`. Missing complete members stay
visible and cannot silently disappear from the selected family. `non_stem_sequences`
checks both flanks and loop in the hairpin; shared material roles also check exact
sequence and chemistry through the ordinary portable-set material contract.

This is a set of separate exact preparations. It does not establish a pooled
degenerate synthesis, pooled reaction, equal recovery, biological effects, RNA
conformation, or destination compatibility. The intended pairing architecture
and complete modeled preparation are the demonstrated endpoints.
