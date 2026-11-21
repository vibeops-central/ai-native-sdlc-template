"""Tests for scripts/gate.py and the Claude Code hook, run against a throwaway copy.

`repo` uses the default mode (acceptance lock off, Anthropic's playbook as written).
`locked` turns the acceptance lock on (the VibeOps experiment).
"""

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


@pytest.fixture
def locked(repo):
    (repo / "sdlc.toml").write_text("acceptance_lock = true\n")
    return repo


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


def edit_log(repo):
    log = repo / ".sdlc" / "acceptance-edits.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


# --- both modes -------------------------------------------------------------------------

def test_default_mode_is_playbook(repo):
    code, out = gate(repo, "check")
    assert code == 0 and "playbook (acceptance lock off)" in out


def test_bad_settings_file_means_lock_off(repo):
    (repo / "sdlc.toml").write_text("acceptance_lock = = nonsense")
    assert "lock off" in gate(repo, "check")[1]


def test_new_scaffolds_numbered_change(repo):
    assert gate(repo, "new", "export-csv")[0] == 0
    assert gate(repo, "new", "import-csv")[0] == 0
    names = sorted(p.name for p in (repo / "changes").iterdir())
    assert names == ["0001-export-csv", "0002-import-csv"]
    assert "Spec: 0001-export-csv" in (repo / "changes" / names[0] / "spec.md").read_text()
    assert (repo / "tests" / "acceptance" / names[0]).is_dir()
    assert gate(repo, "new", "Bad Slug")[0] == 2


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_draft_passes_check(mode, request):
    r = request.getfixturevalue(mode)
    new_change(r)
    code, out = gate(r, "check")
    assert code == 0 and "draft" in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_missing_intent_fails(mode, request):
    r = request.getfixturevalue(mode)
    name = new_change(r)
    (r / "changes" / name / "intent.md").unlink()
    code, out = gate(r, "check")
    assert code == 1 and "missing intent.md" in out


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_approved_without_plan_or_tests_fails(mode, request):
    r = request.getfixturevalue(mode)
    name = new_change(r)
    approve(r, name)
    (r / "changes" / name / "plan.md").unlink()
    (r / "tests" / "acceptance" / name / "test_it.py").unlink()
    code, out = gate(r, "check")
    assert "no plan.md" in out and "has no tests" in out and code == 1


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_test_runs_only_approved_changes(mode, request):
    r = request.getfixturevalue(mode)
    name = new_change(r, test="def test_fails():\n    assert False\n")
    code, out = gate(r, "test")
    assert code == 0 and "No approved changes" in out  # drafts are expected to fail
    approve(r, name)
    assert gate(r, "test")[0] != 0


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_hook_allows_drafting_acceptance_tests(mode, request):
    r = request.getfixturevalue(mode)
    name = new_change(r)
    code, _ = hook(r, "Write", file_path=str(r / "tests" / "acceptance" / name / "test_it.py"))
    assert code == 0 and edit_log(r) == []


@pytest.mark.parametrize("mode", ["repo", "locked"])
def test_hook_ignores_other_files_and_bad_input(mode, request):
    r = request.getfixturevalue(mode)
    assert hook(r, "Edit", file_path="src/app.py")[0] == 0
    p = subprocess.run(
        [sys.executable, ".claude/hooks/protect_acceptance.py"], cwd=r, input="not json",
        capture_output=True, text=True, env={"CLAUDE_PROJECT_DIR": str(r), "PATH": ""},
    )
    assert p.returncode == 0


