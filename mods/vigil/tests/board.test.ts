import { describe, expect, test } from 'claude-code/testing'

import {
  CARDS_MAX, arranged, cardsOf, crossed, dailyTokens, doItOf, forecast, glanceOf, glanceText, moveTile, notNow, parseAutoModes,
  parseBudget, parseLayout, pictureSvg, serializeAutoModes, togglePinned, undoRow, type Layout,
} from '../hooks/board-logic'
import { DAY, emptyHealth, type Feed } from '../hooks/collector-logic'
import { BLOCKS, NEUTRAL_HEX, glyphMeter, glyphSpark, inkOf, meterRole, ringSvg } from '../hooks/draw-logic'
import type { Live } from '../hooks/meters-logic'
import type { Suggestion } from '../hooks/suggest-logic'
import { NEUTRAL, REVENANTWORKS } from '../hooks/theme-logic'

const NOW = Date.UTC(2026, 9, 23, 12)
const feed = (over: Partial<Feed> = {}): Feed => ({ version: 1, generatedAt: NOW, recording: false, sessions7: 0, tokens7: 0, turns7: 0, cost7: null, ctx80Days7: 0, skills: [], meters: null, health: emptyHealth(), suggestionsNew: 0, ...over })
const live = (over: Partial<Live> = {}): Live => ({ at: NOW, five: 20, week: 40, weekResetMs: NOW + 3.5 * DAY, ctx: 30, cacheHit: null, costUsd: null, fromFile: false, ...over })
const row = (id: string, count: number, over: Partial<Suggestion> = {}): Suggestion => ({ key: `k-${id}`, kind: 'command', title: `t ${id}`, evidence: `${count} runs`, action: 'Make a command.', count, id, state: 'new', createdAt: NOW - DAY, stateAt: NOW - DAY, ...over })

describe('layout', () => {
  test('a stored layout is repaired: unknown ids drop, missing tiles join in shipped order', () => {
    const l = parseLayout({ order: ['health', 'ghost', 'usage'], pinned: ['ghost', 'inbox'], collapsed: 'no' })
    expect(l.order.slice(0, 2)).toEqual(['health', 'usage'])
    expect(l.order).toHaveLength(7)
    expect(l.pinned).toEqual(['inbox'])
    expect(l.collapsed).toEqual([])
    expect(parseLayout(null).order[0]).toBe('usage')
  })
  test('pinned tiles draw first; a move stays inside its group and the ends stay put', () => {
    let l: Layout = togglePinned(parseLayout(null), 'health')
    expect(arranged(l)[0]).toBe('health')
    expect(moveTile(l, 'health', -1)).toBe(l)
    expect(moveTile(l, 'usage', -1)).toBe(l)
    l = moveTile(l, 'usage', 1)
    expect(arranged(l).slice(0, 3)).toEqual(['health', 'context', 'usage'])
  })
})

describe('meters', () => {
  test('the forecast carries the burn so far forward; it lasts when the burn is slow', () => {
    // Half the week gone, 75% used: runs out before the reset.
    const f = forecast(live({ week: 75, weekResetMs: NOW + 3.5 * DAY }), NOW)
    expect(f?.lasts).toBe(false)
    expect(f!.runsOutAt!).toBeLessThan(NOW + 3.5 * DAY)
    expect(forecast(live({ week: 30 }), NOW)?.lasts).toBe(true)
    expect(forecast(live({ weekResetMs: null }), NOW)).toBeNull()
  })
  test('a crossing alerts once per level, upward only', () => {
    expect(crossed(70, 85)).toEqual([80])
    expect(crossed(79, 95)).toEqual([80, 90])
    expect(crossed(85, 88)).toEqual([])
    expect(crossed(95, 70)).toEqual([])
    expect(crossed(null, 95)).toEqual([])
  })
  test('the glance strip: three rings, and a mark only when something needs you', () => {
    const g = glanceOf({ live: live(), now: NOW, feed: feed(), inbox: 0 })
    expect(g.rings.map(r => r.label)).toEqual(['5h', 'wk', 'ctx'])
    expect(g.needsYou).toBeNull()
    expect(glanceOf({ live: live(), now: NOW, feed: feed(), inbox: 2 }).needsYou).toMatch(/2 suggestion/)
    expect(glanceText(g, BLOCKS)).toBe('5h ▰▱▱▱  wk ▰▰▱▱  ctx ▰▱▱▱')
  })
  test('tokens by day, today last', () => {
    const turn = (t: number, n: number) => ({ t, s: 'x', k: 'turn' as const, skill: null, input: n, output: 0, cacheRead: 0, cacheWrite: 0, cost: null })
    expect(dailyTokens([turn(NOW, 5), turn(NOW - DAY, 3), turn(NOW - 9 * DAY, 100)], NOW)).toEqual([0, 0, 0, 0, 0, 3, 5])
  })
})

