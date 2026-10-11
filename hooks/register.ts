import type { EngineInterface, Register } from 'claude-code'

type Cue = 'type' | 'think' | 'tool' | 'done'

// The packs a person can pick: each a folder under sounds/, and "tick", the
// original single sound. "none" is silence.
const PACKS = ['busy-dev', 'newsroom', 'in-the-zone', 'lounge', 'vienna', 'tick'] as const
// How many variants of each cue every pack has (sounds/<pack>/<cue><n>.wav).
const VARIANTS: Record<Cue, number> = { type: 4, think: 3, tool: 2, done: 1 }
// A play that has not settled by then is given up on, so a hung afplay or a
// lost promise can never silence a cue for the rest of the session.
const STUCK_MS = 3000

let pack: string = 'busy-dev'
// The engine lets a mod play four clips at once and refuses the rest, so each
// cue is one voice: a cue still sounding skips, and four cues never collide.
// Each holds the id of the play holding it, or 0 when free.
const sounding: Record<Cue, number> = { type: 0, think: 0, tool: 0, done: 0 }
let lastId = 0
let hasReportedError = false

function report($: EngineInterface, err: unknown): void {
  if (hasReportedError) return
  hasReportedError = true
  $.ui.log(`orchestra: a sound could not play: ${String(err)}`)
}

// The file a cue plays in the chosen pack, or undefined for none: the tick
// pack ticks while Claude works and stays quiet when a turn ends.
function asset(cue: Cue): string | undefined {
  if (pack === 'tick') return cue === 'done' ? undefined : 'sounds/tick.wav'
  return `sounds/${pack}/${cue}${Math.floor(Math.random() * VARIANTS[cue])}.wav`
}

function play($: EngineInterface, cue: Cue): void {
  const file = asset(cue)
  if (!file || sounding[cue]) return
  const id = ++lastId
  sounding[cue] = id
  const release = () => {
    if (sounding[cue] === id) sounding[cue] = 0
  }
  $.clock.after(STUCK_MS, release)
  try {
    void $.audio
      .play({ asset: file })
      .catch(err => report($, err))
      .finally(release)
  } catch (err) {
    report($, err)
    release()
  }
}

export const register: Register = (on, options) => {
  const choice = String(options.pack ?? 'busy-dev')
  if (!(PACKS as readonly string[]).includes(choice)) return // "none": no hooks, no sound
  pack = choice

  // The model's response as it streams: writing, thinking, starting a tool call.
  on('turn.step', async function* ($, e, next) {
    const stream = next(e)
    for await (const chunk of stream) {
      if (chunk.kind === 'text' && chunk.text.trim()) play($, 'type')
      else if (chunk.kind === 'thinking') play($, 'think')
      else if (chunk.kind === 'tool') play($, 'tool')
      yield chunk
    }
    return stream.result
  })

  // The main conversation's turn ending normally; not a subagent's, not an Esc.
  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined && !e.isAborted && e.reason === 'answer') play($, 'done')
    return next(e)
  })
}
