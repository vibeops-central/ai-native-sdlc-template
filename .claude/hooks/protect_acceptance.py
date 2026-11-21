#!/usr/bin/env python3
"""Claude Code PreToolUse hook for approved acceptance tests.

The behaviour depends on `acceptance_lock` in sdlc.toml:

- Off (default, Anthropic's playbook as written): edits to the acceptance tests of an
  approved change are allowed, and logged to .sdlc/acceptance-edits.jsonl. The log is
  committed with the PR, so the reviewer sees it in the diff and CI repeats each entry.
- On (VibeOps experiment): such edits are blocked (exit 2, the reason is shown to the agent),
  and so are edits to any acceptance.lock and running `gate.py lock`.

Drafting acceptance tests while the spec is still a draft is always allowed. This hook covers
Claude Code's file tools and obvious shell commands; CI (`gate.py`) is the real gate.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / "scripts"))

from gate import APPROVED, CHANGES, LOCK_NAME, lock_enabled, spec_status  # noqa: E402

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
LOG = ROOT / ".sdlc" / "acceptance-edits.jsonl"
SHELL_WRITE = re.compile(r"(\brm\b|\bmv\b|\bsed\s+-i|>|\btee\b|\bcp\b|\btruncate\b)")


def approved(change_name: str) -> bool:
    return spec_status(CHANGES / change_name) in APPROVED


def finding_for_path(path: Path) -> tuple[str, str] | None:
    """(kind, change) if the path is a lock file or an approved change's acceptance test."""
    try:
        rel = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if rel.name == LOCK_NAME:
        return ("lock-file", parts[1] if len(parts) > 2 else "")
    if len(parts) >= 3 and parts[:2] == ("tests", "acceptance") and approved(parts[2]):
        return ("approved-test", parts[2])
    return None


def finding_for_command(command: str) -> tuple[str, str] | None:
    if re.search(r"gate\.py\s+lock\b", command):
        return ("lock-command", "")
    if LOCK_NAME in command:
        return ("lock-file", "")
    if SHELL_WRITE.search(command):
        for match in re.finditer(r"tests/acceptance/([a-z0-9][a-z0-9-]*)", command):
            if approved(match.group(1)):
                return ("approved-test", match.group(1))
    return None


def log(tool: str, target: str, kind: str, change: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": tool, "target": target, "kind": kind, "change": change,
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


REASONS = {
    "lock-file": "acceptance.lock is written only by a human with `gate.py lock`.",
    "lock-command": "locking acceptance tests is the human approval step.",
    "approved-test": "these acceptance tests are approved. Add new tests elsewhere, or ask a human.",
}


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = event.get("tool_name", "")
    args = event.get("tool_input") or {}

    finding, target = None, ""
    if tool in FILE_TOOLS:
        target = args.get("file_path") or args.get("notebook_path") or ""
        if target:
            path = Path(target)
            finding = finding_for_path(path if path.is_absolute() else ROOT / path)
    elif tool == "Bash":
        target = args.get("command", "")
        finding = finding_for_command(target)
    if finding is None:
        return 0

    kind, change = finding
    if lock_enabled():
        print(f"Blocked by the SDLC gate: {REASONS[kind]}", file=sys.stderr)
        return 2
    if kind == "approved-test":
        log(tool, target, kind, change)
        print(
            f"Note: logged an edit to approved acceptance tests ({change}) in .sdlc/acceptance-edits.jsonl. "
            "Commit that file with your change.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
