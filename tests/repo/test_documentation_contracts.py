"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_documentation_contracts.py

Tests documentation metadata, links, examples, and durable claim language.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest
import yaml

import hop_design as hop
import hop_design.construction as hop_construction
import hop_design.discovery as hop_discovery
import hop_design.methods as hop_methods
import hop_design.spaces as hop_spaces
import hop_design.views as hop_views
from hop_design import api as hop_api
from tests.support.claim_language import assert_no_positive_downstream_claims

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_docs_checker() -> ModuleType:
    path = REPO_ROOT / "scripts" / "check_docs.py"
    spec = importlib.util.spec_from_file_location("hop_check_docs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_landing_page_routes_without_becoming_a_manual() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# ![hop — Hairpin Oligonucleotide Processing")
    assert "assets/hop-design-banner.svg" in readme
    assert "codecov.io/gh/e-south/hop-design/graph/badge.svg" in readme
    assert "HOP is alpha software" in readme
    assert "docs/guides/quickstart.md" in readme
    assert "https://github.com/e-south/hop-design/blob/main/AGENTS.md" in readme
    assert "[AGENTS.md](AGENTS.md)" not in readme
    assert "CONTRIBUTING.md" in readme
    assert "SECURITY.md" in readme
    assert "docs/index.md" in readme
    assert "Specify the duplex context you want to test" in readme
    assert "question → substrate rule → exact paired designs" in readme
    assert "does not choose a biological target or publication example" in readme
    assert "No physical construction, QC, or activity record is attached" in readme
    assert "docs/guides/substrate-spaces.md" in readme
    assert "domain-specific language" not in readme
    assert "```" not in readme
    assert "## Install" not in readme
    assert "## Compile a design" not in readme
    assert len(readme.splitlines()) <= 80


