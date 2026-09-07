---
doc_id: hop-discover-source-partitions-guide
title: Discover an exact source partition
intent: Search bounded nickase subsets for a declared full-span fragment partition.
audience:
  - Python users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-09-07
doc_type: how-to
journey:
  - discover
---

# Discover an exact source partition

Use source-partition discovery when the question is:

> Which provisioned nickase combinations preserve these required fragments and
> keep every sacrificial fragment within the declared removal threshold?

This is a route-level question. It is not a basal-junction subtype and it does
not select a preferred enzyme program.

## Author the request

Create a regular, nonsymlink JSON or YAML file with schema
`hop.source-partition-request/v2`. It declares:

- one exact duplex source through its 5′→3′ top sequence and four terminal
  chemistries;
- one final-payload authority and its exact source-coordinate mapping;
- one caller-owned characterized-enzyme catalog and provisioning policy;
- preferred and absolute inclusive sacrificial-fragment maxima;
- the exact top- or bottom-strand spans that must survive;
- the maximum enzymes per program; and
- explicit search-node and realization bounds.

Because this route maps the authored payload onto the source top strand, at least one
required top-strand survivor must fully contain that mapped payload span.

HOP filters the catalog to nickases provisioned for `strand_exposure`. It
enumerates every nonempty subset in width-first lexical order. Selecting an
enzyme applies every actionable occurrence in the supplied duplex; the search
does not silently choose a convenient site.
Terminal cuts that do not partition a strand are recorded as rejected
candidates rather than aborting the remaining search.

## Run and inspect

```python
from pathlib import Path

import hop_design.construction as construction

discovery = construction.discover_source_partition("source-partition.yaml")

print(discovery.status)
print(discovery.examined_nodes, discovery.candidate_space_size)
print(discovery.accepted_realizations)

output = discovery.write(Path("source-partition-result"))

certificate = construction.project_source_partition_certificate(
    discovery,
    realization_id=discovery.realization_ids[0],
)
certificate.write(Path("source-partition-figure"))

verified = construction.load_verified_source_partition(output / "result.json")
assert verified.result_id == discovery.result_id
```

The output contains:

```text
source-partition-result/
├── data.csv
├── fragments.csv
├── result.json
└── thresholds.csv
```

`result.json` is the replay-verified scientific record. It contains every
examined candidate disposition and, for each accepted realization, the exact
nick sites, full two-strand fragment certificate, threshold ladder, selected
survivors, and nick functions. `data.csv` is a tidy candidate table,
`fragments.csv` records every exact fragment and boundary cause, and
`thresholds.csv` records the complete preferred-to-absolute threshold ladder.
These tables support study-owned analysis and rendering without replacing the
JSON authority.

The certificate projection requires an explicit accepted realization ID and
returns canonical JSON, tidy fragment CSV, and a publication-oriented SVG. It
does not auto-select a program or change the source-partition authority.

Nick functions have literal route meaning:

- `retained_fragment_boundary` defines one edge of a required survivor;
- `excluded_fragment_cleanup` subdivides material that the declared length
  selection excludes.

Neither value implies biological importance or enzyme preference.

## Interpret completion

- `complete`: the declared subset domain was exhausted and at least one exact
  partition was accepted;
- `infeasible`: the declared subset domain was exhausted and no exact
  partition was accepted;
- `truncated`: a search-node or realization bound stopped enumeration before
  the domain was exhausted.

The least-permissive successful maximum is selected only after every stricter
declared threshold has been evaluated. A threshold is feasible only when every
sacrificial fragment is at or below it and every required fragment remains
above it. This rule applies equally to internal and terminal fragments.

Changing the fragment policy changes the scientific problem. Increasing
an execution bound does not. A truncated result is never reported as
infeasible.

## Boundary

This result establishes deterministic source partitioning under characterized
cut geometry. It does not establish empirical cleavage efficiency, fragment
recovery, silica-column performance, PCR feasibility, primer melting
temperature, ligation, physical hairpin construction, QC, or activity.
