# Contributing

Thanks for helping make Claude sound better. This page covers how to run, check and change the mod. For how it works inside, read [docs/how-it-works.md](docs/how-it-works.md).

## You'll need

- **Claude Code**, a recent version. Mods are early access, and the API changes between releases.
- **macOS** to hear anything. Sound plays through `afplay`; on Linux and Windows the mod loads but stays silent, and the tests still run.
- **Python 3** to regenerate sounds (standard library only).
- **Node and npx**, only for type-checking.

## Run your working copy

Clone the repo and start Claude Code with the mod loaded from your files:

```
git clone https://github.com/hari90/claude_orchestra
cd claude_orchestra
claude --plugin-dir .
```

Saving a file reloads the mod: once the current turn ends if Claude is mid-turn, otherwise after a short pause. You don't need to restart.

### Always on

To have every Claude Code session load your working copy, in any project and without the flag, set `CLAUDE_CODE_PLUGIN_DIRS` in the `env` block of `~/.claude/settings.json`:

```json
{
  "env": { "CLAUDE_CODE_PLUGIN_DIRS": "~/code/claude_orchestra" }
}
```

Use the path to your clone. This is how you live with your changes before they ship. Remove the line to go back to the published version.

### Don't load it twice

If you've also installed `orchestra` from the marketplace, disable it with `/plugin` while you develop. Otherwise both copies run and every tick plays twice. To try the published version again, turn it back on and run `claude plugin update`.

## Check your change

Run all three before opening a pull request:

```
claude plugin validate .        # reads the mod the way the engine will
claude plugin test .            # runs tests/*.test.ts
npx -p typescript@5 tsc -p .    # type-checks hooks and tests
```

Type-checking needs this Claude Code build's API types, which the engine writes to `.claude-plugin/types/` the first time it loads the mod (so run `claude --plugin-dir .` once first). That folder is generated and git-ignored.

Every change in behaviour needs a test in `tests/`. The tests run against the engine's own test kit, with a mocked clock for anything timed; [docs/how-it-works.md](docs/how-it-works.md#tests) explains how they're built.

Then listen: run a session with your copy and give Claude something that thinks, writes and calls a tool.

## Change the sounds

Sounds are synthesized by `tools/make_sounds.py`, not recorded. Edit the script, then regenerate:

```
python3 tools/make_sounds.py
```

Commit the script and the regenerated files in `sounds/` together. Recorded samples are welcome only if their licence allows redistribution under Apache 2.0; say where they came from in your pull request.

## Debug a live session

Start a session with a debug log:

```
claude --plugin-dir . --debug-file /tmp/orchestra.log
```

Every clip shows up as `$.audio.play (orchestra): afplay sounds/...`, and a refused one as `refused: ...`. Hook failures are logged there too, and in the transcript while the mod is hot-reloading.

## Ground rules

- **Mind the four-clip limit.** The engine refuses a mod's fifth simultaneous sound without an error you'd see. Give each kind of sound one voice.
- **Keep the README for users.** Say what the mod does and how to install it there; implementation details go in `docs/`.
- **Keep the name.** Plugin names starting with `claude` or `anthropic` are reserved, so the mod stays `orchestra`.

[AGENTS.md](AGENTS.md) has the same rules in more detail, written for AI agents working in the repo.

## Pull requests

Work on a branch and open a pull request against `main`. Describe what changed and how it sounds now. A short screen recording with audio is the best way to show it.

Releases are cut by bumping `version` in `.claude-plugin/plugin.json`. Installed copies pick that up with `claude plugin update`. Leave the bump to the maintainer unless asked.
