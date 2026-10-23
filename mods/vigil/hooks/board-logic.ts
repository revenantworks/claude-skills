// vigil board: pure logic (no $). The three layers of the redesign: the glance strip above the
// prompt, the board of tiles, and one tile's detail. Also the suggestion cards (Do it, Not now),
// the three switches that stand for the feature ids, and the spend-mode toggles pacewright reads.
// Every picture is a spec here; draw-logic.ts turns a spec into SVG or glyphs.
import { DAY, paceOf, type DashEvent, type Feed } from './collector-logic'
import type { Live } from './meters-logic'
import { listed, type Suggestion } from './suggest-logic'
import { badgeSvg, barSvg, dotsSvg, glyphDots, glyphMeter, glyphSpark, ringSvg, sparkSvg, type Dot, type Glyph, type Ink, type Segment } from './draw-logic'

// ---------- tiles and their layout ----------

export const TILES = ['usage', 'context', 'inbox', 'mode', 'spend', 'skills', 'health'] as const
export type TileId = (typeof TILES)[number]
export const isTile = (v: unknown): v is TileId => typeof v === 'string' && (TILES as readonly string[]).includes(v)

/** The board's layout: the tiles in order, which are collapsed, which are pinned to the top. */
export type Layout = { order: TileId[]; collapsed: TileId[]; pinned: TileId[] }

export const defaultLayout = (): Layout => ({ order: [...TILES], collapsed: [], pinned: [] })

/** A stored layout, repaired: unknown ids drop, missing tiles join at the end in shipped order. */
export const parseLayout = (v: unknown): Layout => {
  const o = v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
  const ids = (x: unknown): TileId[] => (Array.isArray(x) ? [...new Set(x.filter(isTile))] : [])
  const order = ids(o.order)
  for (const t of TILES) if (!order.includes(t)) order.push(t)
  return { order, collapsed: ids(o.collapsed), pinned: ids(o.pinned) }
}

/** The order the board draws: pinned tiles first, each group in the layout's order. */
export const arranged = (l: Layout): TileId[] => [...l.order.filter(t => l.pinned.includes(t)), ...l.order.filter(t => !l.pinned.includes(t))]

/** Moves a tile one place up (-1) or down (+1) within its group (pinned or not); the ends stay put. */
export const moveTile = (l: Layout, id: TileId, dir: -1 | 1): Layout => {
  const shown = arranged(l)
  const i = shown.indexOf(id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= shown.length) return l
  const other = shown[j]!
  if (l.pinned.includes(id) !== l.pinned.includes(other)) return l
  const order = [...l.order]
  const a = order.indexOf(id)
  const b = order.indexOf(other)
  order[a] = other
  order[b] = id
  return { ...l, order }
}

const flip = (xs: readonly TileId[], id: TileId): TileId[] => (xs.includes(id) ? xs.filter(x => x !== id) : [...xs, id])
export const toggleCollapsed = (l: Layout, id: TileId): Layout => ({ ...l, collapsed: flip(l.collapsed, id) })
export const togglePinned = (l: Layout, id: TileId): Layout => ({ ...l, pinned: flip(l.pinned, id) })

// ---------- what the board reads ----------

/** pacewright's budget decision (~/.dispatch/budget-decision.json), only the fields the board shows. */
export type Budget = { mode: string; parallelCeiling: number | null; basis: string | null; expiresAt: number }

export const parseBudget = (text: string | null, now: number): Budget | null => {
  let o: Record<string, unknown>
  try {
    const raw = JSON.parse(text ?? '') as unknown
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
    o = raw as Record<string, unknown>
  } catch {
    return null
  }
  const expiresAt = typeof o.expires_at === 'string' ? Date.parse(o.expires_at) : NaN
  if (!Number.isFinite(expiresAt) || expiresAt <= now) return null
  if (typeof o.mode !== 'string' || o.mode === '') return null
  const ceiling = typeof o.parallel_ceiling === 'number' && Number.isFinite(o.parallel_ceiling) ? o.parallel_ceiling : null
  return { mode: o.mode.slice(0, 40), parallelCeiling: ceiling, basis: typeof o.basis === 'string' ? o.basis.slice(0, 160) : null, expiresAt }
}

