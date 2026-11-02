import { describe, expect, test } from 'claude-code/testing'

import { DAY, rollup, sessionKey, type DashEvent } from '../hooks/collector-logic'
import { T, actOn, candidates, coreShape, listed, mergeSuggestions, parseSuggestions, pickNote, serializeSuggestions, type Suggestion } from '../hooks/suggest-logic'

const NOW = Date.UTC(2026, 9, 8, 12)
const s = (n: number) => sessionKey(`session-${n}`)
const cmd = (shape: string, n: number, sessions: number, ago = DAY): DashEvent[] =>
  Array.from({ length: n }, (_, i) => ({ t: NOW - ago - i * 1000, s: s(i % sessions), k: 'cmd', shape }) as DashEvent)
const perm = (shape: string, n: number): DashEvent[] =>
  Array.from({ length: n }, (_, i) => ({ t: NOW - DAY - i, s: s(i % 3), k: 'prompt', shape }) as DashEvent)
const cands = (events: DashEvent[]) => candidates(events, rollup(events, { now: NOW, recording: true }), NOW)
const keys = (events: DashEvent[]) => cands(events).map(c => c.key)
const row = (key: string, kind: Suggestion['kind'], state: Suggestion['state'], count = 1): Suggestion => ({ key, kind, title: key, evidence: 'e', action: 'a', id: key.slice(-6), state, createdAt: NOW, stateAt: NOW, lastSeen: NOW, count })

describe('thresholds', () => {
  test('the same job 20 times in 5 sessions in 7 days, and not one short of any of them', () => {
    expect(keys(cmd('npm run build', T.cmdTimes, T.cmdSessions))).toEqual(['command:npm run build'])
    expect(keys(cmd('npm run build', T.cmdTimes - 1, T.cmdSessions))).toEqual([])
    expect(keys(cmd('npm run build', T.cmdTimes, T.cmdSessions - 1))).toEqual([])
    expect(keys(cmd('npm run build', T.cmdTimes, T.cmdSessions, (T.cmdDays + 1) * DAY))).toEqual([])
  })
  test('the same permission dialog shown to you 3 times in 7 days suggests a decision, never an allow', () => {
    const shown = (n: number, ago = DAY, k: 'prompt' | 'perm' = 'prompt') => Array.from({ length: n }, (_, i) => ({ t: NOW - ago - i, s: s(0), k, shape: 'bash docker compose' }) as DashEvent)
    expect(keys(shown(3))).toEqual(['prompt:bash docker compose'])
    expect(keys(shown(2))).toEqual([])
    expect(keys(shown(3, 8 * DAY))).toEqual([])
    expect(cands(shown(3))[0]!.action).toMatch(/gatewarden.*writes and allows nothing/)
    expect(keys(shown(9, DAY, 'perm'))).toEqual([])
    expect(keys(perm('askuserquestion', 9))).toEqual([])
  })
  test('skills listed 30 days with no fire are one card, however many there are', () => {
    const listedLong: DashEvent[] = [{ t: NOW - 31 * DAY, s: s(0), k: 'listed', skills: ['a', 'b', 'c', 'd', 'e'] }, { t: NOW - DAY, s: s(0), k: 'listed', skills: ['a', 'b', 'c', 'd', 'e'] }]
    const c = cands(listedLong)
    expect(c.map(x => x.key)).toEqual(['unused:skills'])
    expect(c[0]!.title).toBe('5 skills never fired in 30 days')
    expect(c[0]!.evidence).toBe('a, b, c and 2 more')
    expect(keys([{ t: NOW - 29 * DAY, s: s(0), k: 'listed', skills: ['quiet'] }])).toEqual([])
  })
  test('a skill fired by slash more than 70% of the time: rewrite its description', () => {
    const fires = (slash: number, auto: number): DashEvent[] => [
      ...Array.from({ length: slash }, (_, i) => ({ t: NOW - i * 1000, s: s(0), k: 'skill', skill: 'loud', via: 'slash' }) as DashEvent),
      ...Array.from({ length: auto }, (_, i) => ({ t: NOW - i * 1000, s: s(1), k: 'skill', skill: 'loud', via: 'auto' }) as DashEvent),
    ]
    expect(keys(fires(4, 1))).toEqual(['description:loud'])
    expect(keys(fires(7, 3))).toEqual([])
    expect(keys(fires(4, 0))).toEqual([])
  })
  test('context past 80% twice in a day: suggest a slim', () => {
    expect(keys([{ t: NOW - 1000, s: s(0), k: 'ctx80' }, { t: NOW - 2000, s: s(1), k: 'ctx80' }])).toEqual(['slim:context'])
    expect(keys([{ t: NOW - 1000, s: s(0), k: 'ctx80' }])).toEqual([])
  })
  test('a skill whose turns cost 1.5x the turns without it: slim it; one merely loaded every turn: nothing', () => {
    const turns = (skill: string | null, n: number, each: number): DashEvent[] =>
      Array.from({ length: n }, (_, i) => ({ t: NOW - 1000 - i, s: s(0), k: 'turn', skill, input: each, output: 0, cacheRead: 0, cacheWrite: 0, cost: null }) as DashEvent)
    const heavy = cands([...turns('heavy', 10, 20_000), ...turns(null, 20, 10_000)])
    expect(heavy.map(c => c.key)).toEqual(['heavy:heavy'])
    expect(heavy[0]!.evidence).toBe('its turns average 2.0x the tokens of turns without it (10 turns this week)')
    expect(keys([...turns('everywhere', 27, 10_000), ...turns(null, 3, 10_000)])).toEqual([])
    expect(keys([...turns('heavy', 4, 50_000), ...turns(null, 20, 10_000)])).toEqual([])
    expect(keys([...turns('heavy', 10, 2_000), ...turns(null, 20, 1_000)])).toEqual([])
  })
})

