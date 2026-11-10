# Discover compatible basal candidates

Enumerate exact basal arm pairs that satisfy the declared domains and pairing
policy. To resolve processing and cut geometry, continue with
[construction compilation](compile-construction.md).

Run the public example from a contributor checkout:

```bash
# Run the bounded basal-junction example from a source checkout.
uv run python examples/discover_basal_candidates.py
```

The example constructs a strict `BasalCandidateSearchRequest` and supplies both
budgets:

```python
# Search the same local problem through Python.
import hop_design.discovery as discovery

result = discovery.search_basal_candidates(
    request,
    limits=discovery.BasalCandidateSearchLimits(
        max_search_nodes=2,
        max_hits=2,
    ),
)
```

Interpret the result by status:

- `complete`: the declared space was exhausted and at least one compatible hit
  exists;
- `infeasible`: the declared space was exhausted without a compatible hit;
- `truncated`: a named bound stopped the search before either conclusion was
  justified.

Every hit has a content-derived `candidate_id` and a `canonical_ordinal`. The
ordinal provides reproducible presentation order.
Record any caller selection separately with its objective and chosen candidate
identity.

Continue with the [discovery concepts](../discovery/overview.md) or the
[processing-discovery reference](../reference/processing-discovery.md#basal-searches).
