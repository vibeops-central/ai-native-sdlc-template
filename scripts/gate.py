#!/usr/bin/env python3
"""SDLC gates for an AI-native repo. Standard library only.

Every change lives in changes/<NNNN-slug>/ with intent.md, spec.md and plan.md, and its
acceptance tests live in tests/acceptance/<NNNN-slug>/.

    python scripts/gate.py new <slug>      scaffold a change from docs/templates/
    python scripts/gate.py lock <change>   a HUMAN runs this after approving the spec
    python scripts/gate.py check           run in CI: fails if a gate is not met
    python scripts/gate.py test            run the acceptance tests of approved changes
    python scripts/gate.py pr-check <base> run in CI on a PR: docs-only, or an approved change

The lock is the "answer key rule": once a spec is approved, its acceptance tests are pinned
by hash. The agent can add other tests, but a change to the approved ones fails the gate
until a human reviews it and locks again.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGES = ROOT / "changes"
ACCEPTANCE = ROOT / "tests" / "acceptance"
TEMPLATES = ROOT / "docs" / "templates"
LOCK_NAME = "acceptance.lock"
REQUIRED = ("intent.md", "spec.md")
STATUSES = ("draft", "approved", "done")
STATUS_RE = re.compile(r"^\s*\**status\**\s*:\s*\**\s*([a-z]+)", re.IGNORECASE | re.MULTILINE)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def spec_status(change: Path) -> str | None:
    spec = change / "spec.md"
    if not spec.is_file():
        return None
    m = STATUS_RE.search(spec.read_text(encoding="utf-8"))
    return m.group(1).lower() if m else None


def tests_hash(folder: Path) -> str:
    """One sha256 over every file's relative path and bytes (caches ignored)."""
    digest = hashlib.sha256()
    for f in sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        digest.update(f.relative_to(folder).as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
    return digest.hexdigest()


def read_lock(change: Path) -> str | None:
    lock = change / LOCK_NAME
    if not lock.is_file():
        return None
    for line in lock.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha256:"):
            return line.split(":", 1)[1].strip()
    return None


def has_tests(folder: Path) -> bool:
    return folder.is_dir() and any(p.is_file() and "__pycache__" not in p.parts for p in folder.rglob("*"))


def check_change(change: Path) -> list[str]:
    name = change.name
    problems = [f"{name}: missing {f}" for f in REQUIRED if not (change / f).is_file()]
    status = spec_status(change)
    if (change / "spec.md").is_file() and status not in STATUSES:
        problems.append(f"{name}: spec.md needs a 'Status:' line (one of {', '.join(STATUSES)})")
    if status in ("approved", "done"):
        if not (change / "plan.md").is_file():
            problems.append(f"{name}: spec is {status} but there is no plan.md")
        tests = ACCEPTANCE / name
        locked = read_lock(change)
        if not has_tests(tests):
            problems.append(f"{name}: spec is {status} but tests/acceptance/{name}/ has no tests")
        elif locked is None:
            problems.append(
                f"{name}: acceptance tests are not locked. After a human approves the spec, "
                f"they run: python scripts/gate.py lock {name}"
            )
        elif locked != tests_hash(tests):
            problems.append(
                f"{name}: approved acceptance tests changed since they were locked. "
                f"A human must review the change and lock again."
            )
    return problems


def cmd_check() -> int:
    changes = sorted(p for p in CHANGES.iterdir() if p.is_dir()) if CHANGES.is_dir() else []
    problems = [p for c in changes for p in check_change(c)]
    for c in changes:
        print(f"  {c.name}: {spec_status(c) or 'no status'}")
    if problems:
        print("\nGate failed:")
        print("\n".join(f"  ✗ {p}" for p in problems))
        return 1
    print(f"\nGate passed: {len(changes)} change(s) checked.")
    return 0


def cmd_test() -> int:
    """Run acceptance tests for approved or done changes. Drafts are expected to fail."""
    changes = sorted(p for p in CHANGES.iterdir() if p.is_dir()) if CHANGES.is_dir() else []
    paths = [
        str(ACCEPTANCE / c.name)
        for c in changes
        if spec_status(c) in ("approved", "done") and has_tests(ACCEPTANCE / c.name)
    ]
    if not paths:
        print("No approved changes with acceptance tests yet.")
        return 0
    return subprocess.call([sys.executable, "-m", "pytest", "-q", *paths], cwd=ROOT)


RULE_FILES = {"AGENTS.md", "CLAUDE.md", "REVIEW.md"}
RULE_DIRS = (".claude/", ".github/", "scripts/", "docs/templates/")
NEVER_DOCS = ("changes/", "tests/")


def is_rule_file(path: str) -> bool:
    return path in RULE_FILES or path.startswith(RULE_DIRS)


def is_docs_file(path: str) -> bool:
    if is_rule_file(path) or path.startswith(NEVER_DOCS):
        return False
    return path.endswith((".md", ".txt")) or path.startswith("docs/") or path == "LICENSE"


def changed_files(base: str) -> list[str] | None:
    p = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    if p.returncode != 0:
        print(p.stderr.strip() or f"git diff against {base} failed.")
        return None
    return [line for line in p.stdout.splitlines() if line]


def cmd_pr_check(base: str) -> int:
    """Docs-only PRs pass. Any other PR needs an approved, locked change folder."""
    files = changed_files(base)
    if files is None:
        return 2
    if not files:
        print("No changed files.")
        return 0
    if all(is_docs_file(f) for f in files):
        print(f"docs-only PR ({len(files)} file(s)): needs review, no change folder.")
        return 0

    other = [f for f in files if not is_docs_file(f) and not f.startswith("changes/")]
    rules = [f for f in other if is_rule_file(f)]
    names = sorted({f.split("/")[1] for f in files if f.startswith("changes/") and f.count("/") >= 2})
    problems: list[str] = []
    if not names:
        what = ", ".join(rules[:3]) if rules else ", ".join(other[:3])
        problems.append(f"this PR changes {what} but includes no change folder under changes/")
    for name in names:
        change = CHANGES / name
        if not change.is_dir():
            continue  # the change folder was deleted in this PR
        status = spec_status(change)
        if status not in ("approved", "done"):
            problems.append(f"{name}: spec is {status or 'missing a status'}; a human must approve and lock it")
        else:
            problems.extend(check_change(change))
    if problems:
        print("PR check failed:")
        print("\n".join(f"  ✗ {p}" for p in problems))
        return 1
    print(f"PR check passed: {len(files)} file(s), change(s): {', '.join(names)}.")
    return 0


def find_change(arg: str) -> Path | None:
    exact = CHANGES / arg
    if exact.is_dir():
        return exact
    matches = sorted(p for p in CHANGES.glob(f"*-{arg}") if p.is_dir())
    return matches[0] if len(matches) == 1 else None


def cmd_lock(arg: str) -> int:
    change = find_change(arg)
    if change is None:
        print(f"No single change matches '{arg}' in changes/.")
        return 2
    if spec_status(change) not in ("approved", "done"):
        print(f"{change.name}: set 'Status: approved' in spec.md first. Locking is the approval step.")
        return 1
    tests = ACCEPTANCE / change.name
    if not has_tests(tests):
        print(f"{change.name}: no tests in tests/acceptance/{change.name}/ to lock.")
        return 1
    digest = tests_hash(tests)
    (change / LOCK_NAME).write_text(
        "# Written by a human with `python scripts/gate.py lock`. Agents must not edit this file.\n"
        f"sha256: {digest}\n",
        encoding="utf-8",
    )
    print(f"Locked {change.name} acceptance tests at {digest[:12]}.")
    return 0


def cmd_new(slug: str) -> int:
    if not SLUG_RE.match(slug):
        print("Use a short lower-case slug, e.g. 'export-csv'.")
        return 2
    CHANGES.mkdir(exist_ok=True)
    numbers = [int(p.name[:4]) for p in CHANGES.iterdir() if p.is_dir() and p.name[:4].isdigit()]
    name = f"{(max(numbers) + 1) if numbers else 1:04d}-{slug}"
    change = CHANGES / name
    change.mkdir()
    for template in ("intent.md", "spec.md", "plan.md"):
        text = (TEMPLATES / template).read_text(encoding="utf-8").replace("{{change}}", name)
        (change / template).write_text(text, encoding="utf-8")
    (ACCEPTANCE / name).mkdir(parents=True, exist_ok=True)
    print(f"Created changes/{name}/ and tests/acceptance/{name}/. Start with intent.md.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 1 and argv[0] == "check":
        return cmd_check()
    if len(argv) == 1 and argv[0] == "test":
        return cmd_test()
    if len(argv) == 2 and argv[0] == "pr-check":
        return cmd_pr_check(argv[1])
    if len(argv) == 2 and argv[0] in ("lock", "new"):
        return cmd_lock(argv[1]) if argv[0] == "lock" else cmd_new(argv[1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