/**
 * The modes pacewright may enter by itself (by the gap, by the clock, by the projected close). Each
 * can be switched off: an auto mode switched off is entered only on the person's word (owner,
 * 2026-10-23). Turbo, work day and owner-away are never automatic, so they have no switch.
 */
export const AUTO_MODES = ['pace', 'overnight', 'reset-eve'] as const
export type AutoMode = (typeof AUTO_MODES)[number]
export type AutoModes = Record<AutoMode, boolean>
export const isAutoMode = (v: unknown): v is AutoMode => typeof v === 'string' && (AUTO_MODES as readonly string[]).includes(v)

/** ~/.dispatch/spend-modes.json; every mode on when the file is missing, unreadable or silent on it. */
export const parseAutoModes = (text: string | null): AutoModes => {
  const out: AutoModes = { pace: true, overnight: true, 'reset-eve': true }
  try {
    const o = JSON.parse(text ?? '') as { auto?: Record<string, unknown> }
    for (const m of AUTO_MODES) if (typeof o?.auto?.[m] === 'boolean') out[m] = o.auto[m] as boolean
  } catch {
    // No file: pacewright's shipped behaviour, every auto mode on.
  }
  return out
}

export const serializeAutoModes = (a: AutoModes, now: number): string =>
  `${JSON.stringify({ schema: 1, written_at: new Date(now).toISOString(), writer: 'vigil, on the person\'s press', auto: a }, null, 2)}\n`

/** Main-loop tokens per day, oldest first, the last entry today. */
export const dailyTokens = (events: readonly DashEvent[], now: number, days = 7): number[] => {
  const out = new Array<number>(days).fill(0)
  const today = Math.floor(now / DAY)
  for (const e of events) {
    if (e.k !== 'turn') continue
    const i = days - 1 - (today - Math.floor(e.t / DAY))
    if (i >= 0 && i < days) out[i] += e.input + e.output + e.cacheRead + e.cacheWrite
  }
  return out
}

export type BoardData = { live: Live | null; now: number; feed: Feed; daily: readonly number[]; inbox: number; budget: Budget | null; auto: AutoModes }

// ---------- pictures ----------

export type Picture =
  | { kind: 'rings'; rings: ReadonlyArray<{ label: string; pct: number | null; tick: number | null; warnAt?: number }> }
  | { kind: 'spark'; values: readonly number[] }
  | { kind: 'bar'; segs: readonly Segment[] }
  | { kind: 'dots'; dots: readonly Dot[] }
  | { kind: 'badge'; n: number }
  | { kind: 'word'; text: string }

export type Tile = { id: TileId; title: string; picture: Picture; big: string; sub: string }
export type Detail = { id: TileId; title: string; picture: Picture; lines: string[] }

const k = (n: number): string => (n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 10_000 ? `${Math.round(n / 1000)}k` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(Math.round(n)))
const pct = (n: number | null) => (n === null ? '–' : `${Math.round(n)}%`)
const WEEK = 7 * DAY

/** The weekly window's pace tick: the share of the week gone, which is where an even burn sits. */
export const weekTick = (live: Live | null, now: number): number | null =>
  live?.week !== null && live?.week !== undefined && live.weekResetMs !== null ? paceOf(live.week, live.weekResetMs, now).pace : null

/**
 * When the week runs out at this pace: the burn so far (used ÷ time gone), carried forward. Null
 * when the reading or the reset is missing, or too early in the week to say (under an hour gone).
 */
export const forecast = (live: Live | null, now: number): { runsOutAt: number | null; lasts: boolean } | null => {
  if (!live || live.week === null || live.weekResetMs === null) return null
  const start = live.weekResetMs - WEEK
  const gone = now - start
  if (live.week <= 0) return { runsOutAt: null, lasts: true }
  if (gone < 3_600_000) return null
  const msTo100 = ((100 - live.week) / live.week) * gone
  const at = now + msTo100
  return at >= live.weekResetMs ? { runsOutAt: null, lasts: true } : { runsOutAt: at, lasts: false }
}

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
/** "Thu 15:00" in UTC; the surface's own clock is not readable here, so the time says UTC. */
export const whenText = (ms: number): string => {
  const d = new Date(ms)
  return `${DOW[d.getUTCDay()]} ${String(d.getUTCHours()).padStart(2, '0')}:00 UTC`
}

