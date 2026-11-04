"""Allocation-bounded paging of declared domains, including unobserved words and integers."""

from typing import Any

from hop_design.models.construction.variants.domain import ParameterDomainQuery
from hop_design.serialization import canonical_json_bytes


def intervals(domain: dict[str, Any]) -> list[tuple[int, int]]:
    """Canonical union retains holes and never materializes a large numeric range."""
    spans = domain.get("intervals", [domain] if "minimum" in domain else [])
    merged: list[tuple[int, int]] = []
    for a, b in sorted((s["minimum"], s["maximum"]) for s in spans):
        if a > b:
            continue
        if merged and a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def in_domain(domain: dict[str, Any], value: int | str) -> bool:
    if "values" in domain:
        return value in domain["values"]
    return isinstance(value, int) and any(a <= value <= b for a, b in intervals(domain))


def _word(rank: int, length: int) -> str:
    bases = []
    for _ in range(length):
        rank, digit = divmod(rank, 4)
        bases.append("ACGT"[digit])
    return "".join(reversed(bases))


def domain_values(
    domains: dict[str, dict[str, Any]],
    key: str,
    *,
    length: int | None = None,
    prefix: str = "",
    offset: int = 0,
    limit: int = 32,
) -> dict[str, Any]:
    request = ParameterDomainQuery.model_validate_json(
        canonical_json_bytes(
            {
                "key": key,
                "length": length,
                "prefix": prefix,
                "offset": offset,
                "limit": limit,
            }
        )
    )
    domain = domains.get(key, {})
    if length is not None and not in_domain(domains.get("loop_nt", {}), length):
        raise ValueError("Requested loop length is outside the current envelope.")
    values: list[int | str] = []
    if domain.get("alphabet") == "ACGT":
        if request.length is None:
            raise ValueError("Choose a loop length before browsing its unfixed sequence domain.")
        remaining = request.length - len(prefix)
        total = 4**remaining
        values = [prefix + _word(i, remaining) for i in range(offset, min(total, offset + limit))]
    elif "values" in domain:
        available = [
            v
            for v in domain["values"]
            if key != "loop_word"
            or ((length is None or len(str(v)) == length) and str(v).startswith(prefix))
        ]
        total = len(available)
        values = available[offset : offset + limit]
    else:
        spans = intervals(domain)
        total = sum(b - a + 1 for a, b in spans)
        skip = offset
        for a, b in spans:
            size = b - a + 1
            if skip >= size:
                skip -= size
                continue
            values.extend(range(a + skip, min(b + 1, a + skip + limit - len(values))))
            skip = 0
            if len(values) == limit:
                break
    return {
        "key": key,
        "values": values,
        "total": total,
        "offset": offset,
        "next_offset": offset + len(values) if offset + len(values) < total else None,
        "scope": "permitted_domain_not_complete_preparations",
    }
