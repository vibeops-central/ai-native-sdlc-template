"""Acceptance tests for change 0003: deleted change folders and intent approval."""

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


def gate(repo, *args):
    p = sh(repo, sys.executable, "scripts/gate.py", *args)
    return p.returncode, p.stdout + p.stderr


@pytest.fixture
def repo(tmp_path):
    for rel in ("scripts", "docs/templates"):
        shutil.copytree(REPO / rel, tmp_path / rel)
    (tmp_path / "README.md").write_text("# Project\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    sh(tmp_path, "git", "init", "-q", "-b", "main")
    commit(tmp_path, "base")
    sh(tmp_path, "git", "checkout", "-q", "-b", "pr")
    return tmp_path


def commit(repo, message="change"):
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "-m", message)


def set_status(path, status):
    text = path.read_text()
    text = text.replace("Status: draft", f"Status: {status}")
    path.write_text(text)


def set_owner(intent, owner):
    lines = intent.read_text().splitlines()
    lines = [f"**Owner (human):** {owner}" if line.startswith("**Owner (human):**") else line for line in lines]
    intent.write_text("\n".join(lines) + "\n")


def add_change(repo, slug, approve=False, intent_approved=None, owner="@natu"):
    """Create a change. By default the intent is approved whenever the spec is."""
    gate(repo, "new", slug)
    name = next(p.name for p in (repo / "changes").iterdir() if p.name.endswith("-" + slug))
    (repo / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    assert True\n")
    intent = repo / "changes" / name / "intent.md"
    set_owner(intent, owner)
    if approve:
        set_status(repo / "changes" / name / "spec.md", "approved")
    if intent_approved if intent_approved is not None else approve:
        set_status(intent, "approved")
    return name


def pr_check(repo):
    return gate(repo, "pr-check", "main")


# --- 1. deleted change folders ----------------------------------------------------------

def merge_old_change(repo):
    sh(repo, "git", "checkout", "-q", "main")
    name = add_change(repo, "old", approve=True)
    commit(repo, "old change")
    sh(repo, "git", "checkout", "-q", "-b", "pr2")
    return name


def test_deleted_change_folder_does_not_count(repo):
    name = merge_old_change(repo)
    shutil.rmtree(repo / "changes" / name)
    (repo / "src" / "app.py").write_text("x = 2\n")
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and "deleted folders don't count" in out


def test_deleted_folder_with_another_approved_change_passes(repo):
    name = merge_old_change(repo)
    shutil.rmtree(repo / "changes" / name)
    (repo / "src" / "app.py").write_text("x = 2\n")
    add_change(repo, "new", approve=True)
    commit(repo)
    code, out = pr_check(repo)
    assert code == 0, out


def test_only_deleting_a_change_folder_needs_a_change(repo):
    name = merge_old_change(repo)
    shutil.rmtree(repo / "changes" / name)
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and "docs-only" not in out


# --- 2. intent approval -----------------------------------------------------------------

def test_new_change_intent_starts_as_draft(repo):
    gate(repo, "new", "thing")
    intent = (repo / "changes" / "0001-thing" / "intent.md").read_text()
    assert "Status: draft" in intent


def test_approved_spec_needs_approved_intent(repo):
    name = add_change(repo, "thing", approve=True, intent_approved=False)
    code, out = gate(repo, "check")
    assert code == 1 and name in out and "intent" in out


def test_approved_intent_needs_an_owner(repo):
    add_change(repo, "thing", approve=True, owner="@")
    code, out = gate(repo, "check")
    assert code == 1 and "owner" in out.lower()


def test_approved_intent_and_spec_pass(repo):
    add_change(repo, "thing", approve=True)
    code, out = gate(repo, "check")
    assert code == 0, out


def test_draft_spec_does_not_need_approved_intent(repo):
    add_change(repo, "thing")
    assert gate(repo, "check")[0] == 0


def test_pr_check_needs_approved_intent(repo):
    (repo / "src" / "app.py").write_text("x = 2\n")
    name = add_change(repo, "thing", approve=True, intent_approved=False)
    commit(repo)
    code, out = pr_check(repo)
    assert code == 1 and name in out and "intent" in out
