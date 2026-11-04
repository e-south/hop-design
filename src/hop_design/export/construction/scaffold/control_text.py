"""Plain labels for verified comparison controls, shared by reading surfaces."""

from hop_design.models.construction.family.controls import ComparisonControl

PROPERTY_LABELS = {
    "stem_sequence": "Supplied stem sequence",
    "endpoint": "Product endpoint",
    "release_interfaces": "Later release interfaces",
    "open_side_paired_positions": "Open-side paired extent",
    "loop_side_paired_bp": "Loop-side paired extension",
    "loop_nt": "Loop nucleotide count",
    "five_prime_unpaired_nt": "5\u2032 unpaired terminal tract (nt)",
    "three_prime_unpaired_nt": "3\u2032 unpaired terminal tract (nt)",
    "terminal_chemistry": "Hairpin terminal chemistry",
    "non_loop_sequences": "Non-loop regional sequences",
    "regional_contacts": "Region-local pairing contacts",
    "regional_joins": "Region-local covalent joins",
}


def control_label(control: ComparisonControl) -> str:
    if control.status == "different":
        return "Requirement not met" if control.required else "Observed difference"
    return {
        "required_and_verified": "Required and verified",
        "observed_agreement": "Observed agreement",
        "not_assessed": "Required; not assessed" if control.required else "Not assessed",
    }[control.status]
