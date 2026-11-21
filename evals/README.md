# Evals

The rules agents follow (AGENTS.md, CLAUDE.md, skills in `.claude/`, hooks) are code too,
and changing them can quietly break behaviour that used to work.

- Keep 20–50 cases here, taken from real past work: a task, the context the agent had, and
  what a good result looks like. Start with five.
- Re-run them whenever a context file, skill or hook changes, and compare with the last run.
- Every incident adds a case.

Files here count as rule files, not docs: changing a case needs the full loop (see
AGENTS.md), because evals decide whether an agent passes.

Write each case as a file in `cases/` using `cases/_template.md`. Running them is up to your
harness; record the results with the PR that changed the rules.
