"""Tests for scripts/gate.py and the Claude Code hook, run against a throwaway copy."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def repo(tmp_path):
    for rel in ("scripts", "docs/templates", ".claude"):
        shutil.copytree(REPO / rel, tmp_path / rel)
    return tmp_path


def gate(repo, *args):
    p = subprocess.run([sys.executable, "scripts/gate.py", *args], cwd=repo, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def hook(repo, tool, **tool_input):
    event = json.dumps({"tool_name": tool, "tool_input": tool_input})
    p = subprocess.run(
        [sys.executable, ".claude/hooks/protect_acceptance.py"],
        cwd=repo, input=event, capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": ""},
    )
    return p.returncode, p.stderr


def new_change(repo, slug="greet", test="def test_ok():\n    assert True\n"):
    assert gate(repo, "new", slug)[0] == 0
    name = next(p.name for p in (repo / "changes").iterdir() if p.name.endswith(slug))
    (repo / "tests" / "acceptance" / name / "test_it.py").write_text(test)
    return name


def approve(repo, name):
    spec = repo / "changes" / name / "spec.md"
    spec.write_text(spec.read_text().replace("Status: draft", "Status: approved"))


def test_new_scaffolds_numbered_change(repo):
    assert gate(repo, "new", "export-csv")[0] == 0
    assert gate(repo, "new", "import-csv")[0] == 0
    names = sorted(p.name for p in (repo / "changes").iterdir())
    assert names == ["0001-export-csv", "0002-import-csv"]
    assert "Spec: 0001-export-csv" in (repo / "changes" / names[0] / "spec.md").read_text()
    assert (repo / "tests" / "acceptance" / names[0]).is_dir()
    assert gate(repo, "new", "Bad Slug")[0] == 2


def test_draft_passes_check(repo):
    new_change(repo)
    code, out = gate(repo, "check")
    assert code == 0 and "draft" in out


def test_missing_intent_fails(repo):
    name = new_change(repo)
    (repo / "changes" / name / "intent.md").unlink()
    code, out = gate(repo, "check")
    assert code == 1 and "missing intent.md" in out


def test_approved_without_lock_fails_then_lock_passes(repo):
    name = new_change(repo)
    approve(repo, name)
    code, out = gate(repo, "check")
    assert code == 1 and "not locked" in out
    assert gate(repo, "lock", "greet")[0] == 0
    assert gate(repo, "check")[0] == 0


def test_lock_refuses_a_draft(repo):
    new_change(repo)
    code, out = gate(repo, "lock", "greet")
    assert code == 1 and "approved" in out


def test_changed_acceptance_test_fails_the_gate(repo):
    name = new_change(repo)
    approve(repo, name)
    gate(repo, "lock", name)
    (repo / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    pass\n")
    code, out = gate(repo, "check")
    assert code == 1 and "changed since they were locked" in out


def test_added_acceptance_file_fails_the_gate(repo):
    name = new_change(repo)
    approve(repo, name)
    gate(repo, "lock", name)
    (repo / "tests" / "acceptance" / name / "test_extra.py").write_text("def test_x():\n    assert True\n")
    assert gate(repo, "check")[0] == 1


def test_approved_without_plan_or_tests_fails(repo):
    name = new_change(repo)
    approve(repo, name)
    (repo / "changes" / name / "plan.md").unlink()
    (repo / "tests" / "acceptance" / name / "test_it.py").unlink()
    code, out = gate(repo, "check")
    assert "no plan.md" in out and "has no tests" in out and code == 1


def test_test_runs_only_approved_changes(repo):
    name = new_change(repo, test="def test_fails():\n    assert False\n")
    code, out = gate(repo, "test")
    assert code == 0 and "No approved changes" in out  # drafts are expected to fail
    approve(repo, name)
    assert gate(repo, "test")[0] != 0


def test_hook_allows_drafting_acceptance_tests(repo):
    name = new_change(repo)
    code, _ = hook(repo, "Write", file_path=str(repo / "tests" / "acceptance" / name / "test_it.py"))
    assert code == 0


def test_hook_blocks_edits_to_approved_acceptance_tests(repo):
    name = new_change(repo)
    approve(repo, name)
    code, err = hook(repo, "Edit", file_path=f"tests/acceptance/{name}/test_it.py")
    assert code == 2 and "approved" in err


def test_hook_blocks_lock_file_and_lock_command(repo):
    name = new_change(repo)
    assert hook(repo, "Write", file_path=str(repo / "changes" / name / "acceptance.lock"))[0] == 2
    assert hook(repo, "Bash", command=f"python scripts/gate.py lock {name}")[0] == 2
    assert hook(repo, "Bash", command=f"echo x > changes/{name}/acceptance.lock")[0] == 2


def test_hook_blocks_shell_writes_to_approved_tests_only(repo):
    name = new_change(repo)
    assert hook(repo, "Bash", command=f"rm tests/acceptance/{name}/test_it.py")[0] == 0
    approve(repo, name)
    assert hook(repo, "Bash", command=f"rm tests/acceptance/{name}/test_it.py")[0] == 2
    assert hook(repo, "Bash", command=f"cat tests/acceptance/{name}/test_it.py")[0] == 0


def test_hook_ignores_other_files_and_bad_input(repo):
    assert hook(repo, "Edit", file_path="src/app.py")[0] == 0
    p = subprocess.run(
        [sys.executable, ".claude/hooks/protect_acceptance.py"], cwd=repo, input="not json",
        capture_output=True, text=True, env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": ""},
    )
    assert p.returncode == 0


def test_the_real_repo_passes_its_own_gate():
    p = subprocess.run([sys.executable, "scripts/gate.py", "check"], cwd=REPO, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout
