"""Build a generic method trajectory from one resolved method plan."""

from __future__ import annotations

from hop_design.kernel.strand_state import complement_iupac
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.linear_source_method import LinearSourceMultinickHairpinPcrPlan
from hop_design.models.method import ProcessMaterialRole
from hop_design.models.views import (
    TrackDirection,
    ViewFeature,
    ViewPairing,
    ViewPanel,
    ViewTrack,
    WorkflowView,
)


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _track(
    track_id: str,
    label: str,
    sequence: str,
    strand: Strand,
    *,
    direction: TrackDirection = TrackDirection.FORWARD,
) -> ViewTrack:
    return ViewTrack(
        track_id=track_id,
        label=label,
        sequence=sequence,
        strand=strand,
        direction=direction,
    )


def _fragment_tracks(
    plan: LinearSourceMultinickHairpinPcrPlan,
    *,
    retained_only: bool,
) -> tuple[ViewTrack, ...]:
    retained = set(plan.length_selected_fragment_set.retained_fragment_ids)
    fragments = (
        fragment
        for fragment in plan.denatured_fragment_set.fragments
        if not retained_only or fragment.fragment_id in retained
    )
    return tuple(
        _track(
            f"fragment_{index}",
            fragment.fragment_id,
            fragment.sequence,
            fragment.precursor_strand,
        )
        for index, fragment in enumerate(fragments)
    )


def _source_panels(plan: LinearSourceMultinickHairpinPcrPlan) -> tuple[ViewPanel, ViewPanel]:
    source = plan.source_pcr_duplex
    tracks = (
        _track("source_top", "source top strand", source.top_strand.sequence, Strand.TOP),
        _track(
            "source_bottom",
            "source bottom strand",
            complement_iupac(source.top_strand.sequence),
            Strand.BOTTOM,
            direction=TrackDirection.REVERSE,
        ),
    )
    nick_features = tuple(
        ViewFeature(
            feature_id=f"nick_{index}",
            track_id="source_top" if site.nick.strand is Strand.TOP else "source_bottom",
            role="nick_boundary",
            label=f"{site.agent_id} nick",
            span=_span(site.nick.boundary.offset, site.nick.boundary.offset),
        )
        for index, site in enumerate(plan.multi_site_nicked_duplex.sites)
    )
    return (
        ViewPanel(panel_id="source_pcr_duplex", title="Source PCR duplex", tracks=tracks),
        ViewPanel(
            panel_id="multi_site_nicked_duplex",
            title="Multi-site nicked duplex",
            tracks=tracks,
            features=nick_features,
        ),
    )


def _annealed_panel(plan: LinearSourceMultinickHairpinPcrPlan) -> ViewPanel:
    retained_ids = set(plan.length_selected_fragment_set.retained_fragment_ids)
    retained = tuple(
        fragment
        for fragment in plan.denatured_fragment_set.fragments
        if fragment.fragment_id in retained_ids
    )
    top = next(fragment for fragment in retained if fragment.precursor_strand is Strand.TOP)
    bottom = next(fragment for fragment in retained if fragment.precursor_strand is Strand.BOTTOM)
    adapter = next(
        material
        for material in plan.materials.materials
        if material.role is ProcessMaterialRole.LIGATION_ADAPTER
    )
    track_ids = {
        top.fragment_id: "selected_top",
        bottom.fragment_id: "selected_bottom",
        adapter.material_id: "ligation_adapter",
    }
    return ViewPanel(
        panel_id="adapter_annealed_complex",
        title="Adapter-annealed complex",
        tracks=(
            _track("selected_top", top.fragment_id, top.sequence, Strand.TOP),
            _track("selected_bottom", bottom.fragment_id, bottom.sequence, Strand.BOTTOM),
            _track("ligation_adapter", "ligation adapter", adapter.sequence, Strand.TOP),
        ),
        pairings=tuple(
            ViewPairing(
                left_track_id=track_ids[pair.left_strand_id],
                left_index=pair.left_index,
                right_track_id=track_ids[pair.right_strand_id],
                right_index=pair.right_index,
                kind=pair.kind.value,
            )
            for pair in plan.adapter_annealed_complex.pairs
        ),
    )


