# Bounded discovery

Use this reference when the question asks which candidates satisfy explicit
domains, catalogs, geometry, and bounds.

Read [the discovery overview](../../../../docs/discovery/overview.md) and import
operations and contracts from `hop_design.discovery`.

- Construct the smallest strict request that answers the competency question.
- Always provide hard node and hit limits.
- Report candidate-space size, nodes examined, hits, fired bounds, and status.
- Preserve `complete`, `infeasible`, and `truncated`; “no hits” is not a status.
- Report canonical order separately from caller-owned selection.
- Do not turn measurements, vendor eligibility, or procurement policy into
hidden ordering inputs.

The runnable baseline is
`examples/discover_basal_candidates.py`. A discovered candidate is compatible
under declared inputs; it is not selected, method-realized, or experimentally
supported.
