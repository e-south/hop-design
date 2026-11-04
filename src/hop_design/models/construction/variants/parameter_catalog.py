"""Canonical molecular definitions; selection validation lives in parameters."""

from .parameter_contract import category, dimension

PARAMETERS = (
    category(
        "basal_release_recognition_material",
        "Basal release-site requirement",
        "basal",
        "preparation",
        "assembly",
        "Material required to supply the basal future-release recognition site; "
        "actual site ancestry remains a property of the verified construction.",
        role="required",
    ),
    category(
        "basal_release_product_end",
        "Basal future-release end",
        "basal",
        "preparation",
        "assembly",
        "Released-insert end constrained by the basal local obligation.",
        role="required",
    ),
    dimension(
        "foldback_arm_bp",
        "Loop-side extension",
        "foldback",
        "hairpin",
        "closing",
        "Supplied-stem boundary to loop boundary on the paired arm.",
        "bp",
        "A",
        boundaries=("supplied_stem_end", "loop_start"),
        equivalent_measurements=("loop_side_paired_bp",),
        design_role="product",
    ),
    dimension(
        "join_offset_nt",
        "Foldback join position",
        "foldback",
        "hairpin",
        "closing",
        "Supplied-stem boundary to the foldback ligation boundary.",
        symbol="D",
        boundaries=("supplied_stem_end", "foldback_join"),
    ),
    dimension(
        "self_paired_arm_bp",
        "Self-paired arm",
        "foldback",
        "folded",
        "closing",
        "Foldback join boundary to loop boundary in the self-paired portion.",
        "bp",
        "R",
        dependencies=("foldback_arm_bp", "join_offset_nt"),
        relationship="R = A - D",
        role="derived",
        design_role="outcome",
        boundaries=("foldback_join", "loop_start"),
    ),
    dimension(
        "loop_nt",
        "Loop size",
        "foldback",
        "hairpin",
        "loop",
        "Unpaired nucleotides between the two loop boundaries.",
        symbol="C",
        role="derived",
        design_role="product",
        dependencies=("loop_word",),
        relationship="C = length(loop word)",
        boundaries=("loop_start", "loop_end"),
    ),
    category(
        "loop_word",
        "Loop sequence",
        "foldback",
        "hairpin",
        "loop",
        "Exact loop sequence read in the recorded strand's 5-prime to 3-prime direction.",
        representation="sequence",
        design_role="product",
        boundaries=("loop_start", "loop_end"),
    ),
    category(
        "foldback_strand",
        "Foldback nick strand",
        "foldback",
        "source_duplex",
        "closing",
        "Nicked strand of the source duplex in its declared coordinate frame.",
        representation="orientation",
    ),
    dimension(
        "basal_nick_offset_nt",
        "Basal nick position",
        "basal",
        "source_duplex",
        "assembly",
        "Basal nick boundary to supplied-stem boundary in final-payload coordinates.",
        symbol="n",
        boundaries=("basal_nick", "supplied_stem_start"),
    ),
    category(
        "basal_strand",
        "Basal nick strand",
        "basal",
        "source_duplex",
        "assembly",
        "Nicked strand of the source duplex in its declared coordinate frame.",
        representation="orientation",
    ),
    dimension(
        "adapter_annealing_min_nt",
        "Required adapter annealing",
        "basal",
        "preparation",
        "assembly",
        (
            "Minimum annealing span required by this preparation request; "
            "not an achieved pairing count."
        ),
        role="required",
        glyph_frame="association",
        representation="threshold",
        boundaries=("adapter_ligation", "required_annealing_limit"),
    ),
    dimension(
        "adapter_annealing_achieved_nt",
        "Achieved adapter annealing",
        "basal",
        "source_adapter_association",
        "assembly",
        "Recorded adapter/source contacts in the annealed complex, "
        "including permitted noncanonical contacts.",
        "positions",
        design_role="outcome",
        boundaries=("adapter_ligation", "achieved_annealing_limit"),
    ),
    dimension(
        "noncanonical_pairs",
        "Noncanonical open-side contacts",
        "basal",
        "hairpin",
        "assembly",
        "Recorded non-Watson-Crick contacts in the open-side region.",
        "contacts",
        representation="contact",
        design_role="product",
    ),
    dimension(
        "loop_side_paired_bp",
        "Loop-side extension",
        "scaffold",
        "hairpin",
        "closing",
        "Recorded paired positions between supplied stem and loop.",
        "bp",
        boundaries=("supplied_stem_end", "loop_start"),
        equivalent_measurements=("foldback_arm_bp",),
        canonical_key="foldback_arm_bp",
        design_role="product",
    ),
    dimension(
        "open_side_paired_positions",
        "Basal paired extent",
        "scaffold",
        "hairpin",
        "assembly",
        "Recorded paired positions beyond the supplied stem on the open side.",
        "positions",
        design_role="product",
        boundaries=("first_open_side_contact", "supplied_stem_start"),
    ),
    dimension(
        "five_prime_unpaired_nt",
        "5\u2032 tail",
        "scaffold",
        "hairpin",
        "assembly",
        "Unpaired terminal bases from the 5-prime terminus to the first recorded contact.",
        boundaries=("hairpin_5prime_terminus", "first_open_side_contact"),
        design_role="product",
    ),
    dimension(
        "three_prime_unpaired_nt",
        "3\u2032 tail",
        "scaffold",
        "hairpin",
        "assembly",
        "Unpaired terminal bases from the 3-prime terminus to the last recorded contact.",
        boundaries=("last_open_side_contact", "hairpin_3prime_terminus"),
        design_role="product",
    ),
    *tuple(
        definition
        for side in ("left", "right")
        for definition in (
            dimension(
                f"{side}_gap",
                f"{side.title()} gap",
                "interfaces",
                "released_insert",
                "interfaces",
                f"Recorded {side} released-end boundary to its supplied-stem boundary.",
                "bp",
                design_role="product",
                boundaries=(f"{side}_released_paired_boundary", f"{side}_supplied_stem_boundary"),
            ),
            category(
                f"{side}_end_word",
                f"{side.title()} sticky end",
                "interfaces",
                "released_insert",
                "interfaces",
                "Exposed end word in the protruding strand's 5-prime to 3-prime direction.",
                representation="sequence",
                design_role="product",
                boundaries=(f"{side}_overhang_start", f"{side}_overhang_end"),
            ),
            category(
                f"{side}_end_polarity",
                f"{side.title()} end polarity",
                "interfaces",
                "released_insert",
                "interfaces",
                "5-prime or 3-prime protrusion on this released product end.",
                representation="orientation",
                design_role="product",
            ),
        )
    ),
    *tuple(
        category(
            f"{role}_method",
            label,
            "methods",
            "preparation",
            region,
            "Actual enzyme program used for this role; multiple enzymes remain a joint choice.",
            glyph_frame="insert" if role == "release" else "source",
            representation="recognition",
        )
        for role, label, region in (
            ("foldback", "Foldback nickase", "closing"),
            ("basal", "Basal nickase", "assembly"),
            ("release", "Release enzyme", "interfaces"),
        )
    ),
    category(
        "background",
        "Outside-loop scaffold",
        "scaffold",
        "comparison_stage",
        "stem",
        "Exact regional sequence, contacts and termini outside the loop at the comparison stage.",
        role="comparison",
        design_role="comparison",
    ),
    category(
        "methods",
        "Enzyme methods",
        "methods",
        "preparation",
        "assembly",
        "Joint complete-preparation enzyme set.",
        design_role="outcome",
    ),
    *tuple(
        dimension(
            f"source_{side}_primer_{kind}_nt",
            f"Source {side} primer {kind}",
            "basal",
            "source_duplex",
            "assembly" if side == "forward" else "closing",
            "Primer annealing requirement outside the supplied stem."
            if kind == "required"
            else (
                "Available source flank outside the supplied stem; "
                "this span alone does not establish a complete preparation."
            ),
            role="required" if kind == "required" else "achieved",
            design_role="construction" if kind == "required" else "outcome",
            representation="threshold" if kind == "required" else "span",
            boundaries=("source_5prime_terminus", "forward_primer_inward_boundary")
            if side == "forward" and kind == "required"
            else ("reverse_primer_inward_boundary", "source_3prime_terminus")
            if kind == "required"
            else ("source_5prime_terminus", "supplied_stem_start")
            if side == "forward"
            else ("supplied_stem_end", "source_3prime_terminus"),
        )
        for side in ("forward", "reverse")
        for kind in ("required", "available")
    ),
)
