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
sounds/              the clips the mod plays (committed)
  <pack>/            one folder per pack: type0-3, think0-2, tool0-1, done0
  tick.wav           the tick pack's one sound
  CREDITS.md         where each recording came from, and its licence
assets/              the logo: logo-original.jpeg and the round logo.png cut from it
tools/
  cut_recordings.py  cuts the packs out of their source recordings (stdlib only)
  make_sounds.py     synthesizes tick.wav (stdlib only)
tests/               `claude plugin test` suites
```

## The hooks

`hooks/register.ts` reads the **Sound pack** option (`userConfig.pack` in `plugin.json`, default `busy-dev`) and plays four cues from that pack's folder:

| Cue | When | Event |
|---|---|---|
| `type` | a chunk of reply text arrives (not whitespace) | `turn.step`, `text` chunk |
| `think` | a chunk of thinking arrives | `turn.step`, `thinking` chunk |
| `tool` | the model starts a tool call | `turn.step`, `tool` chunk |
| `done` | the main conversation's turn ends normally | `turn.complete` |

`turn.step` is one model request inside a turn, whose response streams through the hook as chunks; the hook is an async generator that passes every chunk on unchanged. `done` skips a subagent's run (`agentId` set), a turn interrupted with Esc (`isAborted`) and one that ended on an error (`reason` other than `answer`).

Each cue picks one of its variants at random (`type0`-`type3`, `think0`-`think2`, `tool0`-`tool1`, `done0`). The `tick` pack plays `sounds/tick.wav` for every cue but `done`. Choosing `none` registers no hooks at all.

`turn.step` also covers subagents' requests, but they share the session's voices, so subagents keep a session busy without making it louder. Parallel *sessions* each have their own voices and do layer.

## Playing sound

`$.audio.play({ asset })` plays one of the mod's own files. On macOS the engine runs `afplay`; elsewhere it plays nothing.

The engine allows **four clips at once per mod** and refuses the rest. Each clip holds its slot for as long as its `afplay` process runs. So **each cue is one voice**: a cue whose last clip is still sounding is skipped, and the four cues can never ask for a fifth slot. That is also why `type` is a pre-rendered *run* of about a second of typing, not one clip per keystroke: text streams in pieces faster than `afplay` can start.

A play that hasn't settled after three seconds frees its voice anyway, so a hung `afplay` can't silence a cue for the rest of the session. The first clip that fails to play is reported once in the transcript.

## Sounds

The packs are **cut from real recordings** shared on Freesound; [sounds/CREDITS.md](../sounds/CREDITS.md) lists each one and its licence. The recordings aren't in the repository: `tools/cut_recordings.py` holds the exact times of every cut and rebuilds the packs from them.

```
python3 tools/cut_recordings.py --typewriter typewriter.wav --laptop laptop.wav \
  --mechanical keyboard.wav --piano piano.wav --orchestra orchestra.wav
```

How each kind of recording is cut:

- **Keyboards** (Busy Dev, Newsroom, In the Zone): typing runs from the densest stretches; thinking is two single keys taken from real typing, each with nothing after it; tool calls and done are the deepest, loudest presses (Enter, the spacebar, the carriage return, the bell). A soft limiter rounds off the sharpest strikes so typing is as loud overall as the music packs. The laptop recording is gated between keystrokes to keep its hiss down; the typewriter's bell, which always rang over a keystroke, is filtered down to its two partials.
- **Music** (Lounge, Vienna): typing is a lively passage, thinking a soft one, tool calls a single accent, and done the piece's own ending, each faded at both ends.

Every clip's peak is set by its cue (typing 0.7, thinking 0.4, tool 0.8, done 0.5), then scaled by `MASTER` (0.25) in both scripts. Change `MASTER` to make everything louder or quieter. Clips are 16-bit mono WAV at the recording's own sample rate.

`tools/make_sounds.py` synthesizes the one sound that isn't recorded: `tick.wav`.

## Tests

The tests (`tests/*.test.ts`) run against the engine's test kit under `claude plugin test .`. They feed fake model responses through `turn.step` and turn endings through `turn.complete`, run each pack through the `pack` option, stand in for `audio.play`, and use a mocked clock (`mock.clock(on)`), so a clip "plays" for as long as the test says and a test can make one refused or hung. A test's own hooks can't call `$.clock`; they use the mock clock's `sleep`.

How to run the mod, check it and debug it is in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Naming

The mod's name is `orchestra`, not `claude_orchestra`: `claude plugin validate` refuses a *plugin* name that reads as Anthropic's own, and refused `claude_orchestra`. The rule is about plugin names; the marketplace's name, `claude_orchestra`, validates, and so does the repository's.
