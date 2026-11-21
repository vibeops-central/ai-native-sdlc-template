# Plan: 0003-pr-check-gaps

Keep this true. If the work drifts from the plan, update it in the same commit.

## Steps
1. `scripts/gate.py`:
   - `intent_status()` and `has_owner()` helpers.
   - `check_change`: when the spec is approved or done, the intent must be approved or done
     and must name an `@owner`.
   - `pr-check`: count only change folders that exist at `HEAD`; fail with "deleted folders
     don't count" when none is left.
2. `docs/templates/intent.md`: add `Status: draft`. Update the comment in
   `docs/templates/spec.md`.
3. Existing changes: `Status: approved` in 0002's intent (recording Natu's 21 Nov approval,
   confirmed by approving this spec); `Status: draft` in 0001's intent.
4. AGENTS.md step 2 and REVIEW.md: approving a change means approving the intent and the
   spec.
5. Update the test helpers in `tests/sdlc/test_gates.py` that approve a spec, so they also
   approve the intent.
6. Run all tests and the gates.

## Files touched
- `scripts/gate.py`
- `docs/templates/intent.md`, `docs/templates/spec.md`
- `changes/0001-greet/intent.md`, `changes/0002-change-classes/intent.md`
- `AGENTS.md`, `REVIEW.md`
- `tests/sdlc/test_gates.py`

## Risks
- **Change 0002's approved acceptance tests** create changes with an approved spec and a
  template intent. If the new rule makes them fail, they cannot be edited without a human
  agreeing (AGENTS.md hard rule). Stop and ask before touching them.