export const forecastText = (live: Live | null, now: number): string => {
  const f = forecast(live, now)
  if (!f) return 'No forecast yet: it needs a weekly reading and its reset.'
  return f.lasts ? 'At this pace the week lasts to its reset.' : `At this pace the week runs out ${whenText(f.runsOutAt!)}.`
}

const healthDots = (feed: Feed): Dot[] => {
  const h = feed.health
  const dots: Dot[] = Object.entries(h.plugins).map(([name, p]) => ({ ok: p.loaded && p.caught === 0, label: name }))
  for (const d of h.drift) dots.push({ ok: d.state === 'not installed' ? null : d.state === 'same', label: d.hook })
  dots.push({ ok: h.pinsChanged === 0, label: 'instruction pins' })
  return dots
}

/** The first failing check and its fix, in one line; null when every check passes. */
export const healthFault = (feed: Feed): string | null => {
  const h = feed.health
  for (const [name, p] of Object.entries(h.plugins)) {
    if (!p.loaded) return `${name} did not load. Fix: /rw-vigil doctor names why.`
    if (p.caught > 0) return `${name} caught ${p.caught} hook error(s). Fix: /rw-vigil doctor, then restart Claude Code.`
  }
  const d = h.drift.find(x => x.state === 'differs')
  if (d) return `Hook ${d.hook} differs from the shipped copy. Fix: reinstall the mod.`
  if (h.pinsChanged > 0) return `${h.pinsChanged} instruction file(s) changed since pinned. Fix: /rw-vigil health lists them.`
  return null
}

const skillSegs = (feed: Feed): Segment[] => {
  const sum = (f: (r: Feed['skills'][number]) => number) => feed.skills.reduce((a, r) => a + f(r), 0)
  const fails = sum(r => r.failures30)
  const mis = sum(r => r.misroutes30)
  return [
    { n: Math.max(0, sum(r => r.fires30) - fails - mis), role: 'ok', label: 'fires' },
    { n: fails, role: 'bad', label: 'failures' },
    { n: mis, role: 'warn', label: 'misroutes' },
  ]
}

const autoText = (a: AutoModes): string => AUTO_MODES.map(m => `${m} ${a[m] ? 'auto' : 'by word'}`).join(', ')

/** One tile's face: a picture, one big figure, one short line. */
export const tileOf = (id: TileId, d: BoardData): Tile => {
  const { live, now, feed } = d
  switch (id) {
    case 'usage': {
      const tick = weekTick(live, now)
      return { id, title: 'Usage', picture: { kind: 'rings', rings: [{ label: '5h', pct: live?.five ?? null, tick: null }, { label: 'week', pct: live?.week ?? null, tick }] }, big: pct(live?.week ?? null), sub: forecast(live, now)?.lasts === false ? `runs out ${whenText(forecast(live, now)!.runsOutAt!)}` : 'week' }
    }
    case 'context':
      return { id, title: 'Context', picture: { kind: 'rings', rings: [{ label: 'ctx', pct: live?.ctx ?? null, tick: null, warnAt: 80 }] }, big: pct(live?.ctx ?? null), sub: feed.ctx80Days7 ? `past 80% on ${feed.ctx80Days7} day(s)` : 'of the window' }
    case 'spend':
      return { id, title: 'Spend', picture: { kind: 'spark', values: d.daily }, big: k(feed.tokens7), sub: 'tokens, 7 days' }
    case 'skills': {
      const segs = skillSegs(feed)
      return { id, title: 'Skills', picture: { kind: 'bar', segs }, big: String(feed.skills.reduce((a, r) => a + r.fires30, 0)), sub: `fires, 30 days${segs[1]!.n || segs[2]!.n ? `; ${segs[1]!.n} failed, ${segs[2]!.n} misrouted` : ''}` }
    }
    case 'health': {
      const dots = healthDots(feed)
      const bad = dots.filter(x => x.ok === false).length
      return { id, title: 'Health', picture: { kind: 'dots', dots }, big: bad ? `${bad} failing` : 'ok', sub: `${dots.length} checks` }
    }
    case 'inbox':
      return { id, title: 'Inbox', picture: { kind: 'badge', n: d.inbox }, big: String(d.inbox), sub: d.inbox === 1 ? 'suggestion' : 'suggestions' }
    case 'mode': {
      const b = d.budget
      return { id, title: 'Spend mode', picture: { kind: 'word', text: b ? b.mode : 'none' }, big: b ? b.mode : '–', sub: b ? `${b.parallelCeiling === null ? '' : `x${b.parallelCeiling}, `}${autoText(d.auto)}` : `no live decision; ${autoText(d.auto)}` }
    }
  }
}

