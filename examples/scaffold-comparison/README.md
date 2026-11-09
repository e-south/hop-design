# Molecular comparison specifications

These synthetic public inputs show five user jobs. Each includes a stem,
permitted preparation methods and bounds. Required members are separate from
those search permissions. No local construction identities are authored.

| Brief | Comparison stage and purpose | Expected bounded result |
| --- | --- | --- |
| `crossed.json` | Distinct hairpins: 3/4-nt loops crossed with 17/18 open-side positions | Four hairpins, but two released products. |
| `methods.json` | Alternative preparations of one exact released insert | BsaI and BsmBI preparations agree on product; the examined BbsI continuation fails. |
| `grouped.json` | Same released product within each loop-size group, different between groups | Four preparations, two products; methods form columns on the sheet. |
| `loop-sequences.json` | AAA and ATA loop groups, both 3 nt, each through two methods | Exact loop composition reaches complete preparations. |
| `hairpin.json` | Distinct adapter-ligated hairpin endpoints | Two independently validated hairpins with no downstream copying primers or release. |

```bash
uv run --locked python examples/scaffold-comparison/run.py \
  --case crossed --out /tmp/hop-crossed
```

Read `comparison/report.pdf` and `report.md`. Inspect the named sets, boundaries
and required members before selecting. The following explicit example chooses
`set-0001` and names a presentation baseline; neither is an inferred winner:

```bash
hop-design construction select-comparison /tmp/hop-crossed/comparison \
  --set set-0001 --baseline loop3-open17 --out /tmp/hop-crossed-selected
```

For one reproducible command including that explicit selection, use
`run.py --case crossed --set set-0001 --baseline loop3-open17 --out NEW_DIR`.
The corresponding baselines for `methods` and `hairpin` are `bsai` and `loop3`.
Use `loop3-bsai` for `grouped` and `aaa-bsai` for `loop-sequences`.
Outputs are create-only. Keep the selected directory intact when relocating it;
`set.json` retrieves ordinary named preparations and consolidated oligos.

To test the importance of stage, copy `crossed.json`, change only
`discovery.comparison_stage` to `endpoint`, then assess the original discovery
at `comparison/discovery` with `construction assess-comparison`. All four member
slots have complete options, but no four-distinct-insert set exists in that pool.

Geometry counts measure recorded pairing positions at the comparison stage.
A hairpin used as an insert intermediate and an explicit hairpin endpoint are
separate products. See the [full workflow](../../docs/guides/specify-a-comparison.md).

## Preserve retained regions, target a missing member and reuse an old source

```bash
uv run --locked python examples/scaffold-comparison/controlled_panel.py \
  --out /tmp/hop-controlled-panel
```

This v3 recipe requests four exact loop words through two methods. Regional
controls apply to the released product; the hairpins remain visibly different.
It then requests TTC under a tight shared budget and compares preserving the
prior insert with explicitly reusing its source. The changed-method reuse
request retains its bounded negative result; the compatible original method
retrieves a portable preparation bound to the prior source.

Open `panel-selected/comparison/report.pdf` for the controlled panel,
`required-ttc/report.pdf` for targeted search and remaining coverage, and
`reused-source-compatible/report.pdf` for materials referenced to the actual
prior preparation. The recipe explicitly selects `set-0001` with `aaa-bsai` as
its display baseline. The caller supplies the selection.
