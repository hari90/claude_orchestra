# AGENTS.md

Notes for AI agents (Claude Code and others) working in this repository.

## What this is

A Claude Code mod named `orchestra` that plays sounds while Claude works. The repository root *is* the mod, and also a one-plugin marketplace. Read [docs/how-it-works.md](docs/how-it-works.md) before changing anything, and [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow.

## Commands

```
claude plugin validate .        # must pass before any commit
claude plugin test .            # tests/*.test.ts
npx -p typescript tsc -p .      # needs .claude-plugin/types/, written when the engine first loads the mod
python3 tools/make_sounds.py    # regenerate sounds/ after editing the script
claude --plugin-dir .           # run a session with the working copy loaded
```

## Rules

- **The hooks module runs in a sandbox**: no Node, no DOM, no `require`, no dynamic `import()`. Reach the outside only through `$`. When `$` is passed to a helper, the helper must be a top-level function declaration in the same file, or validation fails.
- **The API types are the reference.** Grep `.claude-plugin/types/claude-code/index.d.ts` for an event or noun rather than guessing. The API is early access and changes between releases.
- **Respect the four-clip limit.** The engine refuses a mod's fifth simultaneous clip without an error you'd see. Give each kind of sound one voice, and prefer one pre-rendered run over many short clips.
- **Sounds are synthesized** by `tools/make_sounds.py` (stdlib only). Don't add recorded samples unless their licence allows redistribution under Apache 2.0, and note the source.
- **Don't rename the mod** to anything starting with `claude`, `anthropic` or `cc-plugin`: those names are reserved and validation fails.
- **Keep the README non-technical.** It says what the mod does and how to install it. Implementation details go in `docs/`.
- **Every behaviour change gets a test** in `tests/`. Use the mocked clock (`mock.clock(on)`) for anything timed. A test's own hooks can't call `$.clock`; use the mock clock's `sleep`.
- Don't commit `.claude-plugin/types/`; it's generated and git-ignored.
