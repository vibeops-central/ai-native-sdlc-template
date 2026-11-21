# Spec: 0002-change-classes

Status: approved
Risk: higher
<!-- draft -> approved (a human sets this) -> done. The acceptance lock is off by default, so no lock step. -->
<!-- Risk is higher because this changes the gate tooling and the agent's rules. -->

## Behaviour

### Change classes and `pr-check`
New command: `python scripts/gate.py pr-check <base-ref>`. It lists the files that differ
between `<base-ref>` and `HEAD` and classifies the PR:

- **Rule files** steer the agent: `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`, `sdlc.toml`, and
  anything under `.claude/`, `.github/`, `scripts/`, `docs/templates/`, `evals/`.
- **Docs files** are the other `.md` and `.txt` files, anything under `docs/`, and
  `LICENSE`. Files under `changes/`, `tests/` and `.sdlc/` are never docs.
- **Docs-only PR:** every changed file is a docs file. The check passes.
- **Any other PR** must change at least one folder under `changes/`, and the spec of every
  changed change must be `approved` or `done`. Otherwise the check fails and names what is
  missing.
- A PR with no changed files passes.

AGENTS.md describes the three classes. REVIEW.md tells reviewers to confirm the class.
`docs/templates/spec.md` gets a `Risk:` line. CI runs `pr-check` on pull requests.

### Acceptance-test lock: optional, off by default (added 21 Nov)
`sdlc.toml` holds one setting, `acceptance_lock`. Missing, unreadable or anything but
`true` means off.

| | Lock off (default: the playbook as written) | Lock on (VibeOps experiment) |
|---|---|---|
| `gate.py check`, approved change | Needs a plan and acceptance tests. No lock needed. A stale `acceptance.lock` is a warning. | Also needs `acceptance.lock` matching the tests, or it fails. |
| `gate.py lock` | Refuses: "the acceptance lock is off". | Writes the hash, as before. |
| `pr-check`, a PR edits acceptance tests of a change already approved on the base branch | Warning, check still passes. | Fails. |
| Claude Code hook, agent edits approved acceptance tests | Allowed, appended to `.sdlc/acceptance-edits.jsonl`. | Blocked (exit 2). |
| Claude Code hook, agent edits `acceptance.lock` or runs `gate.py lock` | Allowed (the lock command refuses anyway). | Blocked. |

Warnings print as `::warning::...` so GitHub Actions shows them on the PR.

### The edit log (decided 21 Nov)
- `.sdlc/acceptance-edits.jsonl` is committed with each PR, not ignored. The hook tells the
  agent to commit it.
- `pr-check` repeats every line the PR adds to the log as a warning, so the reviewer sees
  each agent edit without opening the file.
- The log is append-only. If a PR removes lines from it, `pr-check` warns. AGENTS.md forbids
  editing it, and REVIEW.md tells the reviewer to block such a PR.

## Edge cases
- A deleted file is classified by its path, like any other changed file.
- A docs file and a rule file in the same PR make it a full-loop PR.
- A PR that only adds a draft change (intent and spec for review) fails `pr-check`: a draft
  can be reviewed on a branch, but it does not merge until it is approved.
- A PR that edits approved acceptance tests without touching any change folder fails for
  that reason alone, in both modes.
- `Risk: higher` is not checked by CI. It tells the reviewer that a tech lead must approve.
- Turning the lock on is itself a change to a rule file (`sdlc.toml`), so it needs the full
  loop.

## Acceptance tests
Tests in `tests/acceptance/0002-change-classes/`. Tests marked "both" run once per mode.

| # | Given / when / then | Mode | Test |
|---|---|---|---|
| 1 | A PR that changes only README.md passes | both | `test_docs_only_passes` |
| 2 | A PR that changes AGENTS.md without a change fails | both | `test_rule_file_needs_a_change` |
| 3 | A PR that changes sdlc.toml without a change fails | both | `test_settings_file_is_a_rule_file` |
| 3a | A PR that changes a file in evals/ without a change fails | both | `test_evals_are_rule_files` |
| 4 | A PR that changes code without a change fails | both | `test_code_needs_a_change` |
| 5 | A PR with code and a draft change fails | both | `test_draft_change_does_not_merge` |
| 6 | A PR with README.md and a template file is not docs-only | both | `test_mixed_docs_and_rules` |
| 7 | A PR with no changed files passes | both | `test_empty_pr_passes` |
| 8 | A PR with code and an approved change passes without a lock | off | `test_off_approved_change_passes_without_lock` |
| 9 | Editing already-approved acceptance tests gives a warning and passes | off | `test_off_editing_approved_tests_warns` |
| 10 | A PR with code and an approved, locked change passes | on | `test_on_approved_locked_change_passes` |
| 11 | An approved change without a lock fails | on | `test_on_approved_without_lock_fails` |
| 12 | Tests changed after the lock fail | on | `test_on_unlocked_change_fails` |
| 13 | Editing already-approved acceptance tests fails | on | `test_on_editing_approved_tests_fails` |
| 14 | Each line a PR adds to the edit log shows as a warning | off | `test_edit_log_entries_are_repeated_as_warnings` |
| 15 | Removing lines from the edit log gives an "append-only" warning | off | `test_removing_edit_log_lines_warns` |
| 16 | A PR that only adds to the edit log is not docs-only | off | `test_edit_log_is_not_docs` |

The hook and `gate.py check` behaviour in both modes is covered by `tests/sdlc/test_gates.py`.

## Decisions (were open questions; Natu decided 21 Nov)
- `evals/` counts as **rule files**: evals decide whether an agent passes, so an agent must
  not soften them in a docs-only PR.
- `.sdlc/acceptance-edits.jsonl` is **committed**: the reviewer sees agent edits in the diff,
  and the record builds up for the lock experiment.

## Open questions
None.
