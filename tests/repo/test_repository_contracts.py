from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import yaml

import hop_design as hop
import hop_design.discovery as hop_discovery
import hop_design.methods as hop_methods
import hop_design.views as hop_views
from hop_design import api as hop_api

REPO_ROOT = Path(__file__).resolve().parents[2]
FULL_SHA_ACTION = re.compile(r"^\s*uses:\s*[^\s@]+@[0-9a-f]{40}(?:\s+#.*)?$", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*[^\s]+(?:\s+#.*)?$", re.MULTILINE)
FULL_SHA_PRECOMMIT = re.compile(r"^\s*rev:\s*[0-9a-f]{40}(?:\s+#.*)?$", re.MULTILINE)
ANY_PRECOMMIT_REV = re.compile(r"^\s*rev:\s*[^\s]+(?:\s+#.*)?$", re.MULTILINE)


def _load_docs_checker() -> ModuleType:
    path = REPO_ROOT / "scripts" / "check_docs.py"
    spec = importlib.util.spec_from_file_location("hop_check_docs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workflow(name: str) -> tuple[dict[str, object], str]:
    path = REPO_ROOT / ".github" / "workflows" / name
    text = path.read_text(encoding="utf-8")
    parsed = yaml.load(text, Loader=yaml.BaseLoader)
    assert isinstance(parsed, dict)
    return parsed, text


def test_public_landing_page_routes_without_becoming_a_manual() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# ![hop — Hairpin Oligonucleotide Processing")
    assert "assets/hop-design-banner.svg" in readme
    assert "CONTRIBUTING.md" in readme
    assert "SECURITY.md" in readme
    assert "docs/index.md" in readme
    assert len(readme.splitlines()) <= 100


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

    mechanics = (REPO_ROOT / "docs" / "reference" / "mechanics-api.md").read_text(encoding="utf-8")
    assert "sequence-and-cut compatible" in mechanics
    assert "empirical cleavage efficiency" in mechanics


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
        "examples/compile_payload_library.py",
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


def test_public_payload_library_example_executes(tmp_path: Path) -> None:
    output = tmp_path / "payload-library"
    completed = subprocess.run(
        [
            sys.executable,
            "examples/compile_payload_library.py",
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["schema"] == "hop.payload-library-compilation/v1"
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
            "examples/compile_payload_library.py",
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
        {"metadata": "version: 1"},
    )

    assert errors == [".agents/skills/example/SKILL.md: metadata must be a YAML mapping"]


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
    for name in references:
        assert f"references/{name}" in skill
        assert (skill_root / "references" / name).is_file()


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

    match = re.search(r"hop_design-([0-9a-z.]+)-py3-none-any\.whl", readme)
    assert match is not None
    published_version = match.group(1)

    if published_version != source_version:
        for text in (readme, schemas, quickstart):
            assert source_version in text
            assert published_version in text
            assert "unreleased" in text
        assert "release-wheel command above uses the a6 contract" in quickstart


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


def test_distribution_metadata_keeps_pypi_brake_but_names_public_home() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    project = config["project"]
    assert "Private :: Do Not Upload" in project["classifiers"]
    assert project["urls"] == {
        "Documentation": "https://github.com/e-south/hop-design/tree/main/docs",
        "Issues": "https://github.com/e-south/hop-design/issues",
        "Repository": "https://github.com/e-south/hop-design",
    }
    assert config["tool"]["uv"]["required-version"] == ">=0.12.3,<0.13"
    assert config["tool"]["coverage"]["report"] == {
        "fail_under": 90,
        "precision": 2,
        "show_missing": True,
        "skip_covered": True,
    }
    dev_dependencies = "\n".join(config["dependency-groups"]["dev"])
    for dependency in ("pip-audit", "pre-commit", "twine"):
        assert dependency in dev_dependencies


def test_ci_has_one_stable_required_context_and_supported_python_probe() -> None:
    workflow, text = _workflow("ci.yaml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    assert set(jobs) == {"verify", "python-compatibility", "checks"}
    assert jobs["checks"]["name"] == "Checks"
    assert set(jobs["checks"]["needs"]) == {"verify", "python-compatibility"}
    assert jobs["python-compatibility"]["strategy"]["matrix"]["python-version"] == [
        "3.12",
        "3.13",
        "3.14",
    ]
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in text


def test_workflows_use_immutable_actions_and_bounded_permissions() -> None:
    for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        action_lines = ANY_ACTION.findall(text)
        assert action_lines, f"{path.name} must use at least one action"
        assert len(FULL_SHA_ACTION.findall(text)) == len(action_lines), (
            f"{path.name} contains an action that is not pinned to a full commit SHA"
        )
        assert "permissions:" in text
        assert "pull_request_target" not in text


def test_dependency_review_is_a_separate_required_signal() -> None:
    workflow, text = _workflow("dependency-review.yaml")

    assert workflow["on"] == {"pull_request": ""}
    assert workflow["permissions"] == {"contents": "read"}
    assert "name: Dependency review" in text
    assert "fail-on-severity: moderate" in text


def test_codeql_is_a_reproducible_required_signal() -> None:
    workflow, text = _workflow("codeql.yaml")

    assert workflow["name"] == "CodeQL"
    assert workflow["on"] == {
        "pull_request": {"branches": ["main"]},
        "push": {"branches": ["main"]},
        "schedule": [{"cron": "17 6 * * 1"}],
    }
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert set(jobs) == {"analyze"}
    assert jobs["analyze"]["name"] == "CodeQL"
    assert jobs["analyze"]["permissions"] == {
        "contents": "read",
        "security-events": "write",
    }
    assert "github/codeql-action/init@" in text
    assert "github/codeql-action/analyze@" in text
    assert "languages: python" in text
    assert "queries: security-extended" in text


def test_release_workflow_verifies_before_publishing_and_cannot_publish_to_pypi() -> None:
    workflow, text = _workflow("release.yaml")

    assert workflow["on"] == {"push": {"tags": ["v*"]}}
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert set(jobs) == {"build", "publish"}
    assert jobs["publish"]["needs"] == "build"
    assert jobs["publish"]["permissions"] == {
        "actions": "read",
        "contents": "write",
    }
    assert jobs["publish"]["env"] == {"GH_REPO": "${{ github.repository }}"}
    assert "id-token: write" not in text
    assert "gh-action-pypi-publish" not in text
    assert "release:" not in text
    assert "git merge-base --is-ancestor" in text
    assert "uv build --no-sources" in text
    assert "scripts/wheel-smoke dist" in text
    assert "sha256sum *.whl *.tar.gz > SHA256SUMS" in text
    assert "actions/upload-artifact" in text
    assert "retention-days: 1" in text
    assert "gh release create" in text
    assert '"${GITHUB_REF_NAME}" dist/*' in text
    assert "--verify-tag" in text
    assert "--generate-notes" in text
    assert "gh release upload" not in text
    assert "--clobber" not in text


def test_source_distribution_includes_readme_routed_public_content() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    includes = set(config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])
    assert {
        "/ARCHITECTURE.md",
        "/CONTRIBUTING.md",
        "/DESIGN.md",
        "/RELIABILITY.md",
        "/SECURITY.md",
        "/assets",
        "/docs",
        "/examples",
    } <= includes


def test_dependabot_and_precommit_cover_declared_supply_chain() -> None:
    dependabot = yaml.safe_load(
        (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    )
    ecosystems = {entry["package-ecosystem"] for entry in dependabot["updates"]}
    assert ecosystems == {"uv", "github-actions", "pre-commit"}

    precommit = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert len(FULL_SHA_PRECOMMIT.findall(precommit)) == len(ANY_PRECOMMIT_REV.findall(precommit))
    for hook in (
        "check-github-workflows",
        "detect-private-key",
        "detect-secrets",
        "ruff-check",
        "ruff-format",
        "uv-lock",
    ):
        assert f"id: {hook}" in precommit


def test_public_example_is_a_real_strict_spec() -> None:
    example = REPO_ROOT / "examples" / "generic-symbolic.yaml"

    spec = hop.load_spec(example)
    compilation = hop.compile(spec)

    assert compilation.spec.design_id == "example-symbolic"
    assert compilation.plan.payload_sequence == "NRY"


def test_readme_and_quickstart_use_real_inputs_and_distinct_outputs() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "guides" / "quickstart.md").read_text(encoding="utf-8")
    release_match = re.search(r"hop_design-([0-9a-z.]+)-py3-none-any\.whl", readme)
    assert release_match is not None
    wheel_name = release_match.group(0)

    assert 'compilation.write("build/demo-python")' in readme
    assert "--spec examples/generic-symbolic.yaml" in quickstart
    assert 'compilation.write("build/symbolic-python")' in quickstart
    assert wheel_name in readme
    assert wheel_name in quickstart
    checksum_command = f"grep '{wheel_name}$' SHA256SUMS | shasum -a 256 -c -"
    assert checksum_command in readme
    assert checksum_command in quickstart


def test_governance_and_release_routes_exist() -> None:
    expected_paths = (
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        ".github/CODEOWNERS",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
        "docs/dev/README.md",
        "docs/dev/github-governance.md",
        "docs/dev/releasing.md",
    )

    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_public_roadmap_distinguishes_release_and_candidate_lines() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    roadmap = (REPO_ROOT / "docs" / "dev" / "plans" / "roadmap.md").read_text(encoding="utf-8")

    assert "public `v0.1.0a6` artifact" in roadmap
    assert f"candidate is `v{version}`" in roadmap
    assert "Research Studies" not in roadmap
    assert "billing" not in roadmap.lower()


def test_source_layout_has_explicit_sprawl_limits() -> None:
    source_root = REPO_ROOT / "src" / "hop_design"
    package_dirs = [source_root, *sorted(path for path in source_root.rglob("*") if path.is_dir())]

    for directory in package_dirs:
        modules = list(directory.glob("*.py"))
        assert len(modules) <= 25, f"{directory.relative_to(REPO_ROOT)} has too many flat modules"
        for module in modules:
            line_count = len(module.read_text(encoding="utf-8").splitlines())
            assert line_count <= 350, f"{module.relative_to(REPO_ROOT)} is a monolith"
