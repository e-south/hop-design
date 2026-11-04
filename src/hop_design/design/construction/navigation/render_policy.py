"""Rendering preferences are explicit and never replace the molecular producer."""

import json
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from hop_design.design.source_documents import load_source_mapping
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..intents.base import Source
from ..packets.atlas import MolecularAtlasPacket
from .types import ChoiceSource


@dataclass(frozen=True)
class RenderContext:
    selection: Source
    reference: Source | None
    policy: str
    presentation: str
    stage: str

    def finish(
        self,
        packet: MolecularAtlasPacket,
        effective: str,
        *,
        notice: str | None = None,
        draw_route: bool = True,
    ) -> MolecularAtlasPacket:
        from .route_presentation import present_route, route_facts

        states = json.loads(packet.json_bytes)["atlas"]["states"]
        if self.stage != "all" and not any(s["state"]["state_id"] == self.stage for s in states):
            raise ValueError("Viewed state is not recorded in this preparation.")
        if not draw_route:
            return rendering_receipt(packet, self.policy, effective, notice=notice)
        if effective == "current":
            packet = present_route(packet, self.presentation, self.stage)
        route = route_facts(packet, self.presentation)
        if route["effective"] != self.presentation:
            explanation = (
                "Captured route composition is unchanged; choose current glyph style to recompose."
                if effective == "captured"
                else "Complete route exposes the inspected cleanup state; All restores assembly."
            )
            notice = " ".join(filter(None, (notice, explanation)))
        return rendering_receipt(packet, self.policy, effective, notice=notice, route=route)


def renderer_identity() -> dict[str, str]:
    package = Path(__file__).resolve().parents[3]
    files = {
        p.relative_to(package).as_posix(): sha256_digest(p.read_bytes())
        for name in ("export/construction", "assets")
        for p in (package / name).rglob("*")
        if p.is_file() and p.suffix in {".py", ".js", ".css", ".html"}
    }
    return {
        "contract": "hop.atlas-edition-renderer/v1",
        "package_version": version("hop-design"),
        "content": sha256_digest(canonical_json_bytes(files)),
    }


def render_context(
    choices: ChoiceSource,
    selection: Source,
    reference: Source | None,
    policy: str | None,
    presentation: str | None = None,
    stage: str | None = None,
) -> RenderContext:
    raw = load_source_mapping(selection) if isinstance(selection, str | Path) else selection
    if raw.get("schema", "").startswith("hop.atlas-view/"):
        view = choices.restore_view(raw)
        selection = view["selection"]
        policy = view["render_policy"] if policy is None else policy
        presentation = view["presentation"]["route"] if presentation is None else presentation
        stage = view["stage"] if stage is None else stage
        if reference is None and view["reference_identity"]:
            reference = choices.select(view["reference_identity"])
    policy = policy or "captured"
    if policy not in {"captured", "current"}:
        raise ValueError("Choose captured or current render policy.")
    if presentation not in {None, "complete", "assembly"}:
        raise ValueError("Choose complete or assembly route presentation.")
    return RenderContext(selection, reference, policy, presentation or "complete", stage or "all")


def rendering_receipt(
    packet: MolecularAtlasPacket,
    requested: str,
    effective: str,
    *,
    notice: str | None = None,
    route: dict[str, object] | None = None,
) -> MolecularAtlasPacket:
    summary = json.loads(packet.json_bytes)
    summary["rendering"] = {
        "requested": requested,
        "effective": effective,
        "renderer": renderer_identity() if effective == "current" else None,
        "notice": notice,
        **({"route": route} if route is not None else {}),
    }
    result = type(packet)._create(dict(packet._files), summary, packet.report_text)
    object.__setattr__(result, "_roots", packet._roots)
    return result
