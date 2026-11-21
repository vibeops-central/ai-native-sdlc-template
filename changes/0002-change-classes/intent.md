# Intent: 0002-change-classes

Status: approved
<!-- Recorded by change 0003: Natu approved 0002 on 21 Nov 2026, before intents had a status. -->
**Owner (human):** @nlauchande (agreed in chat, 21 Nov 2026)
**Date:** 2026-11-21

## Problem
AGENTS.md says every change needs an intent, spec and plan. A README typo fix then needs the
same ceremony as a new feature. Anthropic's AI-native SDLC playbook does not define change
classes; it leaves "what counts as higher risk" to each organization.

## Outcome
- Three change classes, written down in AGENTS.md: docs-only, routine, higher risk.
- Docs-only changes need a reviewed PR but no change folder.
- The files that steer the agent (AGENTS.md, CLAUDE.md, REVIEW.md, `.claude/`, the gate,
  CI, the templates) never count as docs.
- CI checks every PR: a PR that changes anything other than docs must include a change
  whose spec is approved.
- **Added 21 Nov (Natu, in chat):** the acceptance-test lock becomes optional and off by
  default. The default follows Anthropic's playbook as written; the lock is a VibeOps
  experiment to turn on later and compare against the baseline. With the lock off, edits to
  approved acceptance tests are warned about and logged, not blocked.

## Out of scope
Detecting "higher risk" automatically. A human sets it in the spec.

## Constraints
Standard library only. Works on GitHub Actions pull requests.
