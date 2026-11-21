"""Acceptance tests for `gate.py pr-check`, run in a throwaway git repo, in both modes."""

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


def make_repo(tmp_path, lock):
    for rel in ("scripts", "docs/templates"):
        shutil.copytree(REPO / rel, tmp_path / rel)
    (tmp_path / "README.md").write_text("# Project\n")
    (tmp_path / "AGENTS.md").write_text("# Rules\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    if lock:
        (tmp_path / "sdlc.toml").write_text("acceptance_lock = true\n")
    sh(tmp_path, "git", "init", "-q", "-b", "main")
    sh(tmp_path, "git", "add", "-A")
    sh(tmp_path, "git", "commit", "-q", "-m", "base")
    sh(tmp_path, "git", "checkout", "-q", "-b", "pr")
    return tmp_path


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path, lock=False)


@pytest.fixture
def locked(tmp_path):
    return make_repo(tmp_path, lock=True)


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
        # Change 0003: approving a change means approving its intent (with an owner) too.
        intent = repo / "changes" / name / "intent.md"
        intent.write_text(intent.read_text().replace("Status: draft", "Status: approved", 1)
                          .replace("**Owner (human):** @", "**Owner (human):** @owner", 1))
        spec = repo / "changes" / name / "spec.md"
        spec.write_text(spec.read_text().replace("Status: draft", "Status: approved"))
    if lock:
        sh(repo, sys.executable, "scripts/gate.py", "lock", name)
    return name


def merge_approved_change(repo, lock):
    """Put an approved (and, if `lock`, locked) change on main, then start a new PR branch."""
    sh(repo, "git", "checkout", "-q", "main")
    name = add_change(repo, approve=True, lock=lock)
    commit(repo)
    sh(repo, "git", "checkout", "-q", "-b", "pr2")
    return name


# --- both modes -------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_docs_only_passes(mode, request):
    r = request.getfixturevalue(mode)
    (r / "README.md").write_text("# Project\n\nMore words.\n")
    commit(r)
    code, out = pr_check(r)
    assert code == 0 and "docs-only" in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_rule_file_needs_a_change(mode, request):
    r = request.getfixturevalue(mode)
    (r / "AGENTS.md").write_text("# Rules\n\nNew rule.\n")
    commit(r)
    code, out = pr_check(r)
    assert code == 1 and "AGENTS.md" in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_settings_file_is_a_rule_file(mode, request):
    r = request.getfixturevalue(mode)
    (r / "sdlc.toml").write_text("acceptance_lock = false\n# changed\n")
    commit(r)
    code, out = pr_check(r)
    assert code == 1 and "sdlc.toml" in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_evals_are_rule_files(mode, request):
    r = request.getfixturevalue(mode)
    (r / "evals").mkdir()
    (r / "evals" / "case.md").write_text("# Case\n")
    commit(r)
    code, out = pr_check(r)
    assert code == 1 and "evals/case.md" in out and "docs-only" not in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_code_needs_a_change(mode, request):
    r = request.getfixturevalue(mode)
    (r / "src" / "app.py").write_text("x = 2\n")
    commit(r)
    code, out = pr_check(r)
    assert code == 1 and "changes/" in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_draft_change_does_not_merge(mode, request):
    r = request.getfixturevalue(mode)
    (r / "src" / "app.py").write_text("x = 2\n")
    add_change(r)
    commit(r)
    code, out = pr_check(r)
    assert code == 1 and "0001-thing" in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_mixed_docs_and_rules(mode, request):
    r = request.getfixturevalue(mode)
    (r / "README.md").write_text("# Project\n\nMore words.\n")
    (r / "docs" / "templates" / "plan.md").write_text("# Plan\n")
    commit(r)
    code, out = pr_check(r)
    assert code == 1 and "docs-only" not in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_empty_pr_passes(mode, request):
    assert pr_check(request.getfixturevalue(mode))[0] == 0


# --- lock off (default) -----------------------------------------------------------------

def test_off_approved_change_passes_without_lock(repo):
    (repo / "src" / "app.py").write_text("x = 2\n")
    add_change(repo, approve=True)
    commit(repo)
    code, out = pr_check(repo)
    assert code == 0 and "lock off" in out


def test_off_editing_approved_tests_warns(repo):
    name = merge_approved_change(repo, lock=False)
    (repo / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    pass\n")
    plan = repo / "changes" / name / "plan.md"
    plan.write_text(plan.read_text() + "\nTests adjusted.\n")
    commit(repo)
    code, out = pr_check(repo)
    assert code == 0
    assert "::warning::" in out and name in out and "already approved" in out


# --- lock on (VibeOps experiment) -------------------------------------------------------

def test_on_approved_locked_change_passes(locked):
    (locked / "src" / "app.py").write_text("x = 2\n")
    add_change(locked, approve=True, lock=True)
    commit(locked)
    assert pr_check(locked)[0] == 0


def test_on_approved_without_lock_fails(locked):
    (locked / "src" / "app.py").write_text("x = 2\n")
    add_change(locked, approve=True)
    commit(locked)
    code, out = pr_check(locked)
    assert code == 1 and "not locked" in out


def test_on_unlocked_change_fails(locked):
    (locked / "src" / "app.py").write_text("x = 2\n")
    name = add_change(locked, approve=True, lock=True)
    (locked / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    pass\n")
    commit(locked)
    code, out = pr_check(locked)
    assert code == 1 and name in out


def test_on_editing_approved_tests_fails(locked):
    name = merge_approved_change(locked, lock=True)
    (locked / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    pass\n")
    plan = locked / "changes" / name / "plan.md"
    plan.write_text(plan.read_text() + "\nTests adjusted.\n")
    commit(locked)
    code, out = pr_check(locked)
    assert code == 1 and "already approved" in out


# --- the edit log (committed, append-only) ----------------------------------------------

LOG = ".sdlc/acceptance-edits.jsonl"


def write_log(repo, lines):
    path = repo / LOG
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(line + "\n" for line in lines))


def test_edit_log_entries_are_repeated_as_warnings(repo):
    name = merge_approved_change(repo, lock=False)
    (repo / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    pass\n")
    plan = repo / "changes" / name / "plan.md"
    plan.write_text(plan.read_text() + "\nTests adjusted.\n")
    write_log(repo, ['{"tool": "Edit", "change": "0001-thing", "kind": "approved-test"}'])
    commit(repo)
    code, out = pr_check(repo)
    assert code == 0
    assert "logged in .sdlc/acceptance-edits.jsonl" in out and '"tool": "Edit"' in out


def test_removing_edit_log_lines_warns(repo):
    sh(repo, "git", "checkout", "-q", "main")
    write_log(repo, ['{"entry": 1}', '{"entry": 2}'])
    commit(repo)
    sh(repo, "git", "checkout", "-q", "-b", "pr2")
    write_log(repo, ['{"entry": 1}'])
    add_change(repo, approve=True)
    commit(repo)
    code, out = pr_check(repo)
    assert "removed from .sdlc/acceptance-edits.jsonl" in out and "append-only" in out


def test_edit_log_is_not_docs(repo):
    write_log(repo, ['{"entry": 1}'])
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and "docs-only" not in out
