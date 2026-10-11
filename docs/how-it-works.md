# How it works

claude_orchestra is a Claude Code **mod**: a plugin whose behaviour lives in a TypeScript hooks module the engine runs in its own sandbox (no Node, no DOM; everything outside goes through `$`).

## Layout

```
.claude-plugin/
  plugin.json        the mod's manifest (its name is `orchestra`)
  marketplace.json   makes this repo installable with /plugin install
hooks/
  hooks.json         names the hooks module
  register.ts        the hooks module
sounds/              the clips the mod plays (generated, committed)
assets/              the logo: logo-original.jpeg and the round logo.png cut from it
tools/
  make_sounds.py     synthesizes sounds/ (Python stdlib only)
tests/               `claude plugin test` suites
```

## The hook

`hooks/register.ts` hooks one event, `turn.step`: one model request inside a turn, whose response streams through the hook as chunks. The hook is an async generator. It passes every chunk on unchanged, and for each chunk of the model's output (`text`, `thinking`, `tool`, `input`) it asks for a tick.

`turn.step` also covers subagents' requests, but a session has one tick voice: its main loop and all its subagents share it, so subagents keep the session ticking without making it faster. Parallel *sessions* each have their own voice and do layer.

## Playing sound

`$.audio.play({ asset: 'sounds/tick.wav' })` plays one of the mod's own files. On macOS the engine runs `afplay`; elsewhere it plays nothing.

The engine allows **four clips at once per mod** and refuses the rest. Each clip holds its slot for as long as its `afplay` process runs, which is about half a second even for a 35 ms tick. So the mod plays **one tick at a time**: a chunk that arrives while a tick is still sounding is skipped. In practice that's two or three ticks a second while Claude streams, however fast the text arrives.

Future sound packs should keep the same discipline: give each kind of sound (typing, thinking, tool call, done) its own single voice, and play a pre-rendered *run* of sound rather than many tiny clips.

## Sounds

Sounds are synthesized, not recorded, by `tools/make_sounds.py`, so the repo owns every byte and needs no licences. Regenerate them after editing the script:

```
python3 tools/make_sounds.py
```

Clips are 22.05 kHz, 16-bit mono WAV, normalized to the same peak.

## Tests

The tests (`tests/*.test.ts`) run against the engine's test kit under `claude plugin test .`. They feed fake model responses through `turn.step`, stand in for `audio.play`, and use a mocked clock (`mock.clock(on)`), so a clip "plays" for as long as the test says and a test can make one refused or hung. A test's own hooks can't call `$.clock`; they use the mock clock's `sleep`.

How to run the mod, check it and debug it is in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Naming

The mod's name is `orchestra`, not `claude_orchestra`: `claude plugin validate` refuses a *plugin* name that reads as Anthropic's own, and refused `claude_orchestra`. The rule is about plugin names; the marketplace's name, `claude_orchestra`, validates, and so does the repository's.