describe('drawings', () => {
  test('a ring carries a title for readers who cannot see it, and the meter colour by level', () => {
    const svg = ringSvg({ pct: 85, tick: 50, label: 'week', ink: inkOf(NEUTRAL, 'dark') })
    expect(svg).toMatch(/^<svg /)
    expect(svg).toContain('<title>week 85%, pace 50%</title>')
    expect(svg).toContain(NEUTRAL_HEX.dark.warn)
    expect(meterRole(96)).toBe('bad')
    expect(meterRole(10)).toBe('ok')
  })
  test('neutral draws in the house Neutral hex; a brand theme in its own', () => {
    expect(inkOf(NEUTRAL, 'light').accent).toBe(NEUTRAL_HEX.light.accent)
    expect(inkOf(REVENANTWORKS, 'dark').accent).toBe('#00E5FF')
  })
  test('glyphs for the terminal', () => {
    expect(glyphMeter(50)).toBe('▰▰▱▱')
    expect(glyphMeter(null)).toBe('▱▱▱▱?')
    expect(glyphSpark([0, 4, 8])).toBe('▁▅█')
    expect(pictureSvg({ kind: 'badge', n: 3 }, inkOf(NEUTRAL, 'dark'))).toContain('>3<')
  })
})

describe('suggestion cards', () => {
  test('at most three cards, strongest first; the rest are counted', () => {
    const rows = [row('a', 5), row('b', 9), row('c', 7), row('d', 6), row('e', 1, { kind: 'allow' })]
    const { cards, waiting } = cardsOf(rows, NOW)
    expect(cards.map(c => c.id)).toEqual(['b', 'c', 'd'])
    expect(cards).toHaveLength(CARDS_MAX)
    expect(waiting).toBe(1)
  })
  test('Not now hides a card 7 days, then 30; Undo puts it back as it was', () => {
    const rows = [row('a', 5)]
    const one = notNow(rows, 'a', NOW)
    expect(one.days).toBe(7)
    expect(cardsOf(one.rows, NOW).cards).toHaveLength(0)
    expect(cardsOf(one.rows, NOW + 8 * DAY).cards).toHaveLength(1)
    const two = notNow(one.rows, 'a', NOW + 8 * DAY)
    expect(two.days).toBe(30)
    expect(undoRow(two.rows, two.before!)).toEqual(one.rows)
  })
  test('Do it: a repeated prompt goes to the built-in; the rest is a draft in chat that writes nothing', () => {
    expect(doItOf(row('a', 5, { kind: 'prompt' }))).toEqual({ kind: 'command', command: 'fewer-permission-prompts' })
    const d = doItOf(row('b', 5))
    expect(d.kind).toBe('prompt')
    expect(d.kind === 'prompt' && d.text).toMatch(/Write nothing until I say yes\.$/)
  })
})

describe('spend modes', () => {
  test('every auto mode is on until the file says otherwise', () => {
    expect(parseAutoModes(null)).toEqual({ pace: true, overnight: true, 'reset-eve': true })
    const text = serializeAutoModes({ pace: true, overnight: false, 'reset-eve': true }, NOW)
    expect(parseAutoModes(text).overnight).toBe(false)
    expect(JSON.parse(text).schema).toBe(1)
  })
  test('a budget decision past its expiry is no decision', () => {
    const b = JSON.stringify({ mode: 'pace', parallel_ceiling: 1, expires_at: new Date(NOW + 3600_000).toISOString(), basis: 'weekly 61%' })
    expect(parseBudget(b, NOW)).toMatchObject({ mode: 'pace', parallelCeiling: 1 })
    expect(parseBudget(b, NOW + 2 * 3600_000)).toBeNull()
    expect(parseBudget('nope', NOW)).toBeNull()
  })
})