/** One tile's detail: one picture and at most three lines. */
export const detailOf = (id: TileId, d: BoardData): Detail => {
  const t = tileOf(id, d)
  const { live, now, feed } = d
  const lines = ((): string[] => {
    switch (id) {
      case 'usage': {
        const tick = weekTick(live, now)
        const gap = live?.week !== null && live?.week !== undefined && tick !== null ? Math.round(live.week - tick) : null
        return [`5-hour ${pct(live?.five ?? null)}. Week ${pct(live?.week ?? null)}${tick === null ? '' : `, pace ${Math.round(tick)}% (${gap! >= 0 ? '+' : ''}${gap})`}.`, forecastText(live, now), live?.weekResetMs ? `The week resets ${whenText(live.weekResetMs)}.` : 'No reset time in the reading.']
      }
      case 'context':
        return [`${pct(live?.ctx ?? null)} of the context window is in use.`, `Past 80% on ${feed.ctx80Days7} day(s) this week.`, '/rw-vigil context lists what loads every turn.']
      case 'spend': {
        const top = [...feed.skills].sort((a, b) => b.tokens7 - a.tokens7)[0]
        return [`${k(feed.tokens7)} tokens over ${feed.turns7} turns this week${feed.cost7 === null ? '' : `, $${feed.cost7.toFixed(2)}`}.`, top && top.tokens7 > 0 ? `Most in turns with ${top.name}: ${k(top.tokens7)}.` : 'No skill turns counted yet.', '/rw-vigil skills shows each skill\'s share.']
      }
      case 'skills': {
        const segs = skillSegs(feed)
        const top = feed.skills[0]
        return [`${segs[0]!.n} clean fires, ${segs[1]!.n} failures, ${segs[2]!.n} misroutes in 30 days.`, top ? `Busiest: ${top.name}, ${top.fires30} fires.` : 'No skill has fired yet.', '/rw-vigil skills lists each skill\'s row.']
      }
      case 'health': {
        const f = healthFault(feed)
        return f ? [f, '/rw-vigil health shows every check.'] : ['Every check passes.', '/rw-vigil health shows every check.']
      }
      case 'inbox':
        return [d.inbox ? `${d.inbox} suggestion(s) wait. Do it drafts the change in chat; nothing is written until you say yes.` : 'Nothing waits.']
      case 'mode': {
        const b = d.budget
        return [b ? `pacewright set ${b.mode}${b.parallelCeiling === null ? '' : `, up to ${b.parallelCeiling} unit(s) at once`}.` : 'No live decision from pacewright. /rw-pacewright check writes one.', b?.basis ? `Basis: ${b.basis}` : 'Basis: none recorded.', `Auto modes: ${autoText(d.auto)}.`]
      }
    }
  })()
  return { id, title: t.title, picture: t.picture, lines: lines.slice(0, 3) }
}

// ---------- the glance strip ----------

export type Glance = { rings: ReadonlyArray<{ label: string; pct: number | null; tick: number | null; warnAt?: number }>; needsYou: string | null }

/** Three rings (5-hour, week, context) and a fourth mark only when something needs the person. */
export const glanceOf = (d: Pick<BoardData, 'live' | 'now' | 'feed' | 'inbox'>): Glance => ({
  rings: [
    { label: '5h', pct: d.live?.five ?? null, tick: null },
    { label: 'wk', pct: d.live?.week ?? null, tick: weekTick(d.live, d.now) },
    { label: 'ctx', pct: d.live?.ctx ?? null, tick: null, warnAt: 80 },
  ],
  needsYou: healthFault(d.feed) ? 'a health check fails' : d.inbox > 0 ? `${d.inbox} suggestion(s)` : null,
})

