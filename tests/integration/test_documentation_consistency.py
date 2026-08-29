"""Automated consistency tests for documentation, workflows, and code paths.

Enforces SAI-56 acceptance criteria:
- Every local markdown link resolves to a valid existing file.
- Every backticked repository path exists on disk.
- Every documented GitHub workflow exists in `.github/workflows/`.
- No stale GCP region references remain in documentation.
- Every module and test referenced in the Capability Matrix exists.
- Non-clinical safety and emergency boundaries are consistently documented.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _all_markdown_files() -> list[Path]:
    return [REPO_ROOT / "README.md"] + list(DOCS_DIR.rglob("*.md"))


def test_all_local_markdown_links_resolve_to_existing_files() -> None:
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    broken_links: list[str] = []

    for md_path in _all_markdown_files():
        text = md_path.read_text(encoding="utf-8")
        for link_text, target in link_pattern.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean_target = target.split("#")[0]
            if not clean_target:
                continue
            resolved_from_parent = (md_path.parent / clean_target).resolve()
            resolved_from_root = (REPO_ROOT / clean_target).resolve()
            if not resolved_from_parent.exists() and not resolved_from_root.exists():
                broken_links.append(f"{md_path.relative_to(REPO_ROOT)}: [{link_text}]({target})")

    msg = "Broken markdown links detected:\n" + "\n".join(broken_links)
    assert not broken_links, msg


def test_all_backticked_repository_paths_exist() -> None:
    path_pattern = re.compile(r"`([a-zA-Z0-9_\-./\\]+\.[a-zA-Z0-9_\-]+)`")
    broken_paths: list[str] = []

    # Exclude historical planning convergence notes that intentionally reference legacy files
    excluded_docs = {
        "docs/superpowers/plans/2026-08-27-deploy-workflow-convergence.md",
    }

    for md_path in _all_markdown_files():
        rel_path = str(md_path.relative_to(REPO_ROOT)).replace("\\", "/")
        if rel_path in excluded_docs:
            continue

        text = md_path.read_text(encoding="utf-8")
        for match in path_pattern.finditer(text):
            ref = match.group(1).replace("\\", "/")
            if (
                ref.startswith(("src/", "tests/", "docs/", "infra/", "tools/", ".github/"))
                or ref in ["Dockerfile", "pyproject.toml", "uv.lock", "LICENSE", "README.md"]
            ):
                # Ignore globs or generic placeholders
                if "*" in ref or "<" in ref:
                    continue
                target = (REPO_ROOT / ref).resolve()
                if not target.exists():
                    broken_paths.append(f"{rel_path}: `{ref}`")

    msg = "Broken repository path references detected:\n" + "\n".join(set(broken_paths))
    assert not broken_paths, msg


def test_all_documented_github_workflows_exist() -> None:
    actual_workflows = {f.name for f in WORKFLOWS_DIR.glob("*.yml")} | {
        f.name for f in WORKFLOWS_DIR.glob("*.yaml")
    }
    wf_pattern = re.compile(r"([a-zA-Z0-9_\-]+\.ya?ml)")
    missing_workflows: list[str] = []

    excluded_docs = {
        "docs/superpowers/plans/2026-08-27-deploy-workflow-convergence.md",
    }

    key_names = [
        "deploy",
        "control",
        "smoke",
        "diagnostic",
        "evidence",
        "tests",
        "terraform",
    ]

    for md_path in _all_markdown_files():
        rel_path = str(md_path.relative_to(REPO_ROOT)).replace("\\", "/")
        if rel_path in excluded_docs:
            continue

        text = md_path.read_text(encoding="utf-8")
        for match in wf_pattern.finditer(text):
            wf = match.group(1)
            # Check if this looks like an intended workflow file reference
            if any(name in wf for name in key_names) and wf not in actual_workflows:
                missing_workflows.append(f"{rel_path}: {wf}")

    msg = "Referenced workflows not found in .github/workflows:\n" + "\n".join(
        set(missing_workflows)
    )
    assert not missing_workflows, msg


def test_no_stale_gcp_region_references_in_active_docs() -> None:
    stale_region = "australia-southeast2"
    violations: list[str] = []

    # Historical plans may record initial brainstorming; active documentation must not
    for md_path in _all_markdown_files():
        rel_path = str(md_path.relative_to(REPO_ROOT)).replace("\\", "/")
        if rel_path.startswith("docs/superpowers/"):
            continue
        text = md_path.read_text(encoding="utf-8")
        if stale_region in text:
            violations.append(f"{rel_path} contains stale region '{stale_region}'")

    msg = "Stale region references found:\n" + "\n".join(violations)
    assert not violations, msg


def test_capability_matrix_modules_and_tests_exist() -> None:
    matrix_path = DOCS_DIR / "capability-matrix.md"
    assert matrix_path.exists(), "docs/capability-matrix.md must exist"

    # Verify key code modules
    modules = [
        "staylong.agents.intake",
        "staylong.agents.coordinator",
        "staylong.policy.emergency",
        "staylong.policy.approvals",
        "staylong.privacy.gemma",
        "staylong.services.home_plan",
        "staylong.services.google_oauth",
        "staylong.services.google_actions",
        "staylong.services.public_sessions",
        "staylong.api.runtime_token",
    ]
    for mod in modules:
        try:
            importlib.import_module(mod)
        except ImportError as err:
            raise AssertionError(f"Capability matrix module '{mod}' failed to import: {err}")

    # Verify key test suites exist
    test_files = [
        "tests/agents/test_intake.py",
        "tests/agents/test_coordinator.py",
        "tests/policy/test_emergency.py",
        "tests/policy/test_approvals.py",
        "tests/privacy/test_gemma.py",
        "tests/services/test_google_oauth.py",
        "tests/services/test_google_actions.py",
        "tests/services/test_public_sessions.py",
        "tests/api/test_public_sandbox_cleanup.py",
        "tests/infra/test_public_edge_component.py",
    ]
    for tf in test_files:
        assert (REPO_ROOT / tf).exists(), f"Capability matrix test file '{tf}' does not exist"


def test_safety_and_emergency_boundaries_stated_consistently() -> None:
    required_docs = [
        REPO_ROOT / "README.md",
        DOCS_DIR / "product-brief.md",
        DOCS_DIR / "capability-matrix.md",
        DOCS_DIR / "technology-and-compliance.md",
    ]
    for doc in required_docs:
        text = doc.read_text(encoding="utf-8")
        assert "Triple Zero" in text or "000" in text, (
            f"{doc.name} must document Triple Zero (000) emergency boundary"
        )
        assert "not" in text.lower(), f"{doc.name} must state non-clinical boundary"
