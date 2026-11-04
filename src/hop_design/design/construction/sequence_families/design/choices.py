"""Required member roster with ordinary complete choices beneath each exact stem."""

from pathlib import Path
from typing import Any

from hop_design.serialization import canonical_json_bytes

from ...intents.base import DesignChoices, PreparationReceipt, Source
from ...packets.atlas import MolecularAtlasPacket
from ...packets.publication import SourceBoundConstructionPacket
from .execute import batches
from .preview import admit_preview


class DesignFamilyChoices(DesignChoices):
    _members: dict[str, DesignChoices]

    def member(self, name: str) -> DesignChoices:
        names = {m["name"] for m in self.resolution["members"]}
        if name not in names:
            raise ValueError(f"Unknown required member {name!r}.")
        if name not in self._members:
            raise ValueError(f"Required member {name} has not been evaluated; continue the family.")
        return self._members[name]

    def query(self, query: Source | None = None) -> dict[str, Any]:
        rows = []
        for member in self.resolution["members"]:
            name = member["name"]
            answer = self._members[name].query(query) if name in self._members else None
            rows.append(
                {
                    "name": name,
                    "stem_arm": member["stem_arm"],
                    "directory": f"members/{name}",
                    "complete_preparations": answer["matching_preparations"] if answer else 0,
                    "products": answer["matching_products"] if answer else {},
                    "choices": answer,
                    "status": "evaluated" if answer else "not_evaluated",
                }
            )
        used, pending = batches(self._directory, self.resolution)
        return {
            "schema": "hop.design-family-choices/v1",
            "request_digest": self.resolution["request_digest"],
            "required_members": len(rows),
            "members": rows,
            "missing_members": [r["name"] for r in rows if not r["complete_preparations"]],
            "reserved_evaluations": used,
            "interrupted_batch": pending,
            "max_total_evaluations": self.resolution["max_total_evaluations"],
            "shared_properties": self.resolution["shared_properties"],
            "shared_material_roles": self.resolution["shared_material_roles"],
            "shared_controls_status": "require_explicit_selection",
            "pooled_library": "not_assessed",
        }

    def explain(self, query: Source | None = None) -> dict[str, Any]:
        answer = self.query(query)
        available = answer["required_members"] - len(answer["missing_members"])
        return {
            **answer,
            "headline": (
                f"{available} of {answer['required_members']} required stems "
                "have complete preparations."
            ),
            "choices": [],
            "actions": (["select_members"] if not answer["missing_members"] else [])
            + (
                ["continue_search"]
                if not answer["interrupted_batch"]
                and answer["reserved_evaluations"] < answer["max_total_evaluations"]
                else []
            ),
        }

    def select_members(
        self, members: dict[str, dict[str, Any]], *, baseline: str
    ) -> dict[str, Any]:
        from .selection import select_members

        return select_members(self, members, baseline=baseline)

    def select(
        self, choice: dict[str, Any] | str, *, query: Source | None = None
    ) -> dict[str, Any]:
        raise ValueError(
            "Select one preparation per required stem with select_members; "
            "inspect choices with member(name)."
        )

    def sample(
        self,
        *,
        seed: int | None = None,
        query: Source | None = None,
        strategy: str | None = None,
        stage: str | None = None,
        history: tuple[str, ...] = (),
        after: Source | None = None,
    ) -> dict[str, Any]:
        raise ValueError(
            "Sample a preparation from member(name); required stem membership remains explicit."
        )

    def _sample_preparation(self, *, seed: int, query: Source | None = None) -> dict[str, Any]:
        raise ValueError(
            "Sample a preparation from member(name), then select the explicit required membership."
        )

    def figure(
        self,
        *,
        query: Source | None = None,
        selection: Source | None = None,
        view: str | None = None,
        stage: str | None = None,
        layout: str | None = None,
        render_policy: str | None = None,
        reference_selection: Source | None = None,
        display_axes: tuple[str, ...] | None = None,
    ) -> SourceBoundConstructionPacket:
        raise ValueError("Choose member(name) to draw its scaffold options.")

    def _inspection_packet(
        self,
        selection: Source,
        *,
        reference_selection: Source | None = None,
        render_policy: str | None = None,
        presentation: str | None = None,
        stage: str | None = None,
        draw_route: bool = False,
    ) -> MolecularAtlasPacket:
        raise ValueError(
            "Choose member(name) and its exact selection to draw that molecular route."
        )

    def retrieve(self, selection: Source, destination: str | Path) -> PreparationReceipt:
        from .selection import retrieve_family

        return retrieve_family(self, selection, destination)


def load_family(root: Path) -> DesignFamilyChoices:
    from ...intents.execute import load_design_choices

    preview = admit_preview(root)
    batches(root, preview)
    members = {}
    for member in preview["members"]:
        directory = root / "members" / member["name"]
        if not directory.exists():
            continue
        choices = load_design_choices(directory)
        actual = {**choices.resolution["intent"], "context": choices.resolution["permissions"]}
        if actual != member["request"]:
            raise ValueError("Saved family member disagrees with its required stem or permissions.")
        members[member["name"]] = choices
    result = object.__new__(DesignFamilyChoices)
    object.__setattr__(result, "_directory", root)
    object.__setattr__(result, "_resolution", canonical_json_bytes(preview))
    object.__setattr__(result, "_members", members)
    return result
