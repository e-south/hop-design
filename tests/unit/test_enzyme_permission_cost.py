"""Permission rejection does not need a fresh catalog scan on every candidate."""

import pytest

from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
)
from tests.contract.test_reaction_stages import _catalog, _nickase, _restriction_enzyme


def policy(**updates):
    nick, cut = _nickase(), _restriction_enzyme()
    return EnzymeProvisioningPolicy(
        **{
            "catalog": _catalog(nick, cut),
            "allowed_enzyme_ids": (),
            "forbidden_enzyme_ids": (),
            "reserved_enzyme_ids": (),
            "role_restrictions": (),
            **updates,
        }
    )


@pytest.mark.parametrize("restriction", ["allowed", "forbidden", "reserved", "role"])
def test_explicitly_denied_candidate_needs_no_catalog_scan(monkeypatch, restriction):
    nick, cut = _nickase().enzyme_id, _restriction_enzyme().enzyme_id
    restrictions = {
        "allowed": {"allowed_enzyme_ids": (nick,)},
        "forbidden": {"forbidden_enzyme_ids": (cut,)},
        "reserved": {"reserved_enzyme_ids": (cut,)},
        "role": {
            "role_restrictions": (
                EnzymeRoleRestriction(role=EnzymeRole.FOLDBACK_NICK, allowed_enzyme_ids=(nick,)),
            )
        },
    }
    configured = policy(**restrictions[restriction])
    original, reads = CharacterizedEnzyme.__getattribute__, []

    def observed(self, name):
        if name == "enzyme_id":
            reads.append(name)
        return original(self, name)

    monkeypatch.setattr(CharacterizedEnzyme, "__getattribute__", observed)
    assert not configured.permits(cut, role=EnzymeRole.FOLDBACK_NICK)
    assert reads == []


def test_unknown_ids_and_changed_catalogs_remain_checked_after_prior_lookup():
    configured = policy()
    nick, cut = (e.enzyme_id for e in configured.catalog.enzymes)
    for role in EnzymeRole:
        assert configured.permits(nick, role=role)
        assert configured.permits(cut, role=role)
        assert not configured.permits("example:enzyme/unknown@1", role=role)
    reduced = configured.model_copy(update={"catalog": _catalog(_nickase())})
    for role in EnzymeRole:
        assert reduced.permits(nick, role=role)
        assert not reduced.permits(cut, role=role)
    assert EnzymeProvisioningPolicy.model_validate_json(configured.model_dump_json()) == configured
