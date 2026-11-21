# Plan: 0002-change-classes

Keep this true. If the work drifts from the plan, update it in the same commit.

## Steps
1. Add `pr-check` to `scripts/gate.py`: list changed files with `git diff --name-only`,
   classify them, and check every changed change folder with the existing `check_change`
   plus an approved-status check.
2. Add a `Risk:` line to `docs/templates/spec.md`.
3. Add a "Change classes" section to `AGENTS.md`.
4. Update the first block rule in `REVIEW.md` and add a class check.
5. Run `pr-check` in CI on pull requests (`fetch-depth: 0` so the base branch exists).
6. Mention the classes in the README table of what is enforced.

## Files touched
- `scripts/gate.py`
- `docs/templates/spec.md`
- `AGENTS.md`, `REVIEW.md`, `README.md`
- `.github/workflows/sdlc-gates.yml`

## Risks
- A path classified wrongly lets a code change merge as docs. Mitigation: the docs list is
  short and explicit; anything unknown is treated as code.
