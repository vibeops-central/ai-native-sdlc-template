# Project name

> **Made from the [AI-native SDLC template](https://github.com/vibeops-central/ai-native-sdlc-template).**
> To set up your repo, follow
> [Set up a new repo from this template](docs/sdlc.md#set-up-a-new-repo-from-this-template)
> (the setup is change `0000-repo-init`).
> To see the process work, follow [Try it](docs/sdlc.md#try-it-about-10-minutes).
> Then delete this note and write your project's README below.

One or two sentences: what this project does, and for whom.

## How we work

Every change goes through intent, spec, plan, build and review, with gates in CI.

- [`docs/sdlc.md`](docs/sdlc.md): how the process works
- [`AGENTS.md`](AGENTS.md): the rules every coding agent follows
- [`REVIEW.md`](REVIEW.md): how changes are reviewed

```bash
python scripts/gate.py new <slug>   # start a change
python scripts/gate.py check        # the SDLC gates (what CI runs)
python -m pytest                    # all tests
```

## License

MIT
