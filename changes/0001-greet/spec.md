# Spec: 0001-greet

Status: draft
<!-- draft -> approved (a human sets this, then runs `python scripts/gate.py lock 0001-greet`) -> done -->

## Behaviour
`greet(name: str) -> str` returns `"Hello, <name>!"`, with surrounding spaces removed from
the name.

## Edge cases
- An empty name, or one made only of spaces, raises `ValueError`.
- Inner spaces are kept: `"Ada Lovelace"` stays as it is.

## Acceptance tests
Each one maps to a test in `tests/acceptance/0001-greet/`.

| # | Given / when / then | Test |
|---|---|---|
| 1 | Given "Ada", greet returns "Hello, Ada!" | `test_greets_by_name` |
| 2 | Given "  Ada  ", the spaces are trimmed | `test_trims_spaces` |
| 3 | Given "Ada Lovelace", inner spaces are kept | `test_keeps_inner_spaces` |
| 4 | Given "" or "   ", greet raises ValueError | `test_rejects_blank_names` |

## Open questions
None.