def _ligated_panel(plan: LinearSourceMultinickHairpinPcrPlan) -> ViewPanel:
    selected_ids = set(plan.length_selected_fragment_set.retained_fragment_ids)
    selected = tuple(
        fragment
        for fragment in plan.denatured_fragment_set.fragments
        if fragment.fragment_id in selected_ids
    )
    top = next(fragment for fragment in selected if fragment.precursor_strand is Strand.TOP)
    bottom = next(fragment for fragment in selected if fragment.precursor_strand is Strand.BOTTOM)
    adapter = next(
        material
        for material in plan.materials.materials
        if material.role is ProcessMaterialRole.LIGATION_ADAPTER
    )
    top_end = len(top.sequence)
    bottom_end = top_end + len(bottom.sequence)
    features = tuple(
        ViewFeature(
            feature_id=feature_id,
            track_id="ligated_hairpin",
            role=role,
            label=label,
            span=_span(start, end),
        )
        for feature_id, role, label, start, end in (
            ("selected_top", "selected_fragment", top.fragment_id, 0, top_end),
            ("selected_bottom", "selected_fragment", bottom.fragment_id, top_end, bottom_end),
            (
                "ligation_adapter",
                "ligation_adapter",
                adapter.material_id,
                bottom_end,
                len(plan.ligated_hairpin.strand.sequence),
            ),
        )
    )
    return ViewPanel(
        panel_id="ligated_hairpin",
        title="Ligated hairpin strand",
        tracks=(
            _track(
                "ligated_hairpin",
                "ligated hairpin strand",
                plan.ligated_hairpin.strand.sequence,
                Strand.TOP,
            ),
        ),
        features=features,
    )


def build_method_trajectory_view(plan: LinearSourceMultinickHairpinPcrPlan) -> WorkflowView:
    """Project the closed method state sequence without re-deriving any state."""
    source_panels = _source_panels(plan)
    duplex = plan.hairpin_pcr_duplex
    product = plan.restriction_digest_product
    return WorkflowView(
        view_id=(
            f"hop:view/method-trajectory/{plan.request_digest.removeprefix('sha256:')[:16]}@1"
        ),
        kind="method_trajectory",
        panels=(
            *source_panels,
            ViewPanel(
                panel_id="denatured_fragment_set",
                title="Denatured fragments",
                tracks=_fragment_tracks(plan, retained_only=False),
            ),
            ViewPanel(
                panel_id="length_selected_fragment_set",
                title="Length-selected fragments",
                tracks=_fragment_tracks(plan, retained_only=True),
            ),
            _annealed_panel(plan),
            _ligated_panel(plan),
            ViewPanel(
                panel_id="hairpin_pcr_duplex",
                title="Hairpin PCR duplex",
                tracks=(
                    _track(
                        "hairpin_pcr_top",
                        "PCR top strand",
                        duplex.top_strand.sequence,
                        Strand.TOP,
                    ),
                    _track(
                        "hairpin_pcr_bottom",
                        "PCR bottom strand",
                        complement_iupac(duplex.top_strand.sequence),
                        Strand.BOTTOM,
                        direction=TrackDirection.REVERSE,
                    ),
                ),
            ),
            ViewPanel(
                panel_id="restriction_digest_product",
                title="Destination-neutral restriction product",
                tracks=(
                    _track(
                        "restriction_primary",
                        "primary product strand",
                        product.primary_strand.sequence,
                        Strand.TOP,
                    ),
                    _track(
                        "restriction_complementary",
                        "complementary product strand",
                        product.complementary_strand.sequence,
                        Strand.BOTTOM,
                    ),
                    _track(
                        "hairpin_encoding",
                        "hairpin-encoding projection",
                        product.hairpin_encoding_projection.sequence,
                        Strand.TOP,
                    ),
                ),
            ),
        ),
    )


__all__ = ["build_method_trajectory_view"]
