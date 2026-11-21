#!/usr/bin/env python3
"""Claude Code PreToolUse hook: keep the agent away from the answer key.

Blocks (exit 2, with the reason shown to the agent):
- editing any acceptance.lock file,
- editing acceptance tests whose spec is already approved,
- running `gate.py lock` (locking is the human approval step).

Drafting acceptance tests while the spec is still a draft is allowed. This hook covers
Claude Code's file tools and obvious shell commands; CI (`gate.py check`) is the real gate.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / "scripts"))

from gate import CHANGES, LOCK_NAME, spec_status  # noqa: E402

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def block(reason: str) -> int:
    print(f"Blocked by the SDLC gate: {reason}", file=sys.stderr)
    return 2


def protected(path: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if rel.name == LOCK_NAME:
        return "acceptance.lock is written only by a human with `gate.py lock`."
    if len(parts) >= 3 and parts[:2] == ("tests", "acceptance"):
        change = CHANGES / parts[2]
        if spec_status(change) in ("approved", "done"):
            return (
                f"the acceptance tests for {parts[2]} are approved. Add new tests elsewhere, "
                "or ask a human to change the spec."
            )
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = event.get("tool_name", "")
    args = event.get("tool_input") or {}

    if tool in FILE_TOOLS:
        target = args.get("file_path") or args.get("notebook_path")
        if target:
            path = Path(target)
            reason = protected(path if path.is_absolute() else ROOT / path)
            if reason:
                return block(reason)

    if tool == "Bash":
        command = args.get("command", "")
        if re.search(r"gate\.py\s+lock\b", command):
            return block("locking acceptance tests is the human approval step.")
        if LOCK_NAME in command:
            return block("acceptance.lock is written only by a human with `gate.py lock`.")
        for match in re.finditer(r"tests/acceptance/([a-z0-9][a-z0-9-]*)", command):
            if spec_status(CHANGES / match.group(1)) in ("approved", "done") and re.search(
                r"(\brm\b|\bmv\b|\bsed\s+-i|>|\btee\b|\bcp\b|\btruncate\b)", command
            ):
                return block(f"the acceptance tests for {match.group(1)} are approved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
