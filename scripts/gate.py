#!/usr/bin/env python3
"""SDLC gates for an AI-native repo. Standard library only (Python 3.11+).

Every change lives in changes/<NNNN-slug>/ with intent.md, spec.md and plan.md, and its
acceptance tests live in tests/acceptance/<NNNN-slug>/.

    python scripts/gate.py new <slug>       scaffold a change from docs/templates/
    python scripts/gate.py check            run in CI: fails if a gate is not met
    python scripts/gate.py test             run the acceptance tests of approved changes
    python scripts/gate.py pr-check <base>  run in CI on a PR: docs-only, or an approved change
    python scripts/gate.py lock <change>    a HUMAN runs this (only when the lock is on)

Two modes, set in sdlc.toml:

- acceptance_lock = false (default): Anthropic's AI-native SDLC playbook as written. A human
  approves the spec; reviewers check that approved acceptance tests were not changed. The
  gates only WARN about such edits, and the Claude Code hook logs them.
- acceptance_lock = true: the VibeOps experiment. Approved acceptance tests are pinned by
  hash. Editing them fails the gate, and the hook blocks the agent.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGES = ROOT / "changes"
ACCEPTANCE = ROOT / "tests" / "acceptance"
TEMPLATES = ROOT / "docs" / "templates"
SETTINGS = ROOT / "sdlc.toml"
LOCK_NAME = "acceptance.lock"
REQUIRED = ("intent.md", "spec.md")
STATUSES = ("draft", "approved", "done")
APPROVED = ("approved", "done")
OWNER_RE = re.compile(r"^\**owner \(human\):\**\s*@[A-Za-z0-9]", re.IGNORECASE | re.MULTILINE)
STATUS_RE = re.compile(r"^\s*\**status\**\s*:\s*\**\s*([a-z]+)", re.IGNORECASE | re.MULTILINE)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

RULE_FILES = {"AGENTS.md", "CLAUDE.md", "REVIEW.md", "sdlc.toml"}
RULE_DIRS = (".claude/", ".github/", "scripts/", "docs/templates/", "evals/")
NEVER_DOCS = ("changes/", "tests/", ".sdlc/")
EDIT_LOG = ".sdlc/acceptance-edits.jsonl"


# --- settings ---------------------------------------------------------------------------

def lock_enabled() -> bool:
    """True only if sdlc.toml sets acceptance_lock = true. Missing or unreadable: off."""
    try:
        return tomllib.loads(SETTINGS.read_text(encoding="utf-8")).get("acceptance_lock") is True
    except (OSError, tomllib.TOMLDecodeError):
        return False


def mode_name() -> str:
    return "acceptance lock ON (VibeOps experiment)" if lock_enabled() else "playbook (acceptance lock off)"


def warn(message: str) -> None:
    # The "::warning::" prefix shows as an annotation in GitHub Actions; it reads fine locally.
    print(f"::warning::{message}")


# --- changes ----------------------------------------------------------------------------

def parse_status(text: str) -> str | None:
    m = STATUS_RE.search(text)
    return m.group(1).lower() if m else None


def spec_status(change: Path) -> str | None:
    spec = change / "spec.md"
    return parse_status(spec.read_text(encoding="utf-8")) if spec.is_file() else None


def intent_status(change: Path) -> str | None:
    """The intent's status. No intent.md, or no 'Status:' line, means draft."""
    intent = change / "intent.md"
    if not intent.is_file():
        return None
    return parse_status(intent.read_text(encoding="utf-8")) or "draft"


def has_owner(change: Path) -> bool:
    """The intent names a human owner: 'Owner (human):' followed by an @handle."""
    intent = change / "intent.md"
    return intent.is_file() and OWNER_RE.search(intent.read_text(encoding="utf-8")) is not None


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


def check_change(change: Path, warnings: list[str] | None = None) -> list[str]:
    """Problems that fail the gate. Lock findings go to `warnings` when the lock is off."""
    name = change.name
    problems = [f"{name}: missing {f}" for f in REQUIRED if not (change / f).is_file()]
    status = spec_status(change)
    if (change / "spec.md").is_file() and status not in STATUSES:
        problems.append(f"{name}: spec.md needs a 'Status:' line (one of {', '.join(STATUSES)})")
    if status not in APPROVED:
        return problems

    if (change / "intent.md").is_file():
        if intent_status(change) not in APPROVED:
            problems.append(
                f"{name}: spec is {status} but intent.md is not; a human must approve the intent too"
            )
        elif not has_owner(change):
            problems.append(f"{name}: approved intent.md must name a human owner ('Owner (human): @handle')")
    if not (change / "plan.md").is_file():
        problems.append(f"{name}: spec is {status} but there is no plan.md")
    tests = ACCEPTANCE / name
    if not has_tests(tests):
        problems.append(f"{name}: spec is {status} but tests/acceptance/{name}/ has no tests")
        return problems

    locked = read_lock(change)
    if lock_enabled():
        if locked is None:
            problems.append(
                f"{name}: acceptance tests are not locked. After a human approves the spec, "
                f"they run: python scripts/gate.py lock {name}"
            )
        elif locked != tests_hash(tests):
            problems.append(
                f"{name}: approved acceptance tests changed since they were locked. "
                "A human must review the change and lock again."
            )
    elif locked is not None and locked != tests_hash(tests) and warnings is not None:
        warnings.append(f"{name}: acceptance tests differ from {LOCK_NAME}. Reviewer: confirm a human agreed.")
    return problems


