# Discover compatible basal candidates

Use this search when the question is “which exact basal arm pairs satisfy these
declared domains and pairing policy?” It enumerates candidates; it does not
resolve processing or cut geometry, and it does not choose which candidate
should be tested.

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
ordinal provides reproducible presentation order, not biological preference.
Record any caller selection separately with its objective and chosen candidate
identity.

Continue with the [discovery concepts](../discovery/overview.md) or the
[processing-discovery reference](../reference/processing-discovery.md#basal-searches).
