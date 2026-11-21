"""Acceptance tests for change 0000: a repo made from the template has a human owner."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MARKER = "Add your own architecture, style and domain rules below this line."


def test_intent_names_owner():
    intent = (ROOT / "changes" / "0000-repo-init" / "intent.md").read_text()
    assert re.search(r"^\**Owner \(human\):\**\s*@[A-Za-z0-9]", intent, re.M), \
        "Write your GitHub handle after 'Owner (human): @' in intent.md"


def test_codeowners_filled():
    text = (ROOT / ".github" / "CODEOWNERS").read_text()
    assert "@YOUR-HANDLE" not in text, "Replace @YOUR-HANDLE in .github/CODEOWNERS"
    active = [l.split() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    owned = {parts[0] for parts in active if len(parts) > 1 and parts[1].startswith("@")}
    for path in ("/AGENTS.md", "/tests/acceptance/", "/scripts/gate.py"):
        assert path in owned, f"Give {path} an owner in .github/CODEOWNERS (remove the '#')"


def test_agents_has_project_rules():
    text = (ROOT / "AGENTS.md").read_text()
    assert MARKER in text, "Keep the marker line in AGENTS.md"
    below = text.split(MARKER, 1)[1]
    assert any(l.strip() and not l.strip().startswith("<!--") for l in below.splitlines()), \
        "Add at least one project rule below the marker line in AGENTS.md"
