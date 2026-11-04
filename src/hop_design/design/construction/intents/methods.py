"""Resolve displayed enzyme names and exact IDs against one admitted policy."""

from hop_design.models.enzymes import EnzymeClass, EnzymeProvisioningPolicy, EnzymeRole

METHOD_ROLES = {
    "foldback": EnzymeRole.FOLDBACK_NICK,
    "basal": EnzymeRole.BASAL_NICK,
    "release": EnzymeRole.END_GENERATION,
}


def resolve_method_ids(
    names: tuple[str, ...], *, role: str, policy: EnzymeProvisioningPolicy
) -> tuple[str, ...]:
    """Never choose between same-named catalog entries or expand permissions."""
    enzyme_class = EnzymeClass.DUPLEX_RESTRICTION if role == "release" else EnzymeClass.NICKASE
    permitted = tuple(
        enzyme
        for enzyme in policy.catalog.enzymes
        if enzyme.enzyme_class is enzyme_class
        and policy.permits(enzyme.enzyme_id, role=METHOD_ROLES[role])
    )
    selected = []
    for name in names:
        exact = [e for e in permitted if str(e.enzyme_id) == name]
        candidates = exact or [e for e in permitted if e.canonical_name == name]
        if not candidates:
            available = ", ".join(e.canonical_name for e in permitted) or "none"
            raise ValueError(
                f"Requested {role} method {name!r} is not permitted by this context. "
                f"Permitted methods: {available}. "
                f"Edit methods.{role} or the context's {role}.enzymes explicitly."
            )
        if len(candidates) > 1:
            identities = ", ".join(str(e.enzyme_id) for e in candidates)
            raise ValueError(
                f"Ambiguous {role} method {name!r}; choose an exact catalog ID: {identities}."
            )
        selected.append(str(candidates[0].enzyme_id))
    if len(set(selected)) != len(selected):
        raise ValueError(f"Requested {role} methods must not repeat after name resolution.")
    return tuple(selected)
