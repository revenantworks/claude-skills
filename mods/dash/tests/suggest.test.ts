import { describe, expect, test } from 'claude-code/testing'

import { DAY, rollup, sessionKey, type DashEvent } from '../hooks/collector-logic'
import { READ_ONLY_GROUP, T, TOOLS_GROUP, actOn, candidates, groupOf, grouped, listed, mergeSuggestions, nextMdLine, parseSuggestions, pickNote, serializeSuggestions, subLabel, type Suggestion } from '../hooks/suggest-logic'
import { linesText, suggestLines } from '../hooks/view-logic'

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
  test('the same permission dialog shown to you 3 times in 7 days suggests a decision, never an allow', () => {
    const shown = (n: number, ago = DAY, k: 'prompt' | 'perm' = 'prompt') => Array.from({ length: n }, (_, i) => ({ t: NOW - ago - i, s: s(0), k, shape: 'bash docker compose' }) as DashEvent)
    expect(keys(shown(3))).toEqual(['prompt:bash docker compose'])
    expect(keys(shown(2))).toEqual([])
    expect(keys(shown(3, 8 * DAY))).toEqual([])
    expect(cands(shown(3))[0]!.action).toMatch(/gatewarden.*writes and allows nothing/)
    // The retired count (classifier reviews included) never makes a row.
    expect(keys(shown(9, DAY, 'perm'))).toEqual([])
  })
  test('rows from the retired count leave the open queue; settled ones stay as the record', () => {
    const row = (state: Suggestion['state']): Suggestion => ({ key: 'allow:bash cd ; sed -n', kind: 'allow', title: 't', evidence: 'asked 78 times in 7 days', action: 'a', id: `id-${state}`, state, createdAt: NOW, stateAt: NOW })
    expect(mergeSuggestions([row('new'), row('shown'), row('dismissed')], [], NOW + 1000).map(r => r.state)).toEqual(['dismissed'])
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
  test('context past 80% twice in a day: suggest a slim', () => {
    expect(keys([{ t: NOW - 1000, s: s(0), k: 'ctx80' }, { t: NOW - 2000, s: s(1), k: 'ctx80' }])).toEqual(['slim:context'])
    expect(keys([{ t: NOW - 1000, s: s(0), k: 'ctx80' }])).toEqual([])
  })
  test('a skill whose turns cost 1.5x the turns without it: slim it; one merely loaded every turn: nothing', () => {
    const turns = (skill: string | null, n: number, each: number): DashEvent[] =>
      Array.from({ length: n }, (_, i) => ({ t: NOW - 1000 - i, s: s(0), k: 'turn', skill, input: each, output: 0, cacheRead: 0, cacheWrite: 0, cost: null }) as DashEvent)
    // Heavy: 10 turns at 20k beside 20 at 10k is a 2x lift on a 50% share.
    const heavy = cands([...turns('heavy', 10, 20_000), ...turns(null, 20, 10_000)])
    expect(heavy.map(c => c.key)).toEqual(['heavy:heavy'])
    expect(heavy[0]!.evidence).toBe('its turns average 2.0x the tokens of turns without it (10 turns this week)')
    // The task-observer case: loaded in 90% of turns, each the same size as the rest. 90% share, no lift.
    expect(keys([...turns('everywhere', 27, 10_000), ...turns(null, 3, 10_000)])).toEqual([])
    expect(keys([...turns('everywhere', 25, 10_000), ...turns(null, 5, 10_000)])).toEqual([])
    // Too few turns on either side to compare, or a small week: nothing.
    expect(keys([...turns('heavy', 4, 50_000), ...turns(null, 20, 10_000)])).toEqual([])
    expect(keys([...turns('heavy', 10, 2_000), ...turns(null, 20, 1_000)])).toEqual([])
  })
  test('rows from the retired token share leave the open queue; the context slim stays', () => {
    const row = (key: string): Suggestion => ({ key, kind: 'slim-skill', title: 't', evidence: "44% of the week's tokens", action: 'a', id: key, state: 'shown', createdAt: NOW, stateAt: NOW, lastSeen: NOW })
    expect(mergeSuggestions([row('slim:task-observer'), row('slim:context')], [], NOW + 1000).map(r => r.key)).toEqual(['slim:context'])
  })
  test('a loop closer is no command: stored shapes drop it, old rows leave', () => {
    expect(keys(cmd('npm test ; sleep ; done', 5, 3))).toEqual(['command:npm test ; sleep'])
    expect(keys(cmd('grep -q ; sleep ; done', 33, 3))).toEqual([])
    expect(groupOf('command:grep -q ; sleep ; done')).toBe('shell: done')
    const old: Suggestion = { key: 'command:grep -q ; sleep ; done', kind: 'command', title: 't', evidence: '33 runs', action: 'a', id: 'old', state: 'new', createdAt: NOW, stateAt: NOW, lastSeen: NOW }
    expect(mergeSuggestions([old], [], NOW + 1000)).toEqual([])
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
  test('at most one note a session, most evidence first, oldest on a tie', () => {
    const two = mergeSuggestions([], [...base, ...cands(cmd('make test', 5, 3))], NOW)
    const p = pickNote(two, false, NOW)
    expect(p.note?.key).toBe(two[0]!.key)
    expect(p.rows.filter(r => r.state === 'shown').length).toBe(1)
    expect(pickNote(p.rows, true, NOW).note).toBe(null)
    expect(listed(p.rows)[0]!.state).toBe('new')
  })
  test('the note picks the row with the most evidence', () => {
    const rows = mergeSuggestions([], [...cands(cmd('make test', 5, 3)), ...cands(cmd('npm run build', 9, 3))], NOW)
    expect(pickNote(rows, false, NOW).note?.key).toBe('command:npm run build')
  })
  test('the file round-trips; junk rows are dropped', () => {
    const rows = mergeSuggestions([], base, NOW)
    expect(parseSuggestions(serializeSuggestions(rows, NOW))).toEqual(rows)
    expect(parseSuggestions('{"rows":[{"key":"x"}]}')).toEqual([] as Suggestion[])
    expect(parseSuggestions('nope')).toEqual([])
  })
  test('a row stored before counts existed takes its count from its evidence', () => {
    const old = (evidence: string) => ({ key: 'allow:agent', kind: 'allow', title: 't', evidence, action: 'a', id: 'abc123', state: 'new', createdAt: NOW, stateAt: NOW })
    expect(parseSuggestions(JSON.stringify({ rows: [old('asked 91 times in 7 days')] }))[0]!.count).toBe(91)
    expect(parseSuggestions(JSON.stringify({ rows: [old('247 runs in 12 sessions in 7 days')] }))[0]!.count).toBe(247)
    expect(parseSuggestions(JSON.stringify({ rows: [old('44% of the week')] }))[0]!.count).toBeUndefined()
  })
})

const perm = (shape: string, n: number): DashEvent[] =>
  Array.from({ length: n }, (_, i) => ({ t: NOW - DAY - i, s: s(i % 3), k: 'prompt', shape }) as DashEvent)

describe('grouping by command type', () => {
  test('a shell row groups under its lead program; cd and read-only steps do not lead', () => {
    expect(groupOf('prompt:bash cd ; git add ; git commit -m -q')).toBe('shell: git')
    expect(groupOf('command:cd ; git add ; git commit -m -q')).toBe('shell: git')
    expect(groupOf('prompt:bash cd ; python -m unittest ; tail')).toBe('shell: python')
    expect(groupOf('prompt:bash cd ; sed -n ; grep -n')).toBe(READ_ONLY_GROUP)
    expect(groupOf('prompt:mcp__claude-in-chrome__computer')).toBe('mcp: claude-in-chrome')
    expect(groupOf('prompt:agent')).toBe(TOOLS_GROUP)
    expect(groupOf('unused:quiet')).toBe('skills')
    expect(groupOf('slim:context')).toBe('context')
    expect(subLabel('prompt:bash cd ; git add')).toBe('cd ; git add')
    expect(groupOf('allow:bash cd ; git add')).toBe('shell: git')   // a stored row from the retired count still groups
  })
  test('read-only chains never become command rows, and a by-design question never an allow row', () => {
    expect(keys(cmd('cd ; sed -n ; grep -n', 9, 3))).toEqual([])
    expect(keys(perm('askuserquestion', 9))).toEqual([])
    expect(keys(perm('bash cd ; sed -n', 9))).toEqual(['prompt:bash cd ; sed -n'])
  })
  test('groups and their shapes sort by times asked, most first; a run and a prompt of one shape share a row', () => {
    const rows = mergeSuggestions([], cands([
      ...perm('bash cd ; git add ; git commit -m -q', 4), ...cmd('cd ; git add ; git commit -m -q', 6, 3),
      ...perm('bash cd ; git push', 9), ...perm('mcp__srv__read', 30), ...perm('bash cd ; sed -n', 12),
    ]), NOW)
    const gs = grouped(rows)
    expect(gs.map(g => g.name)).toEqual(['mcp: srv', 'shell: git', READ_ONLY_GROUP])
    expect(gs[1]!).toMatchObject({ asked: 13, ran: 6 })
    expect(gs[1]!.subs.map(x => [x.label, x.asked, x.ran])).toEqual([['cd ; git push', 9, 0], ['cd ; git add ; git commit -m -q', 4, 6]])
  })
  test('a whole group, one shape or one id can be acted on; settled groups sink', () => {
    const rows = mergeSuggestions([], cands([...perm('bash cd ; git push', 9), ...perm('bash cd ; git add', 5), ...perm('mcp__srv__read', 3)]), NOW)
    const g = actOn(rows, 'dismiss', '1', NOW)
    expect(g.text).toMatch(/Dismissed: shell: git \(2 rows\)/)
    expect(grouped(g.rows).map(x => x.name)).toEqual(['mcp: srv', 'shell: git'])
    const one = actOn(rows, 'snooze', '1.2', NOW)
    expect(one.rows.filter(r => r.state === 'snoozed').map(r => r.key)).toEqual(['prompt:bash cd ; git add'])
    expect(actOn(rows, 'accept', 'git', NOW).text).toMatch(/these lines to NEXT\.md/)
    expect(actOn(g.rows, 'dismiss', '2', NOW).text).toMatch(/Nothing open/)
  })
  test('open rows without fresh evidence leave after the stale window; settled rows stay', () => {
    const rows = mergeSuggestions([], cands(perm('bash cd ; git push', 9)), NOW)
    expect(mergeSuggestions(rows, [], NOW + T.staleDays * DAY).length).toBe(1)
    expect(mergeSuggestions(rows, [], NOW + (T.staleDays + 1) * DAY).length).toBe(0)
    const kept = actOn(rows, 'dismiss', '1', NOW).rows
    expect(mergeSuggestions(kept, [], NOW + 60 * DAY).length).toBe(1)
  })
  test('stored rows that are now suppressed drop out of the open queue', () => {
    const old: Suggestion = { key: 'prompt:askuserquestion', kind: 'prompt', title: 't', evidence: 'e', action: 'a', id: 'abc123', state: 'new', createdAt: NOW, stateAt: NOW }
    expect(mergeSuggestions([old], [], NOW + 1000)).toEqual([])
  })
  test('the view lists groups, then drills into one with its shapes numbered n.m', () => {
    const rows = mergeSuggestions([], cands([...perm('bash cd ; git push', 9), ...perm('mcp__srv__read', 30)]), NOW)
    const top = linesText(suggestLines(rows))
    expect(top).toMatch(/1\. mcp: srv\s+asked 30/)
    expect(top).toMatch(/2\. shell: git\s+asked 9/)
    const drill = linesText(suggestLines(rows, undefined, '2'))
    expect(drill).toMatch(/2\.1 \[new\] cd ; git push/)
    expect(linesText(suggestLines(rows, undefined, 'git'))).toMatch(/2\.1 \[new\] cd ; git push/)
    expect(linesText(suggestLines(rows, undefined, '9'))).toMatch(/No group "9"/)
  })
})
