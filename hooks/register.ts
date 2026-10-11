import type { EngineInterface, Register } from 'claude-code'

// A play that has not settled by then is given up on, so a hung afplay or a
// lost promise can never silence the mod for the rest of the session.
const STUCK_MS = 3000

// The engine lets a mod play four clips at once and refuses the rest, and each
// clip holds its slot for as long as afplay runs (about half a second), so one
// tick plays at a time: a tick still sounding skips the next.
let isTicking = false
// Which tick holds the voice, so a late release of an earlier one is ignored.
let tickId = 0
let hasReportedError = false

function report($: EngineInterface, err: unknown): void {
  if (hasReportedError) return
  hasReportedError = true
  $.ui.log(`orchestra: a tick could not play: ${String(err)}`)
}

function tick($: EngineInterface): void {
  if (isTicking) return
  isTicking = true
  const id = ++tickId
  const release = () => {
    if (tickId === id) isTicking = false
  }
  $.clock.after(STUCK_MS, release)
  try {
    void $.audio
      .play({ asset: 'sounds/tick.wav' })
      .catch(err => report($, err))
      .finally(release)
  } catch (err) {
    report($, err)
    release()
  }
}

export const register: Register = on => {
  // Ticks while the model streams: thinking, text and tool calls alike.
  on('turn.step', async function* ($, e, next) {
    const stream = next(e)
    for await (const chunk of stream) {
      if (chunk.kind !== 'engine' && chunk.kind !== 'stop') tick($)
      yield chunk
    }
    return stream.result
  })
}
