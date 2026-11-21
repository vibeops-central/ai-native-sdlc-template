# Intent: 0003-pr-check-gaps

Status: draft
**Owner (human):** @nlauchande (asked for in chat, 21 Nov 2026; drafted by the agent)
**Date:** 2026-11-21

## Problem
Two gaps found after change 0002 merged:

1. **Deleted change folders count as a change.** `gate.py pr-check` passes a PR if it touches
   any folder under `changes/`. A deleted folder still appears in the list of changed
   files, and its missing spec is then skipped. So a PR can bundle unrelated code with
   "delete an old change folder" and pass without any approved spec.
2. **Nothing checks the intent.** The only human gate is approving the spec. An agent
   writes `intent.md` from what the human said, and nothing records that the human
   confirmed it. If the intent is wrong or invented, the only safeguard is the human
   noticing it while reviewing the spec.

## Outcome
- A PR that changes anything other than docs must include at least one change folder that
  **still exists** after the PR, with its spec approved. Deleted folders never satisfy this.
- Approving a change means approving **both** the intent and the spec. `intent.md` gets a
  `Status:` line. An approved spec with a draft intent fails the gate, and an approved
  intent must name a human owner.

## Out of scope
- Proving that a human, not an agent, set the status. GitHub sees accounts, not people;
  that needs separate agent identities (see the open question in the spec).
- The cleanup of change 0002 (a later change).

## Constraints
Standard library only. Must not break change 0001 (draft) or change 0002 (approved, merged).
