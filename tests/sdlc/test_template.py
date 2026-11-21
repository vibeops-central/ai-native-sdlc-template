"""Tests for the template as shipped: change 0000-repo-init and the greet example."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SHIPPED = ("scripts", "docs", ".claude", ".github", "changes", "tests/acceptance")


@pytest.fixture
def fresh(tmp_path):
    """A copy of the template, as a new repo gets it."""
    for rel in SHIPPED:
        shutil.copytree(REPO / rel, tmp_path / rel, ignore=shutil.ignore_patterns("__pycache__"))
    for rel in ("AGENTS.md", "sdlc.toml"):
        shutil.copy(REPO / rel, tmp_path / rel)
    return tmp_path


def run(repo, *args):
    p = subprocess.run([sys.executable, *args], cwd=repo, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def approve(folder, owner="@owner"):
    intent, spec = folder / "intent.md", folder / "spec.md"
    intent.write_text(intent.read_text().replace("Status: draft", "Status: approved", 1)
                      .replace("**Owner (human):** @", f"**Owner (human):** {owner}", 1))
    spec.write_text(spec.read_text().replace("Status: draft", "Status: approved", 1))


def test_template_ships_only_0000_as_draft(fresh):
    assert sorted(p.name for p in (fresh / "changes").iterdir()) == ["0000-repo-init"]
    assert "Status: draft" in (fresh / "changes" / "0000-repo-init" / "spec.md").read_text()
    assert run(fresh, "scripts/gate.py", "check")[0] == 0
    assert run(fresh, "scripts/gate.py", "test")[0] == 0


def test_template_names_no_owner(fresh):
    codeowners = (fresh / ".github" / "CODEOWNERS").read_text()
    active = [l for l in codeowners.splitlines() if l.strip() and not l.startswith("#")]
    assert active == [] and "@YOUR-HANDLE" in codeowners
    assert not (fresh / ".sdlc").exists()


def test_first_change_after_0000_is_0001(fresh):
    code, out = run(fresh, "scripts/gate.py", "new", "export-csv")
    assert code == 0 and "changes/0001-export-csv/" in out


def test_setup_without_filling_in_fails(fresh):
    approve(fresh / "changes" / "0000-repo-init")
    assert run(fresh, "scripts/gate.py", "test")[0] != 0


def test_setup_done_passes(fresh):
    folder = fresh / "changes" / "0000-repo-init"
    approve(folder, "@ada")
    codeowners = fresh / ".github" / "CODEOWNERS"
    codeowners.write_text("\n".join(
        l[2:] if l.startswith("# /") or l.startswith("# **") else l
        for l in codeowners.read_text().replace("@YOUR-HANDLE", "@ada").splitlines()) + "\n")
    agents = fresh / "AGENTS.md"
    agents.write_text(agents.read_text() + "\n- Use type hints in all Python code.\n")
    assert run(fresh, "scripts/gate.py", "check")[0] == 0
    code, out = run(fresh, "scripts/gate.py", "test")
    assert code == 0, out


def test_greet_example_copies_in_and_checks(fresh):
    shutil.copytree(fresh / "docs" / "examples" / "greet", fresh, dirs_exist_ok=True)
    folder = fresh / "changes" / "0001-greet"
    assert (fresh / "tests" / "acceptance" / "0001-greet" / "test_greet.py").exists()
    approve(folder, "@ada")
    code, out = run(fresh, "scripts/gate.py", "check")
    assert code == 0, out
