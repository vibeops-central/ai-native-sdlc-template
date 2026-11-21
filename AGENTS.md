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
   review. The human sets `Status: approved` in **both** `intent.md` and `spec.md` (and, if
   the acceptance lock is on, runs `python scripts/gate.py lock <change>`). An approved
   intent must name its human owner (`Owner (human): @handle`).
3. **Plan** (`plan.md`): the files you will touch and the order, small steps. Keep it true:
   if the work drifts from the plan, update the plan in the same commit.
4. **Build**: make the acceptance tests pass. Add any other tests you like.
5. **Review**: open a PR using the template. Another reviewer (a second agent, then a
   named human) checks it against `REVIEW.md`. You cannot approve your own work.

Start a change with `python scripts/gate.py new <slug>`.

## Change classes

Anthropic's playbook leaves "what counts as higher risk" to each team. This repo uses three
classes. CI checks the first two (`gate.py pr-check`); reviewers check the third.

| Class | What it is | What it needs | Who approves |
|---|---|---|---|
| **Docs-only** | Only `.md`/`.txt` files, `docs/`, `LICENSE` | A PR, reviewed against REVIEW.md. No change folder. | The engineer |
| **Routine** | Any other change | The full loop above | The engineer |
| **Higher risk** | Auth, payments, personal data, money movement, the gate tooling, the agent's rules | The full loop, with `Risk: higher` in the spec | A tech lead or second human |

**These are never docs:** `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`, `sdlc.toml`, `.claude/`,
`.github/`, `scripts/`, `docs/templates/`, `evals/`. They change how agents and gates
behave, or decide whether an agent passes, so they get the full loop. If you are unsure of
the class, use the stricter one.

## Acceptance-test lock (`sdlc.toml`)

- **Off (default):** Anthropic's playbook as written. Reviewers check that approved
  acceptance tests were not changed. CI warns about such edits, and the Claude Code hook logs
  them to `.sdlc/acceptance-edits.jsonl`. **Commit that log with your change**; CI repeats
  every new entry as a warning on the PR.
- **On:** the VibeOps experiment. Approved acceptance tests are pinned by hash. The hook
  blocks edits to them, and CI fails if they change.

## Hard rules

- **Never edit approved acceptance tests** or any `acceptance.lock`, and never run
  `gate.py lock`, in either mode. With the lock off, every such edit is logged and flagged
  for review; with it on, it is blocked. If a test looks wrong, say so and stop.
- **The edit log is append-only.** Never edit, shorten or delete
  `.sdlc/acceptance-edits.jsonl`. CI flags removed lines.
- **"Done" needs evidence.** Report the commands you ran and their output, not a summary of
  what you believe happened.
- **No new dependencies, network calls or secrets** without saying so in the PR, with a
  reason.
- **Don't widen scope.** Anything outside the intent goes in the PR as a suggestion.
- **Open questions get written down** in the spec or plan, never silently dropped.

## Commands

```bash
python scripts/gate.py check            # the SDLC gates (what CI runs)
python scripts/gate.py pr-check main    # the change-class check CI runs on a PR
python -m pytest                        # all tests
```

## Project-specific rules

Add your own architecture, style and domain rules below this line.
