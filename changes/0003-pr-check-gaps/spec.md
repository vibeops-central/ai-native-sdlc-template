# Spec: 0003-pr-check-gaps

Status: draft
Risk: higher
<!-- draft -> approved (a human sets this, together with Status: approved in intent.md) -> done -->
<!-- Risk is higher because this changes the gate tooling and the templates. -->

## Behaviour

### 1. Only existing change folders count (`gate.py pr-check`)
- A change folder counts for a PR only if it exists at `HEAD` (after the PR).
- A PR that changes anything other than docs must include at least one counting change
  folder. Otherwise it fails with: "includes no change folder under changes/ (deleted
  folders don't count)".
- Every counting change folder must pass the same checks as today (approved spec, plan,
  acceptance tests, lock if on) plus the intent rule below.
- Deleting a change folder is never docs-only, so a PR that only deletes a change folder
  needs its own approved change, like any other PR.

### 2. Approval covers the intent (`gate.py check` and `pr-check`)
- `docs/templates/intent.md` gets a `Status: draft` line at the top. `gate.py new` copies
  it, so every new change starts with a draft intent.
- When a spec is `approved` or `done`, its intent must also be `approved` or `done`.
  Otherwise the gate fails with: "<change>: spec is approved but intent.md is not; a human
  must approve the intent too".
- An approved intent must name a human owner: the `Owner (human):` line must contain an
  `@handle`, not only the placeholder `@`. Otherwise the gate fails.
- A draft spec does not need an approved intent (drafting is still free).
- AGENTS.md step 2 and REVIEW.md say that approving a change means setting both statuses.
  The spec template comment says the same.

### 3. Existing changes
- Change 0002 is approved and merged, and its intent has no `Status:` line. This change
  adds `Status: approved` to 0002's intent, recording that Natu approved 0002 on 21 Nov.
  **Approving this spec confirms that record.**
- Change 0001 (draft) gets `Status: draft` in its intent.

## Edge cases
- An intent without any `Status:` line counts as draft.
- A PR that deletes one change folder and includes another approved change passes.
- A PR that deletes approved acceptance tests still gets the existing "already approved"
  warning (lock off) or failure (lock on).

## Acceptance tests
Tests in `tests/acceptance/0003-pr-check-gaps/`.

| # | Given / when / then | Test |
|---|---|---|
| 1 | A PR deletes an approved change folder and changes code: fails | `test_deleted_change_folder_does_not_count` |
| 2 | A PR deletes an old change folder and includes another approved change: passes | `test_deleted_folder_with_another_approved_change_passes` |
| 3 | A PR that only deletes a change folder: fails | `test_only_deleting_a_change_folder_needs_a_change` |
| 4 | `gate.py new` creates an intent with `Status: draft` | `test_new_change_intent_starts_as_draft` |
| 5 | Approved spec with a draft intent: `check` fails and names the intent | `test_approved_spec_needs_approved_intent` |
| 6 | Approved intent with only the `@` placeholder as owner: `check` fails | `test_approved_intent_needs_an_owner` |
| 7 | Approved intent with an owner and approved spec: `check` passes | `test_approved_intent_and_spec_pass` |
| 8 | Draft spec with a draft intent: `check` passes | `test_draft_spec_does_not_need_approved_intent` |
| 9 | A PR with code and an approved spec but a draft intent: `pr-check` fails | `test_pr_check_needs_approved_intent` |

## Open questions
- **Who set the status?** These checks prove a status says "approved", not that a human
  wrote it. My pull requests appear on GitHub as authored by @nlauchande, because I work
  through that account. Making "human approval" provable needs agents to have their own
  GitHub identity (a bot account or app) and code-owner review on `changes/`. Out of scope
  here; worth its own change.