def test_scientist_surface_keeps_the_64_member_space_as_a_verification_fixture() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    guide = (REPO_ROOT / "docs" / "guides" / "substrate-spaces.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "guides" / "quickstart.md").read_text(encoding="utf-8")
    cli = (REPO_ROOT / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    spec_path = REPO_ROOT / "examples" / "fixed-site-three-base-context.yaml"

    for text in (readme, quickstart, guide):
        assert "define" in text.lower()
        assert "preview" in text.lower()
        assert "compile" in text.lower()
    for text in (readme, quickstart):
        assert "payload library" not in text.lower()
    assert "hop-design space preview" in guide
    assert "hop-design space compile" in guide
    assert "hop-design verify" in guide
    assert "64 exact" in guide
    assert "verification fixture" in guide
    assert "publication claim" in guide
    assert "review.html" in guide
    assert "No physical construction, QC, or activity record is attached" in guide
    assert "256" in guide
    assert "tested release envelope" in guide
    assert "source.yaml" not in guide
    assert "--dry-run" in cli
    assert "--out is optional with `--dry-run`" in cli
    assert spec_path.is_file()
    spec_text = spec_path.read_text()
    for removed_field in ("context:", "hairpin:", "enumeration:", "max_members"):
        assert removed_field not in spec_text
    spec = hop_spaces.SubstrateSpaceSpec.model_validate(yaml.safe_load(spec_text))
    preview = hop_spaces.preview_space(spec)
    assert preview.state == "ready"
    assert preview.theoretical_cardinality == 64
    assert "three `N` positions define 64 exact designs" not in readme
    assert "publication-oriented" not in (
        REPO_ROOT / "src" / "hop_design" / "export" / "space_figures.py"
    ).read_text(encoding="utf-8")


def test_public_docs_route_the_five_sibling_surfaces() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_index = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    expected_routes = {
        "start/mental-model.md",
        "language/overview.md",
        "discovery/overview.md",
        "methods/overview.md",
        "provenance/overview.md",
        "ecosystem/ownership-boundaries.md",
    }
    for route in expected_routes:
        assert (REPO_ROOT / "docs" / route).is_file()
        assert route in docs_index
    assert "docs/start/mental-model.md" in readme
    assert not (REPO_ROOT / "docs" / "concepts").exists()

    processing = (REPO_ROOT / "docs" / "reference" / "processing-discovery.md").read_text(
        encoding="utf-8"
    )
    assert "sequence-and-cut compatible" in processing
    assert "empirical cleavage efficiency" in processing


def test_public_docs_distinguish_the_scientist_facade_from_specialist_surfaces() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    language = (REPO_ROOT / "docs" / "language" / "overview.md").read_text(encoding="utf-8")
    docs_index = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    public_text = "\n".join((readme, language, docs_index))

    assert "`hop_design.spaces` is the scientist-facing facade" in public_text
    for specialist_surface in (
        "`hop_design`",
        "`hop_design.discovery`",
        "`hop_design.methods`",
        "`hop_design.views`",
    ):
        assert specialist_surface in public_text
    assert "small public vocabulary" not in language.lower()


def test_discovery_docs_define_truthful_exact_first_local_results() -> None:
    discovery = (REPO_ROOT / "docs" / "discovery" / "overview.md").read_text(encoding="utf-8")
    view_contracts = (REPO_ROOT / "docs" / "reference" / "view-contracts.md").read_text(
        encoding="utf-8"
    )
    reliability = (REPO_ROOT / "RELIABILITY.md").read_text(encoding="utf-8")
    normalized = " ".join(discovery.split())
    normalized_views = " ".join(view_contracts.split())
    normalized_reliability = " ".join(reliability.split())

    assert "Exact targets are examined before enabled relaxation shells" in normalized
    assert "requested geometry" in normalized
    assert "achieved geometry" in normalized
    assert "not an optimization" in normalized
    assert "declared stopping rule" in normalized
    assert "through_radius" in discovery
    assert "first_feasible_shell" in discovery
    assert "every candidate in the declared neighborhood was examined" not in normalized
    assert "infeasible" in discovery
    assert "truncated" in discovery
    assert "does not establish physical construction" in normalized
    assert "local construction projection" in normalized
    for schema_id in (
        "hop.foldback-feasibility-landscape/v2",
        "hop.basal-feasibility-landscape/v1",
        "hop.foldback-relaxation-frontier/v2",
        "hop.basal-relaxation-frontier/v1",
    ):
        assert schema_id in view_contracts
    assert "verified against its exact source result" in normalized_views
    assert "Only the final examined shell may be partial" in normalized_reliability


@pytest.mark.parametrize(
    "relative_path",
    (
        "README.md",
        "docs/index.md",
        "docs/guides/quickstart.md",
        "docs/start/why-hop.md",
        "docs/discovery/overview.md",
        "docs/reference/view-contracts.md",
    ),
)
def test_default_scientist_surfaces_do_not_make_positive_downstream_claims(
    relative_path: str,
) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert_no_positive_downstream_claims(text, surface=relative_path)


def test_public_claim_language_keeps_digital_derivation_narrow() -> None:
    why_hop = (REPO_ROOT / "docs" / "start" / "why-hop.md").read_text(encoding="utf-8")
    cli = (REPO_ROOT / "src" / "hop_design" / "cli.py").read_text(encoding="utf-8")

    assert "constraint-checked hairpin anatomy" in why_hop
    assert "bundle validated" not in cli.lower()
    assert "design derivation verified; no files written" in cli.lower()


def test_action_routes_have_runnable_public_examples() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_index = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "guides" / "quickstart.md").read_text(encoding="utf-8")
    method_guide = (REPO_ROOT / "docs" / "guides" / "resolve-production-method.md").read_text(
        encoding="utf-8"
    )
    provenance = (REPO_ROOT / "docs" / "provenance" / "overview.md").read_text(encoding="utf-8")

    for path in (
        "docs/guides/discover-compatible-basal-candidates.md",
        "docs/guides/resolve-production-method.md",
        "examples/discover_basal_candidates.py",
        "examples/compile_linear_source_method.py",
        "examples/compile_payload_records.py",
        "examples/linear-source-matched-design.yaml",
        "examples/verify_design_method_handoff.py",
    ):
        assert (REPO_ROOT / path).is_file(), path
    assert "docs/guides/discover-compatible-basal-candidates.md" in readme
    assert "docs/guides/resolve-production-method.md" in readme
    assert "guides/discover-compatible-basal-candidates.md" in docs_index
    assert "guides/resolve-production-method.md" in docs_index
    assert "discover-compatible-basal-candidates.md" in quickstart
    assert "resolve-production-method.md" in quickstart
    assert "payload-sources-and-expansion.md" in quickstart
    for text in (docs_index, method_guide, provenance):
        assert "examples/verify_design_method_handoff.py" in text
    assert "--out build/matched-handoff" in provenance


def test_public_discovery_and_method_examples_execute(tmp_path: Path) -> None:
    discovery = subprocess.run(
        [sys.executable, "examples/discover_basal_candidates.py"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    discovery_rows = json.loads(discovery.stdout)
    assert [row["status"] for row in discovery_rows] == [
        "complete",
        "infeasible",
        "truncated",
    ]
    assert discovery_rows[-1]["truncated_by"] == ["max_search_nodes"]

    output = tmp_path / "method-bundle"
    method = subprocess.run(
        [
            sys.executable,
            "examples/compile_linear_source_method.py",
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    method_summary = json.loads(method.stdout)
    assert method_summary["product_state"] == "restriction-digest-product"
    assert method_summary["destination_readiness"] == "not_evaluated"
    assert (
        hop_methods.load_verified_method_bundle(output).bundle.bundle_id
        == (method_summary["bundle_id"])
    )


def test_public_matched_handoff_example_executes(tmp_path: Path) -> None:
    output = tmp_path / "handoff"
    completed = subprocess.run(
        [
            sys.executable,
            "examples/verify_design_method_handoff.py",
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert set(summary) == {
        "design_bundle_verified",
        "method_bundle_verified",
        "design_digest",
        "method_bundle_digest",
        "product_projection_digest",
        "design_bundle_id",
        "method_bundle_id",
    }
    assert summary["design_bundle_verified"] is True
    assert summary["method_bundle_verified"] is True
    assert summary["design_digest"] == summary["method_bundle_digest"]
    assert summary["method_bundle_digest"] == summary["product_projection_digest"]
    repeated = subprocess.run(
        [
            sys.executable,
            "examples/verify_design_method_handoff.py",
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert repeated.returncode != 0
    assert "FileExistsError" in repeated.stderr
    assert (
        hop.load_verified_bundle(output / "design").bundle.bundle_id == summary["design_bundle_id"]
    )
    assert (
        hop_methods.load_verified_method_bundle(output / "method").bundle.bundle_id
        == summary["method_bundle_id"]
    )


def test_public_payload_record_example_executes(tmp_path: Path) -> None:
    output = tmp_path / "payload-records"
    completed = subprocess.run(
        [
            sys.executable,
            "examples/compile_payload_records.py",
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["schema"] == "hop.payload-record-compilation/v1"
    assert summary["payload_count"] == 3
    assert summary["design_count"] == 3
    assert summary["feasible_count"] == 3
    assert summary["bundle_verified_count"] == 3
    assert summary["method_resolution_status"] == "not_evaluated"
    assert len(summary["designs"]) == 3
    assert all(
        row["paired_payload_sequence"]
        == hop.ExactPayload(sequence=row["payload_sequence"]).paired_sequence
        for row in summary["designs"]
    )
    assert all(
        hop.load_verified_bundle(output / row["payload_id"]).bundle.bundle_id == row["bundle_id"]
        for row in summary["designs"]
    )

    repeated = subprocess.run(
        [
            sys.executable,
            "examples/compile_payload_records.py",
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert repeated.returncode != 0
    assert "already exists" in repeated.stderr


def test_advanced_payload_example_uses_digital_record_language() -> None:
    guide = (REPO_ROOT / "docs" / "guides" / "payload-sources-and-expansion.md").read_text(
        encoding="utf-8"
    )
    assert (REPO_ROOT / "examples" / "compile_payload_records.py").is_file()
    assert not (REPO_ROOT / "examples" / "compile_payload_library.py").exists()
    assert "payload library" not in guide.lower()
    assert "compile_payload_records.py" in guide


def test_symbolic_encoding_language_and_handoff_paths_match_public_models() -> None:
    public_text = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "docs/index.md",
            "docs/start/mental-model.md",
            "docs/start/why-hop.md",
            "docs/language/overview.md",
        )
    )
    provenance = (REPO_ROOT / "docs" / "provenance" / "overview.md").read_text(encoding="utf-8")

    assert "exact, verified encoding" not in public_text
    assert "exact feature-partitioned encoding" not in public_text
    assert "verified_design.plan.hairpin_encoding_insert.sequence_digest" in provenance
    assert "verified_method.bundle.hairpin_encoding_digest" in provenance
    assert "HopBundle.hairpin_encoding" not in provenance
    assert "MethodBundle.restriction_product" not in provenance


def test_campaign_context_is_generic_at_the_durable_route() -> None:
    campaign = REPO_ROOT / "docs" / "ecosystem" / "campaign-orchestration.md"
    assert campaign.is_file()
    text = campaign.read_text(encoding="utf-8")
    assert "doc_id: hop-campaign-orchestration" in text
    assert "Proto-like campaign" not in text
    assert not (REPO_ROOT / "docs" / "ecosystem" / "proto-and-campaign-orchestration.md").exists()


def test_docs_index_preserves_the_claim_journey_order() -> None:
    docs_index = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    labels = (
        "**Design language:**",
        "**Discovery language:**",
        "**Method language:**",
        "**Verify and inspect:**",
        "**Integrate:**",
    )
    positions = [docs_index.index(label) for label in labels]
    assert positions == sorted(positions)


def test_every_numbered_adr_is_indexed_once() -> None:
    decision_root = REPO_ROOT / "docs" / "architecture" / "decisions"
    index = (decision_root / "README.md").read_text(encoding="utf-8")

    for decision in sorted(decision_root.glob("[0-9][0-9][0-9][0-9]-*.md")):
        assert index.count(f"({decision.name})") == 1


def test_agent_inline_route_targets_fail_closed() -> None:
    checker = _load_docs_checker()
    errors = checker.check_inline_route_targets(
        REPO_ROOT / "AGENTS.md",
        "Read `docs/does-not-exist.md` before proceeding.",
    )

    assert errors == ["AGENTS.md: broken inline route 'docs/does-not-exist.md'"]


def test_skill_metadata_is_structurally_validated() -> None:
    checker = _load_docs_checker()
    errors = checker.check_skill_metadata(
        REPO_ROOT / ".agents" / "skills" / "example" / "SKILL.md",
        {"description": "Example skill.", "metadata": "version: 1"},
    )

    assert errors == [".agents/skills/example/SKILL.md: metadata must be a YAML mapping"]
    assert checker.check_skill_metadata(
        REPO_ROOT / ".agents" / "skills" / "example" / "SKILL.md",
        {
            "description": "x" * 221,
            "metadata": {"version": "1", "category": "testing", "tags": ["example"]},
        },
    ) == [".agents/skills/example/SKILL.md: description exceeds 220 characters"]
    assert checker.check_skill_metadata(
        REPO_ROOT / ".agents" / "skills" / "example" / "SKILL.md",
        {
            "description": "   ",
            "metadata": {"version": "1", "category": "testing", "tags": ["example"]},
        },
    ) == [".agents/skills/example/SKILL.md: description must be a non-empty string"]
    assert checker.check_skill_metadata(
        REPO_ROOT / ".agents" / "skills" / "example" / "SKILL.md",
        {
            "description": 42,
            "metadata": {"version": "1", "category": "testing", "tags": ["example"]},
        },
    ) == [".agents/skills/example/SKILL.md: description must be a non-empty string"]


def test_document_frontmatter_uses_controlled_routing_fields() -> None:
    checker = _load_docs_checker()
    path = REPO_ROOT / "docs" / "example.md"

    assert (
        checker.check_document_metadata(
            path,
            {
                "audience": ["users"],
                "doc_type": "how-to",
                "journey": ["compile"],
                "status": "active",
            },
        )
        == []
    )
    assert checker.check_document_metadata(
        path,
        {
            "audience": ["everyone"],
            "doc_type": "how-to",
            "status": "active",
        },
    ) == [
        "docs/example.md: audience must use controlled reader roles",
        "docs/example.md: how-to documents require journey routing",
    ]


def test_document_inline_route_targets_fail_closed() -> None:
    checker = _load_docs_checker()
    errors = checker.check_inline_route_targets(
        REPO_ROOT / "docs" / "example.md",
        "Continue with `docs/not-a-real-route.md`.",
    )

    assert errors == ["docs/example.md: broken inline route 'docs/not-a-real-route.md'"]


def test_user_skill_is_a_small_competency_router() -> None:
    skill_root = REPO_ROOT / ".agents" / "skills" / "hop-design-user"
    skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    references = {
        "design.md",
        "discovery.md",
        "methods.md",
        "verification-and-integration.md",
        "views.md",
    }

    assert len(skill.splitlines()) <= 90
    assert "hop_design.spaces" in skill
    assert "substrate space" in skill.lower()
    for name in references:
        assert f"references/{name}" in skill
        assert (skill_root / "references" / name).is_file()


def test_root_agent_router_selects_one_focused_skill() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "Load one skill" in agents
    assert ".agents/skills/hop-design-user/SKILL.md" in agents
    assert ".agents/skills/hop-maintainer/SKILL.md" in agents
    assert len(agents.splitlines()) <= 50


def test_active_docs_do_not_teach_retired_design_schemas_or_route_fields() -> None:
    active_docs = [
        path
        for path in (REPO_ROOT / "docs").rglob("*.md")
        if "architecture/decisions" not in path.as_posix()
    ]
    content = "\n".join(path.read_text(encoding="utf-8") for path in active_docs)

    for retired in (
        "hop.design/v1",
        "hop.resolved-design/v1",
        "hop.plan/v2",
        "hop.resolved-design-space/v1",
        "hop.design-space-plan/v1",
        "hop.basal-candidate-search/v1",
        "hop.basal-processing-route-search-result/v1",
        "hop.hairpin-junction-route-search-result/v1",
        "hop.linear-source-multinick-hairpin-pcr-result/v1",
        "hop.method-bundle/v1",
        "processing_route_ref",
        "resolved_events",
    ):
        assert retired not in content


def test_active_docs_do_not_teach_retired_candidate_ordering() -> None:
    active_text = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "DESIGN.md",
            "docs/reference/mechanics-api.md",
            "docs/reference/python-api.md",
        )
    )

    for retired_claim in (
        "canonical physical record order",
        "Candidate order uses extra-site counts",
        "Candidate order is compact S3/S2/S1/S0 profile",
        "upstream physical ranks",
    ):
        assert retired_claim not in active_text


def test_schema_reference_distinguishes_release_and_source_generations() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        source_version = tomllib.load(handle)["project"]["version"]
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    schemas = (REPO_ROOT / "docs" / "reference" / "schemas.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "guides" / "quickstart.md").read_text(encoding="utf-8")

    match = re.search(r"hop_design-([0-9a-z.]+)-py3-none-any\.whl", quickstart)
    assert match is not None
    published_version = match.group(1)

    if published_version != source_version:
        for text in (readme, schemas, quickstart):
            assert source_version in text
            assert published_version in text
            assert "unreleased" in text
        assert "release-wheel command above uses the a7 contract" in quickstart


def test_every_stable_operation_is_named_in_the_api_reference() -> None:
    reference = "\n".join(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for relative_path in (
            "docs/reference/python-api.md",
            "docs/reference/mechanics-api.md",
            "docs/methods/destination-neutrality.md",
        )
    )

    operations = set(hop_api.__all__)
    operations.update(
        name for name in hop_spaces.__all__ if name.startswith(("compile_", "load_", "preview_"))
    )
    operations.update(
        name
        for name in hop_construction.__all__
        if name.startswith(("compile_", "load_", "project_"))
    )
    operations.update(
        name for name in hop_discovery.__all__ if name.startswith(("classify_", "scan_", "search_"))
    )
    operations.update(
        name
        for name in hop_methods.__all__
        if name.startswith(("compile_", "load_", "resolve_", "verify_"))
    )
    operations.update(name for name in hop_views.__all__ if name.startswith(("build_", "render_")))
    for operation in operations:
        assert f"`{operation}" in reference, operation


def test_public_prose_does_not_use_removed_specialized_root_operations() -> None:
    surfaces = [
        REPO_ROOT / ".agents" / "skills" / "hop-design-user" / "SKILL.md",
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
        *sorted((REPO_ROOT / "examples").glob("*.py")),
        REPO_ROOT / "scripts" / "method-bundle-smoke.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in surfaces)
    specialized_operations = {
        name
        for name in (
            *hop_construction.__all__,
            *hop_discovery.__all__,
            *hop_methods.__all__,
            *hop_views.__all__,
        )
        if name.startswith(
            (
                "build_",
                "classify_",
                "compile_",
                "load_",
                "render_",
                "resolve_",
                "scan_",
                "search_",
                "verify_",
            )
        )
    }

    for operation in specialized_operations:
        assert f"hop.{operation}" not in text, operation


def test_banner_uses_literal_name_and_method_stages() -> None:
    banner = (REPO_ROOT / "assets" / "hop-design-banner.svg").read_text(encoding="utf-8")

    assert 'width="1280" height="260"' in banner
    assert "HAIRPIN OLIGONUCLEOTIDE PROCESSING" in banner
    assert all(color in banner for color in ("#1E1D1A", "#F3EFE7", "#969087", "#D97757"))
    for stage in ("SOURCE", "RELEASE", "FOLDBACK", "INSERT"):
        assert f">{stage}</text>" in banner
    for buzzword in (">SPEC</text>", ">PLAN</text>", ">BUNDLE</text>"):
        assert buzzword not in banner
