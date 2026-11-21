"""Acceptance tests for `gate.py pr-check`, run in a throwaway git repo."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def sh(repo, *args):
    return subprocess.run(args, cwd=repo, capture_output=True, text=True, env=GIT_ENV)


@pytest.fixture
def repo(tmp_path):
    for rel in ("scripts", "docs/templates"):
        shutil.copytree(REPO / rel, tmp_path / rel)
    (tmp_path / "README.md").write_text("# Project\n")
    (tmp_path / "AGENTS.md").write_text("# Rules\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    sh(tmp_path, "git", "init", "-q", "-b", "main")
    sh(tmp_path, "git", "add", "-A")
    sh(tmp_path, "git", "commit", "-q", "-m", "base")
    sh(tmp_path, "git", "checkout", "-q", "-b", "pr")
    return tmp_path


def commit(repo):
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "-m", "pr")


def pr_check(repo):
    p = sh(repo, sys.executable, "scripts/gate.py", "pr-check", "main")
    return p.returncode, p.stdout + p.stderr


def add_change(repo, approve=False, lock=False):
    sh(repo, sys.executable, "scripts/gate.py", "new", "thing")
    name = "0001-thing"
    (repo / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    assert True\n")
    if approve:
        spec = repo / "changes" / name / "spec.md"
        spec.write_text(spec.read_text().replace("Status: draft", "Status: approved"))
    if lock:
        sh(repo, sys.executable, "scripts/gate.py", "lock", name)
    return name


def test_docs_only_passes(repo):
    (repo / "README.md").write_text("# Project\n\nMore words.\n")
    commit(repo)
    code, out = pr_check(repo)
    assert code == 0 and "docs-only" in out


def test_rule_file_needs_a_change(repo):
    (repo / "AGENTS.md").write_text("# Rules\n\nNew rule.\n")
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and "AGENTS.md" in out


def test_code_needs_a_change(repo):
    (repo / "src" / "app.py").write_text("x = 2\n")
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and "changes/" in out


def test_draft_change_does_not_merge(repo):
    (repo / "src" / "app.py").write_text("x = 2\n")
    add_change(repo)
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and "0001-thing" in out


def test_approved_locked_change_passes(repo):
    (repo / "src" / "app.py").write_text("x = 2\n")
    add_change(repo, approve=True, lock=True)
    commit(repo)
    assert pr_check(repo)[0] == 0


def test_unlocked_change_fails(repo):
    (repo / "src" / "app.py").write_text("x = 2\n")
    name = add_change(repo, approve=True, lock=True)
    (repo / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    pass\n")
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and name in out


def test_mixed_docs_and_rules(repo):
    (repo / "README.md").write_text("# Project\n\nMore words.\n")
    (repo / "docs" / "templates" / "plan.md").write_text("# Plan\n")
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and "docs-only" not in out


def test_empty_pr_passes(repo):
    assert pr_check(repo)[0] == 0
