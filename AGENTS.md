# AGENTS.md

Rules for any coding agent working in this repo (Claude Code, Codex, Cursor and friends).
The human who approves a change is accountable for it, so these rules exist to make their
judgment cheap and well-informed, not to route around it.

## The loop

Every change goes through five steps, as files in `changes/<NNNN-slug>/`:

1. **Intent** (`intent.md`): the problem, who it is for, and what "done" means. Written or
   confirmed by a human. Never start without one.
2. **Spec** (`spec.md`): behaviour, edge cases, and the acceptance tests in
   `tests/acceptance/<NNNN-slug>/`. You may draft both. **Stop here** and ask a human to
   review. The human sets `Status: approved` and runs `python scripts/gate.py lock <change>`.
3. **Plan** (`plan.md`): the files you will touch and the order, small steps. Keep it true:
   if the work drifts from the plan, update the plan in the same commit.
4. **Build**: make the acceptance tests pass. Add any other tests you like.
5. **Review**: open a PR using the template. Another reviewer (a second agent, then a
   named human) checks it against `REVIEW.md`. You cannot approve your own work.

Start a change with `python scripts/gate.py new <slug>`.

## Hard rules

- **Never edit approved acceptance tests** or any `acceptance.lock`, and never run
  `gate.py lock`. A hook blocks this; CI fails it. If a test looks wrong, say so and stop.
- **"Done" needs evidence.** Report the commands you ran and their output, not a summary of
  what you believe happened.
- **No new dependencies, network calls or secrets** without saying so in the PR, with a
  reason.
- **Don't widen scope.** Anything outside the intent goes in the PR as a suggestion.
- **Open questions get written down** in the spec or plan, never silently dropped.

## Commands

```bash
python scripts/gate.py check      # the SDLC gates (what CI runs)
python -m pytest                  # all tests
```

## Project-specific rules

Add your own architecture, style and domain rules below this line.
