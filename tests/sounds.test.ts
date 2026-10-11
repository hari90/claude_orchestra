import { expect, mock, test, type Engine } from 'claude-code/testing'
import type { On, TurnCompleteInput, TurnStepChunk } from 'claude-code'

const STEP = { turnId: 't1', index: 0, model: 'm', messageCount: 1 }
const DONE: TurnCompleteInput = { turnId: 't1', answer: 'ok', durationMs: 1, isAborted: false, reason: 'answer' }

// How the stand-in for afplay answers: play for a second, refuse, or hang.
type Playback = 'plays' | 'refused' | 'hangs'

// Feeds model responses and turn endings through the mod. Clips "play" on the
// mocked clock, so the test decides when a cue's voice frees up.
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
  on('turn.complete', async () => ({ text: '' }))
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
  const complete = async (e: Partial<TurnCompleteInput> = {}) => {
    await $.turn.complete({ ...DONE, ...e } as TurnCompleteInput)
    await clock.settle()
  }
  const setPlayback = (p: Playback) => (playback = p)
  return { clock, played, logged, stream, complete, setPlayback }
}

const text = (t: string): TurnStepChunk => ({ kind: 'text', index: 0, text: t })
const thinking: TurnStepChunk = { kind: 'thinking', index: 0, text: 'hmm' }
const tool: TurnStepChunk = { kind: 'tool', index: 1, id: 'tu1', name: 'Bash' }

test('Busy Dev is the default: writing plays a typing run, and the stream passes through', async ($, on) => {
  const { played, stream } = harness($, on)
  const chunks = [text('Hello')]
  expect(await stream(chunks)).toEqual(chunks)
  expect(played).toHaveLength(1)
  expect(played[0]).toMatch(/^sounds\/busy-dev\/type[0-3]\.wav$/)
})

test('thinking, a tool call and the end of a turn each have their own sound', async ($, on) => {
  const { played, stream, complete } = harness($, on)
  await stream([thinking, tool])
  await complete()
  expect(played).toHaveLength(3)
  expect(played[0]).toMatch(/^sounds\/busy-dev\/think[0-2]\.wav$/)
  expect(played[1]).toMatch(/^sounds\/busy-dev\/tool[01]\.wav$/)
  expect(played[2]).toBe('sounds/busy-dev/done0.wav')
})

test('whitespace, tool arguments and the stop make no sound', async ($, on) => {
  const { played, stream } = harness($, on)
  await stream([text('  \n'), { kind: 'input', index: 1, json: '{}' }, { kind: 'stop', stopReason: 'end_turn', usage: null }])
  expect(played).toEqual([])
})

test('each cue is one voice: a cue still sounding skips, and plays again once it ends', async ($, on) => {
  const { clock, played, stream } = harness($, on)
  await stream([text('a'), text('b'), text('c'), thinking, thinking])
  expect(played).toHaveLength(2) // one typing run, one thinking sound
  await clock.advance(1000)
  await stream([text('d')])
  expect(played).toHaveLength(3)
})

test('no done sound for a subagent, an interrupted turn or a failed one', async ($, on) => {
  const { played, complete } = harness($, on)
  await complete({ agentId: 'a1' })
  await complete({ isAborted: true, reason: 'aborted' })
  await complete({ reason: 'error' })
  expect(played).toEqual([])
})

for (const pack of ['newsroom', 'in-the-zone', 'lounge', 'vienna'] as const) {
  test(`the ${pack} pack plays its own files`, { options: { pack } }, async ($, on) => {
    const { played, stream, complete } = harness($, on)
    await stream([text('x')])
    await complete()
    expect(played).toHaveLength(2)
    expect(played[0]).toMatch(new RegExp(`^sounds/${pack}/type[0-3]\\.wav$`))
    expect(played[1]).toBe(`sounds/${pack}/done0.wav`)
  })
}

test('the tick pack ticks while Claude works and is quiet when a turn ends', { options: { pack: 'tick' } }, async ($, on) => {
  const { played, stream, complete } = harness($, on)
  await stream([text('x'), thinking, tool])
  await complete()
  expect(played).toEqual(['sounds/tick.wav', 'sounds/tick.wav', 'sounds/tick.wav'])
})

test('None is silent', { options: { pack: 'none' } }, async ($, on) => {
  const { played, stream, complete } = harness($, on)
  await stream([text('hello'), thinking, tool])
  await complete()
  expect(played).toEqual([])
})

test('a refused sound is reported once and does not silence its cue', async ($, on) => {
  const { played, logged, stream, setPlayback } = harness($, on)
  setPlayback('refused')
  await stream([text('a')])
  await stream([text('b')])
  expect(played).toHaveLength(2)
  expect(logged).toHaveLength(1)
  expect(logged[0]).toMatch(/^orchestra: a sound could not play/)
})

test('a sound that never finishes is given up on after three seconds', async ($, on) => {
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
