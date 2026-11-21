# REVIEW.md

The policy every PR is reviewed against, by a reviewer agent first and a named human last.
The author of a change (human or agent) cannot be its approver.

## Block the PR if any of these is true

- [ ] The class is wrong (see AGENTS.md). For example, a "docs-only" PR that changes a
      rule file, or higher-risk work marked `Risk: routine`.
- [ ] A routine or higher-risk change has no `intent.md` and approved `spec.md`.
- [ ] `Risk: higher`, but no tech lead or second human approved it.
- [ ] `python scripts/gate.py check` or `python scripts/gate.py pr-check` fails.
- [ ] Approved acceptance tests or an `acceptance.lock` were changed without a human saying
      why in the PR. With the lock off, CI shows these as warnings ("already approved") and
      the agent's edits are logged in `.sdlc/acceptance-edits.jsonl`: read both.
- [ ] The PR claims "done" without evidence (commands run and their output).
- [ ] A new dependency, network call, secret or permission appears without a reason.

## Check, and comment if it fails

- [ ] **Drift:** does the diff match `plan.md`? Did the agent stay inside the boundaries in
      AGENTS.md, not only produce code that passes?
- [ ] **Scope:** does it do only what the intent asks?
- [ ] **Open questions:** anything parked in the spec or plan still unanswered?
- [ ] **Size:** could a human read this diff properly? If not, ask for it to be split.

## The human approver

Approve only what you understand well enough to answer for when it breaks. If you can't
explain the change, that is the review result.
