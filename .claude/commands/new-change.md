---
description: Start a new change following the AI-native SDLC loop
argument-hint: <short-slug> <what you want, in a sentence>
---

1. Run `python scripts/gate.py new <slug>` using the first word of: $ARGUMENTS
2. Draft `intent.md` from the rest of the request. Ask me about anything you would
   otherwise have to guess, then wait for me to confirm the intent.
3. Once I confirm, draft `spec.md` and the acceptance tests in `tests/acceptance/<change>/`.
   Leave `Status: draft`.
4. Stop. Tell me what to review. I approve the spec and run the lock myself.
