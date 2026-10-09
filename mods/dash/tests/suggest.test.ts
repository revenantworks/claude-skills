import { describe, expect, test } from 'claude-code/testing'

import { DAY, rollup, sessionKey, type DashEvent } from '../hooks/collector-logic'
import { T, actOn, candidates, listed, mergeSuggestions, nextMdLine, parseSuggestions, pickNote, serializeSuggestions, type Suggestion } from '../hooks/suggest-logic'

const NOW = Date.UTC(2026, 9, 8, 12)
const s = (n: number) => sessionKey(`session-${n}`)
const cmd = (shape: string, n: number, sessions: number, ago = DAY): DashEvent[] =>
  Array.from({ length: n }, (_, i) => ({ t: NOW - ago - i * 1000, s: s(i % sessions), k: 'cmd', shape }) as DashEvent)
const cands = (events: DashEvent[]) => candidates(events, rollup(events, { now: NOW, recording: true }), NOW)
const keys = (events: DashEvent[]) => cands(events).map(c => c.key)

describe('thresholds', () => {
  test('the same command 5 times in 3 sessions in 7 days, and not one short of any of them', () => {
    expect(keys(cmd('npm run build', 5, 3))).toEqual(['command:npm run build'])
    expect(keys(cmd('npm run build', 4, 3))).toEqual([])
    expect(keys(cmd('npm run build', 5, 2))).toEqual([])
    expect(keys(cmd('npm run build', 5, 3, (T.cmdDays + 1) * DAY))).toEqual([])
    expect(keys(cmd('git status', 9, 4))).toEqual([])
  })
  test('the same permission prompt 3 times in 7 days suggests a gatewarden review, never an allow', () => {
    const perm = (n: number, ago = DAY) => Array.from({ length: n }, (_, i) => ({ t: NOW - ago - i, s: s(0), k: 'perm', shape: 'bash docker compose' }) as DashEvent)
    expect(keys(perm(3))).toEqual(['allow:bash docker compose'])
    expect(keys(perm(2))).toEqual([])
    expect(keys(perm(3, 8 * DAY))).toEqual([])
    expect(cands(perm(3))[0]!.action).toMatch(/gatewarden.*writes and allows nothing/)
  })
  test('a skill listed 30 days with no fire: probe or retire', () => {
    const listedLong: DashEvent[] = [{ t: NOW - 31 * DAY, s: s(0), k: 'listed', skills: ['quiet'] }, { t: NOW - DAY, s: s(0), k: 'listed', skills: ['quiet'] }]
    expect(keys(listedLong)).toEqual(['unused:quiet'])
    expect(keys([{ t: NOW - 29 * DAY, s: s(0), k: 'listed', skills: ['quiet'] }])).toEqual([])
    expect(keys([...listedLong, { t: NOW - 2 * DAY, s: s(0), k: 'skill', skill: 'quiet', via: 'auto' }])).toEqual([])
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
  test('context past 80% twice in a day, or one skill over a quarter of the week: suggest a slim', () => {
    expect(keys([{ t: NOW - 1000, s: s(0), k: 'ctx80' }, { t: NOW - 2000, s: s(1), k: 'ctx80' }])).toEqual(['slim:context'])
    expect(keys([{ t: NOW - 1000, s: s(0), k: 'ctx80' }])).toEqual([])
    const turn = (skill: string | null, tokens: number): DashEvent => ({ t: NOW - 1000, s: s(0), k: 'turn', skill, input: tokens, output: 0, cacheRead: 0, cacheWrite: 0, cost: null })
    expect(keys([turn('heavy', 60_000), turn(null, 140_000)])).toEqual(['slim:heavy'])
    expect(keys([turn('heavy', 40_000), turn(null, 160_000)])).toEqual([])
    expect(keys([turn('heavy', 60_000), turn(null, 100_000)])).toEqual([])
  })
})

describe('the queue: dedupe, dismiss, snooze, accept, one note a session', () => {
  const base = cands(cmd('npm run build', 5, 3))
  test('a candidate seen again updates its row; it never doubles', () => {
    let rows = mergeSuggestions([], base, NOW)
    rows = mergeSuggestions(rows, base, NOW + 1000)
    expect(rows.length).toBe(1)
    expect(rows[0]!.state).toBe('new')
  })
  test('dismissed rows stay quiet 30 days and come back only with fresh evidence', () => {
    const rows = mergeSuggestions([], base, NOW)
    const d = actOn(rows, 'dismiss', '1', NOW).rows
    expect(d[0]!.state).toBe('dismissed')
    expect(mergeSuggestions(d, base, NOW + 29 * DAY)[0]!.state).toBe('dismissed')
    expect(mergeSuggestions(d, base, NOW + 31 * DAY)[0]!.state).toBe('new')
    expect(mergeSuggestions(d, [], NOW + 31 * DAY)[0]!.state).toBe('dismissed')
  })
  test('a snooze lasts 7 days', () => {
    const rows = mergeSuggestions([], base, NOW)
    const z = actOn(rows, 'snooze', rows[0]!.id, NOW).rows
    expect(z[0]!.state).toBe('snoozed')
    expect(mergeSuggestions(z, base, NOW + 6 * DAY)[0]!.state).toBe('snoozed')
    expect(mergeSuggestions(z, base, NOW + 7 * DAY)[0]!.state).toBe('new')
  })
  test('accepting gives a NEXT.md line to copy and never comes back', () => {
    const rows = mergeSuggestions([], base, NOW)
    const a = actOn(rows, 'accept', '1', NOW)
    expect(a.text).toMatch(/Copy this line to NEXT\.md yourself; dash writes nothing there/)
    expect(a.text).toContain(nextMdLine(a.rows[0]!, NOW))
    expect(mergeSuggestions(a.rows, base, NOW + 90 * DAY)[0]!.state).toBe('accepted')
    expect(actOn(rows, 'accept', '9', NOW).text).toMatch(/No suggestion/)
  })
  test('at most one note a session, oldest first', () => {
    const two = mergeSuggestions([], [...base, ...cands(cmd('make test', 5, 3))], NOW)
    const p = pickNote(two, false, NOW)
    expect(p.note?.key).toBe(two[0]!.key)
    expect(p.rows.filter(r => r.state === 'shown').length).toBe(1)
    expect(pickNote(p.rows, true, NOW).note).toBe(null)
    expect(listed(p.rows)[0]!.state).toBe('new')
  })
  test('the file round-trips; junk rows are dropped', () => {
    const rows = mergeSuggestions([], base, NOW)
    expect(parseSuggestions(serializeSuggestions(rows, NOW))).toEqual(rows)
    expect(parseSuggestions('{"rows":[{"key":"x"}]}')).toEqual([] as Suggestion[])
    expect(parseSuggestions('nope')).toEqual([])
  })
})
