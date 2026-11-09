# Discover an exact source partition

A **source partition** records the fragments produced by nicking the source
duplex: which strands must survive and which pieces are to be removed by the
declared length-selection rule. The source is the starting material containing
the payload and construction flanks; it can include DNA absent from the final
product.

Use source-partition discovery when the question is:

> Which permitted nickase combinations preserve these required fragments and
> keep every unwanted fragment within the declared removal threshold?

This search evaluates source-fragment removal across the route. Choose an enzyme
program explicitly from the accepted results.

## Permit cleanup during design discovery

For complete designs using the already permitted source nickases, add this
optional field to the construction context (or an explicit product request):

```json
"source_cleanup": {
  "preferred_maximum_nt": 10,
  "absolute_maximum_nt": 15
}
```

The numbers are inclusive lengths of discarded fragments, in nucleotides.
Discovery evaluates every cut made by the candidate's selected source nickases,
checks that the required strands remain intact, and recompiles the full route
with that certificate. It adds no new enzyme choice and does not waive unwanted
sites. Omitting this permission retains the ordinary site rejection.

Released-insert discovery evaluates source contexts separately. An explicit
request continuation with cleanup must specify one exact source context; it
cannot apply one molecule's certificate to several source sequences. Prepared
`construction.json` is only the expanded molecular input: the request executor
owns cleanup discovery, and the low-level compiler requires an explicit verified
partition. The resulting selection, route, figures and oligos use the same
complete-preparation identity.

To search additional removal enzymes or inspect the partition itself, use the
explicit contract below.

## Author the request

Create a regular, nonsymlink JSON or YAML file with schema
`hop.source-partition-request/v2`. It declares:

- one exact duplex source through its 5′→3′ top sequence and four terminal
  chemistries;
- one final-payload specification and its exact source-coordinate mapping;
- one caller-owned characterized-enzyme catalog and provisioning policy;
- preferred and absolute inclusive sacrificial-fragment maxima;
- the exact top- or bottom-strand spans that must survive;
- the maximum enzymes per program; and
- explicit search-node and realization bounds.

The payload mapping may be forward or reverse-complemented. A required survivor
must contain the complete mapped payload on the top strand for a forward mapping,
or on the bottom strand for a reverse-complement mapping. Both mapping and survivor
spans use the source duplex's top-strand coordinate frame; bottom-strand spans are
not reindexed from that strand's 5′ end. HOP checks the encoded payload sequence
in its declared orientation before searching partitions.

HOP filters the catalog to nickases provisioned for `strand_exposure`. It
enumerates every nonempty subset in width-first lexical order. Selecting an
enzyme applies every actionable occurrence in the supplied duplex; the search
does not silently choose a convenient site.
Terminal cuts that do not partition a strand are recorded as rejected
candidates rather than aborting the remaining search.

## Run and inspect

```python
# Inspect the fragment-removal program for the requested source.
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
Use these tables for analysis and rendering; keep `result.json` for replay.

The certificate projection requires an explicit accepted realization ID and
returns canonical JSON, tidy fragment CSV, and a publication-oriented SVG while
preserving the source-partition result.

Nick functions have literal route meaning:

- `retained_fragment_boundary` defines one edge of a required survivor;
- `excluded_fragment_cleanup` subdivides material that the declared length
  selection excludes.

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