describe('the same work is one row (bug: 187 open rows, each a chain variant)', () => {
  test('coreShape drops cd, read-only steps, closers and repeats', () => {
    expect(coreShape('cd ; python -m unittest ; tail')).toBe('python -m unittest')
    expect(coreShape('python -m unittest ; grep -E ; head')).toBe('python -m unittest')
    expect(coreShape('seq ; for ; grep -q ; done')).toBe('')
    expect(coreShape('npm test ; sleep ; npm test')).toBe('npm test')
  })
  test('every variant of a chain counts toward one job', () => {
    const events = [...cmd('cd ; python -m unittest ; tail', 8, 5), ...cmd('python -m unittest ; grep -E', 7, 5), ...cmd('cd ; for ; python -m unittest', 5, 5)]
    const c = cands(events)
    expect(c.map(x => x.key)).toEqual(['command:python -m unittest'])
    expect(c[0]!.count).toBe(20)
  })
  test('a step that names no job never makes a row, however often it runs', () => {
    for (const shape of ['cd ; git add ; git commit -m -q', 'cd ; git status --short ; head', 'python *.py', 'python -c', 'cd ; python *.py ; echo', 'cd ; sed -n ; grep -n', 'git status', 'seq ; for ; grep -q']) {
      expect(keys(cmd(shape, 200, 9))).toEqual([])
    }
  })
  test('the queue the owner saw heals itself: old chain rows leave, settled rows stay', () => {
    const old = ['command:cd ; git add ; git commit -m -q', 'command:cd ; python -m unittest ; tail', 'command:seq ; for ; grep -q', 'allow:bash cd ; sed -n', 'slim:task-observer', 'unused:quiet'].map((k, i) => row(k, 'command', 'new', 100 - i))
    expect(mergeSuggestions(old, [], NOW + 1000)).toEqual([])
    const settled = row('allow:bash cd ; git', 'allow', 'dismissed')
    expect(mergeSuggestions([settled], [], NOW + 1000)).toEqual([settled])
  })
})

