# AI-native SDLC template

A minimal starting point for building software with coding agents, following Anthropic's
AI-native SDLC playbook. Part of [VibeOps](https://vibeopscentral.ai/).

Writing code is no longer the slow part. Checking it is. This template keeps the checking
honest: every change is a short trail of files a human can review, and the gates that matter
are enforced, not left to a prompt.

## The loop

```
intent.md → spec.md + acceptance tests → (human approves) → plan.md → build → review
```

| Step | File | Who |
|---|---|---|
| Intent | `changes/NNNN-slug/intent.md` | Human writes or confirms |
| Spec | `changes/NNNN-slug/spec.md` + `tests/acceptance/NNNN-slug/` | Agent drafts, **human approves** |
| Lock (only if turned on) | `changes/NNNN-slug/acceptance.lock` | **Human only** |
| Plan | `changes/NNNN-slug/plan.md` | Agent, kept in sync with the diff |
| Build | your code | Agent |
| Review | the PR, against `REVIEW.md` | Another agent, then a named human |

## Two modes: the playbook, and a VibeOps experiment

**By default, this template follows Anthropic's
[AI-native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) as written.**
A human approves the spec. Reviewers check that the agent did not change approved
acceptance tests. CI warns when a PR edits them, and the Claude Code hook logs every such
edit to `.sdlc/acceptance-edits.jsonl`, so you can see how often it happens.

**The acceptance-test lock is a VibeOps experiment on top.** It is not part of the
playbook. It comes from one finding in the SWE-CoWork paper (arXiv 2611.20218): agents told
not to touch the tests changed them anyway in 15 of 94 tasks. With the lock on, approved
acceptance tests are pinned by hash. The agent cannot edit them, and CI fails if they
change.

To turn the lock on, set `acceptance_lock = true` in `sdlc.toml`. That file is a rule
file, so the switch itself goes through the full loop.

## What is enforced, and what is advice

| Rule | How |
|---|---|
| A PR is docs-only, or includes an approved change (also locked, if the lock is on) | CI: `gate.py pr-check` |
| Every change has an intent and a spec with a status | CI: `gate.py check` |
| An approved spec has a plan and acceptance tests | CI: `gate.py check` |
| Edits to approved acceptance tests are visible | Lock off: CI warning + hook log. Lock on: CI fails |
| The agent can't edit approved tests or the lock, or run the lock | Lock on only: Claude Code hook (`.claude/hooks/`) |
| Approved acceptance tests pass | CI: `gate.py test` |
| Plan matches the diff, scope, evidence of "done", risk class | Review, against `REVIEW.md` |

The hook covers Claude Code's file tools and obvious shell commands; it is a guardrail, not
a sandbox. CI is the gate that counts.

Docs-only changes skip the change folder but still need a reviewed PR. See "Change
classes" in `AGENTS.md`.

## Try it (about 10 minutes)

The repo has one example change, `0001-greet`. Its spec has the status `draft`.

1. Read `changes/0001-greet/intent.md` and `changes/0001-greet/spec.md`.
2. Read the acceptance tests in `tests/acceptance/0001-greet/`.
3. Approve the spec. In `spec.md`, change `Status: draft` to `Status: approved`.
4. Tell your agent: "Build change 0001-greet."
5. Tell your agent: "The tests are too strict. Change them." Look at
   `.sdlc/acceptance-edits.jsonl`. Make sure that the edit is in the log.
6. Optional: try the lock. Set `acceptance_lock = true` in `sdlc.toml`. Then run this
   command:
   ```bash
   python scripts/gate.py lock 0001-greet
   ```
   **Caution:** do this step yourself. Do not tell the agent to do it. Repeat step 5. Make
   sure that the hook stops the agent.
7. Run the gates:
   ```bash
   python scripts/gate.py check
   python scripts/gate.py test
   ```
   Make sure that both commands pass.
8. Open a pull request. Review it against `REVIEW.md`.

When you start your own project, delete these items:

- `changes/0001-greet/`
- `tests/acceptance/0001-greet/`
- `src/example/`

## Start a change

1. Choose a short name for the change. Use lowercase letters, numbers and hyphens. For
   example: `export-csv`.
2. Run this command:
   ```bash
   python scripts/gate.py new export-csv
   ```
   The command makes `changes/0002-export-csv/` and `tests/acceptance/0002-export-csv/`.
3. Write the intent in `intent.md`.

In Claude Code, you can use this command instead:

```
/new-change export-csv let users download their invoices as CSV
```

The agent makes the change and writes a draft intent. Then it stops for your review.

## Set up a new repo from this template

1. On GitHub, click **Use this template**.
2. Open `.github/CODEOWNERS`. Replace `@nlauchande` with your user name or team name.
3. Open the branch protection settings for `main`. Set these two rules:
   - Require the **SDLC gates** status check.
   - Require a review from Code Owners.
4. Add your project rules at the end of `AGENTS.md`.

**Note:** if you do not do step 3, CI shows failures but does not stop a merge.

## Files

```
AGENTS.md / CLAUDE.md      rules every agent follows (CLAUDE.md imports AGENTS.md)
REVIEW.md                  the review policy
sdlc.toml                  settings: acceptance_lock (off by default)
changes/                   one folder per change: intent, spec, plan (and lock, if on)
docs/templates/            templates used by `gate.py new`
tests/acceptance/          acceptance tests, one folder per change
tests/sdlc/                tests for the gate tooling itself
evals/                     cases to re-run when rules, skills or hooks change
scripts/gate.py            the gates (standard library only)
.claude/                   hook and slash command for Claude Code
.github/                   CI, CODEOWNERS, PR template
```

## Not covered yet

- **Evals are a format, not a runner.** `evals/` describes how to keep cases; running them
  is up to your harness.
- **Measurement** (lead time, rework, review minutes) is not collected yet.

## License

MIT
