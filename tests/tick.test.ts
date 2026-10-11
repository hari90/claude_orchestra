import { expect, mock, test, type Engine } from 'claude-code/testing'
import type { On, TurnStepChunk } from 'claude-code'

const STEP = { turnId: 't1', index: 0, model: 'm', messageCount: 1 }

// How the stand-in for afplay answers: play for a second, refuse, or hang.
type Playback = 'plays' | 'refused' | 'hangs'

// Feeds model responses through the mod. Clips "play" on the mocked clock, so
// the test decides when the next one may start.
function harness($: Engine, on: On) {
  const clock = mock.clock(on)
  const played: string[] = []
  const logged: string[] = []
  let playback: Playback = 'plays'
  on('audio.play', async (_$, e) => {
    if (e.clip.asset) played.push(e.clip.asset)
    if (playback === 'refused') return { deny: 'no such asset' }
    await clock.sleep(playback === 'hangs' ? 60_000 : 1000)
    return { value: undefined }
  })
  on('ui.log', async (_$, e) => {
    logged.push(e.text)
    return { value: undefined }
  })
  let chunks: TurnStepChunk[] = []
  on('turn.step', async function* () {
    for (const c of chunks) yield c
    return { turnId: 't1', index: 0, answer: '', toolUses: [], stopReason: 'end_turn', usage: null }
  })
  const stream = async (next: TurnStepChunk[]) => {
    chunks = next
    const seen: TurnStepChunk[] = []
    for await (const c of $.turn.step(STEP)) seen.push(c)
    await clock.settle()
    return seen
  }
  const setPlayback = (p: Playback) => (playback = p)
  return { clock, played, logged, stream, setPlayback }
}

const text = (t: string): TurnStepChunk => ({ kind: 'text', index: 0, text: t })

test('a streamed response ticks and passes through unchanged', async ($, on) => {
  const { played, stream } = harness($, on)
  const chunks = [text('Hello')]
  expect(await stream(chunks)).toEqual(chunks)
  expect(played).toEqual(['sounds/tick.wav'])
})

test('thinking, tool calls and tool arguments tick too', async ($, on) => {
  const { clock, played, stream } = harness($, on)
  const chunks: TurnStepChunk[] = [
    { kind: 'thinking', index: 0, text: 'hmm' },
    { kind: 'tool', index: 1, id: 'tu1', name: 'Bash' },
    { kind: 'input', index: 1, json: '{"command":"ls"}' },
  ]
  for (const c of chunks) {
    await stream([c])
    await clock.advance(1000)
  }
  expect(played).toHaveLength(3)
})

// `engine` chunks are skipped the same way, but only the engine can make one,
// so a test cannot feed them.
test('the stop does not tick', async ($, on) => {
  const { played, stream } = harness($, on)
  const chunks: TurnStepChunk[] = [{ kind: 'stop', stopReason: 'end_turn', usage: null }]
  expect(await stream(chunks)).toEqual(chunks)
  expect(played).toEqual([])
})

test('one tick at a time: chunks arriving mid-tick are skipped, the next tick follows', async ($, on) => {
  const { clock, played, stream } = harness($, on)
  await stream([text('a'), text('b'), text('c')])
  expect(played).toHaveLength(1)
  await clock.advance(1000)
  await stream([text('d')])
  expect(played).toHaveLength(2)
})

test('a refused tick is reported once and does not silence the mod', async ($, on) => {
  const { played, logged, stream, setPlayback } = harness($, on)
  setPlayback('refused')
  await stream([text('a')])
  await stream([text('b')])
  expect(played).toHaveLength(2)
  expect(logged).toHaveLength(1)
  expect(logged[0]).toMatch(/^orchestra: a tick could not play/)
})

test('a tick that never finishes is given up on after three seconds', async ($, on) => {
  const { clock, played, stream, setPlayback } = harness($, on)
  setPlayback('hangs')
  await stream([text('a')])
  await clock.advance(2000)
  await stream([text('b')])
  expect(played).toHaveLength(1)
  await clock.advance(1000)
  await stream([text('c')])
  expect(played).toHaveLength(2)
})