describe('the queue never tops out (bug: the cap filled and dismissals fell off)', () => {
  const many = Array.from({ length: 40 }, (_, i) => perm(`bash tool-${i}`, 3 + i)).flat()
  test('at most maxOpen open rows, strongest first', () => {
    const rows = mergeSuggestions([], cands(many), NOW)
    expect(rows.length).toBe(T.maxOpen)
    expect(rows[0]!.key).toBe('prompt:bash tool-39')
  })
  test('a prompt beats a command with more runs: an interruption ranks first', () => {
    const rows = listed(mergeSuggestions([], cands([...cmd('npm run build', 500, 9), ...perm('bash docker compose', 3)]), NOW))
    expect(rows.map(r => r.kind)).toEqual(['prompt', 'command'])
  })
  test('dismissing the whole queue holds, and the next ones take their places', () => {
    let rows = mergeSuggestions([], cands(many), NOW)
    const gone: string[] = []
    for (let i = 0; i < 3; i++) {
      const r = actOn(rows, 'dismiss', '1', NOW)
      gone.push(r.hit!.key)
      rows = r.rows
      rows = mergeSuggestions(rows, cands(many), NOW + 1000)
    }
    expect(rows.filter(r => r.state === 'dismissed').map(r => r.key).sort()).toEqual([...gone].sort())
    expect(rows.filter(r => r.state === 'new').length).toBe(T.maxOpen)
  })
  test('a full queue never pushes a dismissal out', () => {
    let rows = actOn(mergeSuggestions([], cands(many), NOW), 'dismiss', '1', NOW).rows
    for (let i = 1; i < 20; i++) rows = mergeSuggestions(rows, cands(many), NOW + i * 1000)
    expect(rows.filter(r => r.state === 'dismissed').length).toBe(1)
  })
  test('an open row with no fresh evidence leaves after the stale window', () => {
    const rows = mergeSuggestions([], cands(perm('bash cd ; git push', 9)), NOW)
    expect(mergeSuggestions(rows, [], NOW + T.staleDays * DAY).length).toBe(1)
    expect(mergeSuggestions(rows, [], NOW + (T.staleDays + 1) * DAY).length).toBe(0)
  })
})

describe('acting on a card', () => {
  const base = cands(perm('bash docker compose', 5))
  test('a candidate seen again updates its row; it never doubles', () => {
    const rows = mergeSuggestions(mergeSuggestions([], base, NOW), base, NOW + 1000)
    expect(rows.length).toBe(1)
    expect(rows[0]!.state).toBe('new')
  })
  test('dismissed rows stay quiet 30 days and come back only with fresh evidence', () => {
    const d = actOn(mergeSuggestions([], base, NOW), 'dismiss', '1', NOW).rows
    expect(d[0]!.state).toBe('dismissed')
    expect(mergeSuggestions(d, base, NOW + 29 * DAY)[0]!.state).toBe('dismissed')
    expect(mergeSuggestions(d, base, NOW + 31 * DAY)[0]!.state).toBe('new')
    expect(mergeSuggestions(d, [], NOW + 31 * DAY)[0]!.state).toBe('dismissed')
  })
  test('a snooze lasts 7 days, by number or by id', () => {
    const rows = mergeSuggestions([], base, NOW)
    const z = actOn(rows, 'snooze', rows[0]!.id, NOW).rows
    expect(z[0]!.state).toBe('snoozed')
    expect(mergeSuggestions(z, base, NOW + 6 * DAY)[0]!.state).toBe('snoozed')
    expect(mergeSuggestions(z, base, NOW + 7 * DAY)[0]!.state).toBe('new')
  })
  test('an accepted row never comes back; a bad reference says so', () => {
    const rows = mergeSuggestions([], base, NOW)
    const a = actOn(rows, 'accept', '1', NOW)
    expect(mergeSuggestions(a.rows, base, NOW + 90 * DAY)[0]!.state).toBe('accepted')
    expect(actOn(rows, 'accept', '9', NOW).text).toMatch(/No suggestion/)
  })
  test('at most one note a session, the strongest, and never the same one twice', () => {
    const two = mergeSuggestions([], cands([...perm('bash a', 3), ...perm('bash b', 9)]), NOW)
    const p = pickNote(two, false, NOW)
    expect(p.note?.key).toBe('prompt:bash b')
    expect(pickNote(p.rows, true, NOW).note).toBe(null)
    expect(pickNote(p.rows, false, NOW).note?.key).toBe('prompt:bash a')
  })
  test('the file round-trips; junk rows are dropped', () => {
    const rows = mergeSuggestions([], base, NOW)
    expect(parseSuggestions(serializeSuggestions(rows, NOW))).toEqual(rows)
    expect(parseSuggestions('{"rows":[{"key":"x"}]}')).toEqual([] as Suggestion[])
    expect(parseSuggestions('nope')).toEqual([])
  })
})
