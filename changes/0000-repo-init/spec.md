# Spec: 0000-repo-init

Status: draft
Risk: higher
<!-- draft -> approved: the owner sets this here AND in intent.md, in the setup pull request. -->
<!-- Risk: higher, because this change sets who owns the agent's rules. -->

## Behaviour
1. The owner writes their GitHub handle and the date in `intent.md`.
2. In `.github/CODEOWNERS`, the owner replaces `@YOUR-HANDLE` with their handle or team, and
   removes the `#` at the start of each owner line.
3. The owner adds at least one project rule below the marker line in `AGENTS.md`.
4. The owner sets branch protection on `main` to require the `gates` status check.
5. The owner sets `Status: approved` in `intent.md` and `spec.md`, and opens one pull request
   with all of this. The PR check passes because this change folder is in the PR.

## Edge cases
- The owner is a team (`@org/team`). CODEOWNERS accepts it. The intent still names one
  human, because a person is accountable.
- Branch protection can't be checked from a test without GitHub access. The reviewer
  checks it, using the PR's checklist.
- The repo is the template itself. This change stays `draft` there, so `gate.py test` does
  not run its tests.

## Acceptance tests
Each one maps to a test in `tests/acceptance/0000-repo-init/`.

| # | Given / when / then | Test |
|---|---|---|
| 1 | The intent names a human owner, not the empty placeholder | `test_intent_names_owner` |
| 2 | CODEOWNERS has no `@YOUR-HANDLE`, and has active owner lines for `/AGENTS.md`, `/tests/acceptance/` and `/scripts/gate.py` | `test_codeowners_filled` |
| 3 | `AGENTS.md` has at least one non-empty line below the marker line | `test_agents_has_project_rules` |

## Open questions
- **Bootstrap.** In the template, 0000 is `draft`. So the PR that adds 0000 to the template
  has no approved change folder, and the PR check fails. Proposal: merge that one PR with a
  one-off bypass, as with PR #3. After that, every new repo's setup PR passes normally.
- **Test 3.** Should a new repo need its own rule before it can start? Proposal: yes. A
  one-line rule is enough, and it makes the owner read AGENTS.md once.