def all_changes() -> list[Path]:
    return sorted(p for p in CHANGES.iterdir() if p.is_dir()) if CHANGES.is_dir() else []


# --- commands ---------------------------------------------------------------------------

def cmd_check() -> int:
    changes = all_changes()
    warnings: list[str] = []
    problems = [p for c in changes for p in check_change(c, warnings)]
    print(f"Mode: {mode_name()}")
    for c in changes:
        print(f"  {c.name}: {spec_status(c) or 'no status'}")
    for w in warnings:
        warn(w)
    if problems:
        print("\nGate failed:")
        print("\n".join(f"  ✗ {p}" for p in problems))
        return 1
    print(f"\nGate passed: {len(changes)} change(s) checked.")
    return 0


def cmd_test() -> int:
    """Run acceptance tests for approved or done changes. Drafts are expected to fail."""
    paths = [
        str(ACCEPTANCE / c.name)
        for c in all_changes()
        if spec_status(c) in APPROVED and has_tests(ACCEPTANCE / c.name)
    ]
    if not paths:
        print("No approved changes with acceptance tests yet.")
        return 0
    return subprocess.call([sys.executable, "-m", "pytest", "-q", *paths], cwd=ROOT)


def is_rule_file(path: str) -> bool:
    return path in RULE_FILES or path.startswith(RULE_DIRS)


def is_docs_file(path: str) -> bool:
    if is_rule_file(path) or path.startswith(NEVER_DOCS):
        return False
    return path.endswith((".md", ".txt")) or path.startswith("docs/") or path == "LICENSE"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def changed_files(base: str) -> list[str] | None:
    p = git("diff", "--name-only", f"{base}...HEAD")
    if p.returncode != 0:
        print(p.stderr.strip() or f"git diff against {base} failed.")
        return None
    return [line for line in p.stdout.splitlines() if line]


def status_at(base: str, name: str) -> str | None:
    """The change's spec status on the base branch (None if it did not exist there)."""
    p = git("show", f"{base}:changes/{name}/spec.md")
    return parse_status(p.stdout) if p.returncode == 0 else None


def edit_log_changes(base: str) -> tuple[list[str], int]:
    """Lines this PR added to the edit log, and how many it removed."""
    p = git("diff", "--unified=0", f"{base}...HEAD", "--", EDIT_LOG)
    added, removed = [], 0
    for line in p.stdout.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return added, removed


def cmd_pr_check(base: str) -> int:
    """Docs-only PRs pass. Any other PR needs an approved change folder."""
    files = changed_files(base)
    if files is None:
        return 2
    print(f"Mode: {mode_name()}")
    if not files:
        print("No changed files.")
        return 0

    problems: list[str] = []
    warnings: list[str] = []

    # Acceptance tests of a change that was already approved on the base branch.
    edited = sorted({
        f.split("/")[2] for f in files
        if f.startswith("tests/acceptance/") and f.count("/") >= 3
        and status_at(base, f.split("/")[2]) in APPROVED
    })
    for name in edited:
        message = f"{name}: this PR edits acceptance tests that were already approved"
        if lock_enabled():
            problems.append(message + ". A human must review and lock again.")
        else:
            warnings.append(message + ". Reviewer: confirm a human agreed (see REVIEW.md).")

    # The hook's log of agent edits to approved acceptance tests (committed with the PR).
    if EDIT_LOG in files:
        added, removed = edit_log_changes(base)
        for entry in added:
            warnings.append(f"agent edit to approved acceptance tests logged in {EDIT_LOG}: {entry}")
        if removed:
            warnings.append(f"{removed} line(s) were removed from {EDIT_LOG}. The log is append-only.")

    if not problems and all(is_docs_file(f) for f in files):
        print(f"docs-only PR ({len(files)} file(s)): needs review, no change folder.")
        return 0

    other = [f for f in files if not is_docs_file(f) and not f.startswith("changes/")]
    rules = [f for f in other if is_rule_file(f)]
    touched = sorted({f.split("/")[1] for f in files if f.startswith("changes/") and f.count("/") >= 2})
    names = [n for n in touched if (CHANGES / n).is_dir()]  # deleted folders don't count
    if not names:
        what = ", ".join(rules[:3]) if rules else ", ".join(other[:3]) or "a change folder"
        problems.append(
            f"this PR changes {what} but includes no change folder under changes/ (deleted folders don't count)"
        )
    for name in names:
        change = CHANGES / name
        status = spec_status(change)
        if status not in APPROVED:
            step = "approve and lock it" if lock_enabled() else "approve it"
            problems.append(f"{name}: spec is {status or 'missing a status'}; a human must {step}")
        else:
            problems.extend(check_change(change, warnings))

    for w in warnings:
        warn(w)
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
    if not lock_enabled():
        print("The acceptance lock is off (sdlc.toml). Set acceptance_lock = true to use it.")
        return 1
    change = find_change(arg)
    if change is None:
        print(f"No single change matches '{arg}' in changes/.")
        return 2
    if spec_status(change) not in APPROVED:
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
    if len(argv) == 1 and argv[0] in ("check", "test"):
        return cmd_check() if argv[0] == "check" else cmd_test()
    if len(argv) == 2 and argv[0] in ("lock", "new", "pr-check"):
        return {"lock": cmd_lock, "new": cmd_new, "pr-check": cmd_pr_check}[argv[0]](argv[1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