/** A meter crossing a level upward since the last reading: the levels crossed, highest last. */
export const crossed = (prev: number | null, cur: number | null, levels: readonly number[] = [80, 90]): number[] =>
  prev === null || cur === null ? [] : levels.filter(l => prev < l && cur >= l)

// ---------- suggestion cards ----------

export const CARDS_MAX = 3
/** Not now hides a card this long the first time, then this long each time after. */
export const NOT_NOW_DAYS = [7, 30] as const

const isOpen = (r: Suggestion, now: number) => r.kind !== 'allow' && (r.state === 'new' || r.state === 'shown' || (r.state === 'snoozed' && (r.snoozeUntil ?? 0) <= now))

/** At most three cards, the strongest evidence first; the rest wait and are counted. */
export const cardsOf = (rows: readonly Suggestion[], now: number): { cards: Suggestion[]; waiting: number } => {
  const open = listed(rows.filter(r => isOpen(r, now)).map(r => (r.state === 'snoozed' ? { ...r, state: 'shown' as const } : r)))
  return { cards: open.slice(0, CARDS_MAX), waiting: Math.max(0, open.length - CARDS_MAX) }
}

export const openCount = (rows: readonly Suggestion[], now: number): number => rows.filter(r => isOpen(r, now)).length

export type Snoozed = Suggestion & { notNow?: number }

/** Not now: hidden 7 days the first time, 30 after; the row as it was comes back for Undo. */
export const notNow = (rows: readonly Suggestion[], id: string, now: number): { rows: Suggestion[]; before: Suggestion | null; days: number } => {
  const before = rows.find(r => r.id === id) ?? null
  if (!before) return { rows: [...rows], before: null, days: 0 }
  const times = ((before as Snoozed).notNow ?? 0) + 1
  const days = NOT_NOW_DAYS[Math.min(times, NOT_NOW_DAYS.length) - 1]!
  const after: Snoozed = { ...before, state: 'snoozed', stateAt: now, snoozeUntil: now + days * DAY, notNow: times }
  return { rows: rows.map(r => (r.id === id ? after : r)), before, days }
}

/** Undo puts the row back exactly as it was before the press. */
export const undoRow = (rows: readonly Suggestion[], before: Suggestion): Suggestion[] => rows.map(r => (r.id === before.id ? before : r))

/**
 * What Do it hands Claude. A repeated permission prompt goes to the built-in
 * /fewer-permission-prompts, which already writes allow rules with the person's yes; every other
 * kind is a drafting ask in chat. Nothing is written until the person says yes there.
 */
export type DoIt = { kind: 'command'; command: string } | { kind: 'prompt'; text: string }

export const doItOf = (r: Suggestion): DoIt => {
  if (r.kind === 'prompt') return { kind: 'command', command: 'fewer-permission-prompts' }
  const what = r.kind === 'command' ? 'a command or skill for it' : r.kind === 'unused' ? 'whether to keep, retire or re-describe it' : r.kind === 'description' ? 'a description change' : 'a slim plan'
  return { kind: 'prompt', text: `vigil suggestion: ${r.title}. Evidence: ${r.evidence}. Suggested: ${r.action} Draft ${what} here in chat: what you would change and where. Write nothing until I say yes.` }
}

/** The card's evidence picture: one dot per time seen, up to twelve. */
export const evidenceDots = (r: Suggestion): Dot[] => Array.from({ length: Math.min(12, Math.max(1, r.count ?? 1)) }, (_, i) => ({ ok: true, label: `seen ${i + 1}` }))

// ---------- three switches ----------

/**
 * Three switches stand for the feature ids on the board (the ids stay for the terminal). Each is a
 * switch command the shared parser already knows, so the pane and a typed command change the same file.
 */