def test_the_real_repo_passes_its_own_gate():
    p = subprocess.run([sys.executable, "scripts/gate.py", "check"], cwd=REPO, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout


# --- lock off (default): warn and log ---------------------------------------------------

def test_off_approved_without_lock_passes(repo):
    name = new_change(repo)
    approve(repo, name)
    assert gate(repo, "check")[0] == 0


def test_off_lock_command_is_disabled(repo):
    name = new_change(repo)
    approve(repo, name)
    code, out = gate(repo, "lock", name)
    assert code == 1 and "lock is off" in out
    assert not (repo / "changes" / name / "acceptance.lock").exists()


def test_off_stale_lock_file_only_warns(repo):
    name = new_change(repo)
    approve(repo, name)
    (repo / "changes" / name / "acceptance.lock").write_text("sha256: not-the-real-hash\n")
    code, out = gate(repo, "check")
    assert code == 0 and "::warning::" in out and name in out


def test_off_hook_allows_and_logs_edits_to_approved_tests(repo):
    name = new_change(repo)
    approve(repo, name)
    code, err = hook(repo, "Edit", file_path=f"tests/acceptance/{name}/test_it.py")
    assert code == 0 and "logged" in err
    code, _ = hook(repo, "Bash", command=f"rm tests/acceptance/{name}/test_it.py")
    assert code == 0
    entries = edit_log(repo)
    assert [e["tool"] for e in entries] == ["Edit", "Bash"]
    assert all(e["change"] == name and e["kind"] == "approved-test" for e in entries)


def test_off_hook_does_not_log_reads(repo):
    name = new_change(repo)
    approve(repo, name)
    assert hook(repo, "Bash", command=f"cat tests/acceptance/{name}/test_it.py")[0] == 0
    assert edit_log(repo) == []


# --- lock on (VibeOps experiment): block ------------------------------------------------

def test_on_mode_is_reported(locked):
    assert "acceptance lock ON" in gate(locked, "check")[1]


def test_on_approved_without_lock_fails_then_lock_passes(locked):
    name = new_change(locked)
    approve(locked, name)
    code, out = gate(locked, "check")
    assert code == 1 and "not locked" in out
    assert gate(locked, "lock", "greet")[0] == 0
    assert gate(locked, "check")[0] == 0


def test_on_lock_refuses_a_draft(locked):
    new_change(locked)
    code, out = gate(locked, "lock", "greet")
    assert code == 1 and "approved" in out


def test_on_changed_acceptance_test_fails_the_gate(locked):
    name = new_change(locked)
    approve(locked, name)
    gate(locked, "lock", name)
    (locked / "tests" / "acceptance" / name / "test_it.py").write_text("def test_ok():\n    pass\n")
    code, out = gate(locked, "check")
    assert code == 1 and "changed since they were locked" in out


def test_on_added_acceptance_file_fails_the_gate(locked):
    name = new_change(locked)
    approve(locked, name)
    gate(locked, "lock", name)
    (locked / "tests" / "acceptance" / name / "test_extra.py").write_text("def test_x():\n    assert True\n")
    assert gate(locked, "check")[0] == 1


def test_on_hook_blocks_edits_to_approved_acceptance_tests(locked):
    name = new_change(locked)
    approve(locked, name)
    code, err = hook(locked, "Edit", file_path=f"tests/acceptance/{name}/test_it.py")
    assert code == 2 and "approved" in err
    assert edit_log(locked) == []


def test_on_hook_blocks_lock_file_and_lock_command(locked):
    name = new_change(locked)
    assert hook(locked, "Write", file_path=str(locked / "changes" / name / "acceptance.lock"))[0] == 2
    assert hook(locked, "Bash", command=f"python scripts/gate.py lock {name}")[0] == 2
    assert hook(locked, "Bash", command=f"echo x > changes/{name}/acceptance.lock")[0] == 2


def test_on_hook_blocks_shell_writes_to_approved_tests_only(locked):
    name = new_change(locked)
    assert hook(locked, "Bash", command=f"rm tests/acceptance/{name}/test_it.py")[0] == 0
    approve(locked, name)
    assert hook(locked, "Bash", command=f"rm tests/acceptance/{name}/test_it.py")[0] == 2
    assert hook(locked, "Bash", command=f"cat tests/acceptance/{name}/test_it.py")[0] == 0
