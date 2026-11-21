# AI-native SDLC template

A minimal starting point for building software with coding agents, following Anthropic's
AI-native SDLC playbook. Part of [VibeOps](https://vibeopscentral.ai/).

Writing code is no longer the slow part. Checking it is. This template keeps the checking
honest: every change is a short trail of files a human can review, and the gates that matter
are enforced, not left to a prompt.

## The loop

```
intent.md → spec.md + acceptance tests → (human approves, locks) → plan.md → build → review
```

| Step | File | Who |
|---|---|---|
| Intent | `changes/NNNN-slug/intent.md` | Human writes or confirms |
| Spec | `changes/NNNN-slug/spec.md` + `tests/acceptance/NNNN-slug/` | Agent drafts, **human approves** |
| Lock | `changes/NNNN-slug/acceptance.lock` | **Human only** |
| Plan | `changes/NNNN-slug/plan.md` | Agent, kept in sync with the diff |
| Build | your code | Agent |
| Review | the PR, against `REVIEW.md` | Another agent, then a named human |

## What is enforced, and what is advice

| Rule | How |
|---|---|
| Every change has an intent and a spec with a status | CI: `gate.py check` |
| An approved spec has a plan and locked acceptance tests | CI: `gate.py check` |
| Approved acceptance tests can't change without a human | CI (hash in `acceptance.lock`) + CODEOWNERS |
| The agent can't edit approved tests or the lock, or run the lock | Claude Code hook (`.claude/hooks/`) |
| Approved acceptance tests pass | CI: `gate.py test` |
| Plan matches the diff, scope, evidence of "done" | Review, against `REVIEW.md` |

The hook covers Claude Code's file tools and obvious shell commands; it is a guardrail, not
a sandbox. CI is the gate that counts.

## Try it (about 10 minutes)

The repo ships one worked example, `0001-greet`, waiting for approval.

1. **Read the intent and spec** in `changes/0001-greet/`, and the drafted acceptance tests in
   `tests/acceptance/0001-greet/`.
2. **Approve it** (you, the human): set `Status: approved` in `spec.md`, then run
   ```bash
   python scripts/gate.py lock 0001-greet
   ```
3. **Ask your agent to build it**: "Build change 0001-greet." Then try "the tests are too
   strict, loosen them". The hook should refuse.
4. **Check the gates**:
   ```bash
   python scripts/gate.py check
   python scripts/gate.py test
   ```
5. **Open a PR** and review it against `REVIEW.md`.

When you start your own project, delete `changes/0001-greet/`, `tests/acceptance/0001-greet/`
and `src/example/`.

## Start a change

```bash
python scripts/gate.py new export-csv
```

In Claude Code: `/new-change export-csv let users download their invoices as CSV`.

## Set up a new repo from this template

1. **Use this template** on GitHub.
2. Replace `@nlauchande` in `.github/CODEOWNERS` with your user or team.
3. In branch protection for `main`: require the **SDLC gates** check and **review from Code
   Owners**.
4. Add your own rules at the bottom of `AGENTS.md`.

## Files

```
AGENTS.md / CLAUDE.md      rules every agent follows (CLAUDE.md imports AGENTS.md)
REVIEW.md                  the review policy
changes/                   one folder per change: intent, spec, plan, lock
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
