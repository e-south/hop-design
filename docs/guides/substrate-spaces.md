---
doc_id: hop-substrate-spaces
title: Define and compile a bounded substrate space
intent: Preview and compile one complete digital hairpin design set from fixed and variable payload rules.
audience:
  - new users
  - users
owner: HOP Design maintainers
status: active
last_verified: 2026-08-27
doc_type: tutorial
journey:
  - compile
  - verify
---

# Define and compile a bounded substrate space

Use this route when the scientific question concerns a finite set of paired
payload variants in one fixed hairpin context. You author one payload arm. HOP
derives the opposite arm by reverse complement.

The public tracer fixes two payload segments and varies three adjacent
positions:

```yaml
schema: hop/substrate-space/v1
name: fixed-site-three-base-context
question: How does activity vary across three paired context positions?
payload:
  - fixed: ACTG
  - variable: NNN
    label: context
  - fixed: GATC
    label: recognition-site
```

Three `N` positions each permit `A`, `C`, `G`, or `T`, so the declared space
contains (4^3=64) exact assignments. `question` is optional review text and
does not change design-set identity. The top-level name, segment labels, and
equivalent segment boundaries are likewise presentation concerns rather than
molecular identity. HOP applies exhaustive enumeration and the versioned
standard hairpin context without asking the first-use author to configure
package policy.

## Define, preview, compile

From a source checkout:

```bash
uv run hop-design space preview examples/fixed-site-three-base-context.yaml
uv run hop-design space compile examples/fixed-site-three-base-context.yaml \
  --out build/fixed-site-three-base-context
uv run hop-design verify build/fixed-site-three-base-context/bundle
```

Preview validates the specification, reports fixed and variable positions,
reports each actual IUPAC domain, computes exact cardinality, and writes
nothing. This release has a tested release envelope of 256 exact designs. A
larger valid space is `blocked`: preview still reports its symbolic cardinality,
no members are allocated, and no partial set is published.

Compile expands variable positions from 5-prime to 3-prime in `A`, `C`, `G`,
`T` order, compiles every exact member through the existing HOP compiler,
replays every member bundle, and commits only a complete package. It refuses
to replace an existing destination.

## Read the package

```text
build/fixed-site-three-base-context/
├── bundle/             verified digital authority
├── figures/
│   ├── 01-substrate-space.svg
│   └── 02-design-set.svg
├── handoff/
│   └── scientific-receipt.svg
├── designs.csv         exact sequence index
├── sequences.fasta     downstream sequence handoff
└── review.html         offline human review
```

Open `review.html` directly in a browser. It explains the paired substrate
anatomy, exact space accounting, evidence boundaries, member sequences, and
handoff files. The two figure SVGs state the substrate rule and complete member
set; the receipt SVG reports the manifest-backed evidence boundary. The HTML,
SVG, CSV, and FASTA files are regenerable projections. Only `bundle/`
participates in design-set identity and verification.

Successful compilation establishes complete digital derivation and replay of
64 exact member authorities.
The verified manifest records the complete evidence boundary directly. The review says:

> No physical construction, QC, or activity record is attached.

Later evidence belongs in separate records that reference the stable design-set ID.

## Python

```python
import yaml

from hop_design.spaces import SubstrateSpaceSpec, compile_space, preview_space

data = yaml.safe_load(open("examples/fixed-site-three-base-context.yaml"))
spec = SubstrateSpaceSpec.model_validate(data)
preview = preview_space(spec)
assert preview.state == "ready"
verified = compile_space(spec, destination="build/python-space")
assert verified.design_set.coverage == "complete"
```

The scientist-facing facade is `hop_design.spaces`. Advanced discovery retains
its separate `complete`, `infeasible`, and `truncated` semantics; those states
do not apply to this exhaustive-or-blocked surface.
