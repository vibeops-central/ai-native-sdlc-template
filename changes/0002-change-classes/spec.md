# Spec: 0002-change-classes

Status: draft
Risk: higher
<!-- draft -> approved (a human sets this, then runs `python scripts/gate.py lock 0002-change-classes`) -> done -->
<!-- Risk is higher because this changes the gate tooling and the agent's rules. -->

## Behaviour
New command: `python scripts/gate.py pr-check <base-ref>`. It lists the files that differ
between `<base-ref>` and `HEAD` and classifies the PR:

- **Rule files** steer the agent: `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`, anything under
  `.claude/`, `.github/`, `scripts/`, `docs/templates/`.
- **Docs files** are the other `.md` and `.txt` files, anything under `docs/`, and
  `LICENSE`. Files under `changes/` and `tests/` are never docs.
- **Docs-only PR:** every changed file is a docs file. The check passes.
- **Any other PR** must change at least one folder under `changes/`, and the spec of every
  changed change must be `approved` or `done` with its acceptance tests locked. Otherwise
  the check fails and names what is missing.
- A PR with no changed files passes.

AGENTS.md describes the three classes. REVIEW.md tells reviewers to confirm the class.
`docs/templates/spec.md` gets a `Risk:` line. CI runs `pr-check` on pull requests.

## Edge cases
- A deleted file is classified by its path, like any other changed file.
- A docs file and a rule file in the same PR make it a full-loop PR.
- A PR that only adds a draft change (intent and spec for review) fails `pr-check`: a draft
  can be reviewed on a branch, but it does not merge until it is approved and locked.
- `Risk: higher` is not checked by CI. It tells the reviewer that a tech lead must approve.

## Acceptance tests
Each one maps to a test in `tests/acceptance/0002-change-classes/`.

| # | Given / when / then | Test |
|---|---|---|
| 1 | A PR that changes only README.md passes | `test_docs_only_passes` |
| 2 | A PR that changes AGENTS.md without a change fails | `test_rule_file_needs_a_change` |
| 3 | A PR that changes code without a change fails | `test_code_needs_a_change` |
| 4 | A PR with code and a draft change fails | `test_draft_change_does_not_merge` |
| 5 | A PR with code and an approved, locked change passes | `test_approved_locked_change_passes` |
| 6 | A PR with code and an approved change whose tests changed after the lock fails | `test_unlocked_change_fails` |
| 7 | A PR with README.md and a template file is not docs-only | `test_mixed_docs_and_rules` |
| 8 | A PR with no changed files passes | `test_empty_pr_passes` |

## Open questions
- Should `evals/` count as docs or as rule files? This spec treats `evals/*.md` as docs.
