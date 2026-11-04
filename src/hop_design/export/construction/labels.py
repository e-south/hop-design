"""Reader-facing labels, separate from stable molecular identifiers."""

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.molecular_state import EndChemistry


def terminal_label(prime: str, chemistry: EndChemistry) -> str:
    """Compact explicit chemistry shared by molecular states and input orders."""
    return prime + ("P" if chemistry is EndChemistry.PHOSPHATE else "OH")


def endpoint_label(endpoint: ConstructionEndpoint) -> str:
    return {
        ConstructionEndpoint.SSDNA_HAIRPIN: "ssDNA hairpin",
        ConstructionEndpoint.ADAPTER_LIGATED_HAIRPIN: "adapter-ligated hairpin",
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX: "copied hairpin duplex",
        ConstructionEndpoint.CLONE_READY_DUPLEX: "released duplex insert",
    }[endpoint]


def material_role_label(role: MaterialUseRole) -> str:
    return {
        MaterialUseRole.SOURCE_SSDNA: "source oligo",
        MaterialUseRole.SOURCE_MATERIALIZATION_FORWARD_PRIMER: "source forward primer",
        MaterialUseRole.SOURCE_MATERIALIZATION_REVERSE_PRIMER: "source reverse primer",
        MaterialUseRole.LIGATION_ADAPTER: "adapter",
        MaterialUseRole.ENDPOINT_FORWARD_PRIMER: "endpoint forward primer",
        MaterialUseRole.ENDPOINT_REVERSE_PRIMER: "endpoint reverse primer",
    }[role]


def drawing_material_label(role: MaterialUseRole) -> str:
    """Short names on the molecular drawing; full role names remain in metadata."""
    return {
        MaterialUseRole.SOURCE_MATERIALIZATION_FORWARD_PRIMER: "Source forward",
        MaterialUseRole.SOURCE_MATERIALIZATION_REVERSE_PRIMER: "Source reverse",
        MaterialUseRole.ENDPOINT_FORWARD_PRIMER: "Hairpin forward",
        MaterialUseRole.ENDPOINT_REVERSE_PRIMER: "Hairpin reverse",
    }.get(role, material_role_label(role).capitalize())


def state_label(value: str) -> str:
    return "released duplex insert" if value == "clone_ready_duplex" else value.replace("_", " ")


def atlas_state_label(value: str) -> str:
    """Short stage titles for a complete route; stable state IDs remain unchanged."""
    return {
        "source_ssdna": "Source ssDNA",
        "duplex": "Copied duplex",
        "cleaved_duplex": "Cleaved duplex",
        "denatured_fragments": "Separated fragments",
        "selected_fragments": "Retained fragments",
        "annealed_complex": "Annealed fragments",
        "foldback_closed_hairpin": "Closed hairpin",
        "adapter_annealed": "Adapter association",
        "adapter_ligated": "Ligated hairpin",
        "hairpin_pcr_duplex": "Hairpin PCR duplex",
        "clone_ready_duplex": "Released insert",
    }.get(value, state_label(value))


def enzyme_label(enzyme_id: str, names: tuple[tuple[str, str], ...]) -> str:
    name = dict(names).get(enzyme_id)
    return enzyme_id if name is None else f"{name} ({enzyme_id})"


def operation_label(kind: str) -> str:
    """Name physical operations without leaking executor phase names."""
    return {
        "source_copying": "Source PCR",
        "source_materialization": "Source PCR",
        "enzyme_phase": "Enzymatic cleavage",
        "denaturation": "Strand separation",
        "fragment_selection": "Fragment retention",
        "annealing": "Annealing",
        "ligation": "Ligation",
        "primer_extension": "Primer extension",
        "end_generation": "Insert release",
    }.get(kind, kind.replace("_", " "))
