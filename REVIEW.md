# REVIEW.md

The policy every PR is reviewed against, by a reviewer agent first and a named human last.
The author of a change (human or agent) cannot be its approver.

## Block the PR if any of these is true

- [ ] There is no `intent.md` and approved `spec.md` for the change.
- [ ] `python scripts/gate.py check` fails.
- [ ] Approved acceptance tests or an `acceptance.lock` were changed without a human saying
      why in the PR.
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
