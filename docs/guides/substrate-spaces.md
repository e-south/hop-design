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
context:
  question: How does activity vary across three paired context positions?
payload:
  segments:
    - fixed: ACTG
    - variable: NNN
      name: context
    - fixed: GATC
      name: recognition-site
hairpin:
  defaults_ref: hop:defaults/generic-hairpin-design@2
enumeration:
  mode: exhaustive
  max_members: 64
```

Three `N` positions each permit `A`, `C`, `G`, or `T`, so the declared space
contains (4^3=64) exact assignments. `context` describes the experimental
question for the review; it does not change design-set identity. The top-level
name, segment labels, equivalent segment boundaries, and a permissive
`max_members` value are likewise presentation or execution concerns rather
than molecular identity.

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
nothing. A valid space larger than `max_members` is `blocked`: no members are
allocated and no partial set is published. `max_members` is limited to
100,000 in this release; larger theoretical spaces can be previewed only when
their submitted execution bound remains within that implementation ceiling.

Compile expands variable positions from 5-prime to 3-prime in `A`, `C`, `G`,
`T` order, compiles every exact member through the existing HOP compiler,
replays every member bundle, and commits only a complete package. It refuses
to replace an existing destination.

## Read the package

```text
build/fixed-site-three-base-context/
├── bundle/             verified digital authority
├── source.yaml         normalized authored specification
├── designs.csv         exact sequence index
├── sequences.fasta     downstream sequence handoff
└── review.html         offline human review
```

Open `review.html` directly in a browser. It explains the paired substrate
anatomy, exact space accounting, evidence boundaries, member sequences, and
handoff files. The HTML, CSV, FASTA, and source copy are regenerable
projections. Only `bundle/` participates in design-set identity and
verification.

Successful compilation establishes complete digital derivation and replay of
64 exact member authorities.
The verified manifest records this evidence boundary directly. A named
construction method and destination compatibility were not evaluated.
Physical construction, QC, and biological activity were not recorded. Later
evidence belongs in separate records that reference the stable design-set ID.

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
