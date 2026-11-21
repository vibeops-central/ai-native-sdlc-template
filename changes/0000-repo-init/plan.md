# Plan: 0000-repo-init

Do these in one pull request, after you make the repo from the template.

1. `changes/0000-repo-init/intent.md`: your handle and the date.
2. `.github/CODEOWNERS`: replace `@YOUR-HANDLE`, and uncomment the owner lines.
3. `AGENTS.md`: add your project rules below the marker line.
4. GitHub settings: require the `gates` status check on `main`.
5. `intent.md` and `spec.md`: set `Status: approved`.
6. Run `python scripts/gate.py check` and `python scripts/gate.py test`. Both must pass.

## Files
- `changes/0000-repo-init/intent.md`, `spec.md`
- `.github/CODEOWNERS`
- `AGENTS.md`