export const SWITCHES = [
  { name: 'Meters', on: 'on status-line', off: 'off status-line', id: 'D2' },
  { name: 'Suggestions', on: 'on suggestions', off: 'off suggestions', id: 'D5' },
  { name: 'Records', on: 'records on', off: 'records off', id: 'D1' },
] as const


// ---------- drawing a picture ----------

/** A picture as one SVG document, for a surface that draws `Svg`. */
export const pictureSvg = (p: Picture, ink: Ink, size = 56): string => {
  switch (p.kind) {
    case 'rings': {
      // Rings side by side in one document: each ring's own markup, shifted.
      const one = p.rings.map(r => ringSvg({ pct: r.pct, tick: r.tick, label: r.label, ink, size, ...(r.warnAt === undefined ? {} : { warnAt: r.warnAt }) }))
      if (one.length === 1) return one[0]!
      const gap = 8
      const w = one.length * size + (one.length - 1) * gap
      const inner = one.map((svg, i) => svg.replace('<svg ', `<svg x="${i * (size + gap)}" `)).join('')
      return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${size}" viewBox="0 0 ${w} ${size}" role="img">${inner}</svg>`
    }
    case 'spark': return sparkSvg(p.values, ink, 120, 32, 'tokens by day, 7 days')
    case 'bar': return barSvg(p.segs, ink)
    case 'dots': return dotsSvg(p.dots, ink)
    case 'badge': return badgeSvg(p.n, ink)
    case 'word': return `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="24" viewBox="0 0 120 24" role="img"><text x="0" y="18" font-family="system-ui,sans-serif" font-size="16" fill="${ink.accent}">${p.text.replace(/[&<>"']/g, '')}</text></svg>`
  }
}

/** What a reader without the picture gets: the same facts in words. */
export const pictureAlt = (p: Picture): string => {
  switch (p.kind) {
    case 'rings': return p.rings.map(r => `${r.label} ${pct(r.pct)}${r.tick === null ? '' : `, pace ${Math.round(r.tick)}%`}`).join('; ')
    case 'spark': return `tokens by day: ${p.values.map(k).join(', ')}`
    case 'bar': return p.segs.map(x => `${x.label} ${x.n}`).join(', ')
    case 'dots': return p.dots.map(x => `${x.label} ${x.ok === null ? 'unknown' : x.ok ? 'ok' : 'failing'}`).join(', ') || 'no checks yet'
    case 'badge': return `${p.n} waiting`
    case 'word': return p.text
  }
}

/** A picture as one line of glyphs, for the terminal. */
export const pictureGlyph = (p: Picture, g: Glyph, on = '●', off = '○', bad = '✗'): string => {
  switch (p.kind) {
    case 'rings': return p.rings.map(r => `${r.label} ${glyphMeter(r.pct, 4, g)}`).join('  ')
    case 'spark': return glyphSpark(p.values)
    case 'bar': return p.segs.map(x => `${x.label} ${x.n}`).join(' · ')
    case 'dots': return glyphDots(p.dots, on, off, bad) || '–'
    case 'badge': return p.n ? `${on} ${p.n}` : off
    case 'word': return p.text
  }
}

/** The glance strip as text: `5h ▰▰▱▱  wk ▰▰▰▱  ctx ▰▱▱▱` and a mark when something needs you. */
export const glanceText = (gl: Glance, g: Glyph, mark = '●'): string =>
  `${gl.rings.map(r => `${r.label} ${glyphMeter(r.pct, 4, g)}`).join('  ')}${gl.needsYou ? `  ${mark} ${gl.needsYou}` : ''}`

/** The board as text lines (a typed /rw-vigil board, and the terminal's fallback). */
export const boardText = (l: Layout, d: BoardData, g: Glyph): string[] => {
  const out: string[] = []
  for (const id of arranged(l)) {
    const t = tileOf(id, d)
    const pin = l.pinned.includes(id) ? ' (pinned)' : ''
    if (l.collapsed.includes(id)) {
      out.push(`  ${t.title}${pin}: ${t.big}`)
      continue
    }
    out.push(`  ${t.title}${pin}: ${t.big}, ${t.sub}`, `    ${pictureGlyph(t.picture, g)}`)
  }
  return out
}
