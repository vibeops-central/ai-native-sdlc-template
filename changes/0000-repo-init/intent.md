# Intent: 0000-repo-init

Status: draft
<!-- Do this change when you make a repo from the template. Fill in the owner and date,
     do the plan, then set Status: approved here and in spec.md. -->
**Owner (human):** @
**Date:**

## Problem
A repo made from the AI-native SDLC template has no human owner yet. Its rule files
(AGENTS.md, REVIEW.md, the gates) have nobody to approve changes to them, and the gates
are not enforced on `main`.

## Outcome
- A named human owns the repo. The intent names them, and `.github/CODEOWNERS` gives them
  the rule files and the acceptance tests.
- `AGENTS.md` has this project's own rules below the marker line.
- Branch protection on `main` requires the `gates` status check.
- `python scripts/gate.py test` passes this change's acceptance tests.

## Out of scope
- Product code. Your first real change is 0001.
- Changes to `scripts/`, `docs/templates/` or the gates.

## Constraints
- This folder stays in the repo as the record of who adopted the process, and when.
