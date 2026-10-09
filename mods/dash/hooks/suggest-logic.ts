// dash suggestion queue: pure logic (no $). Owner 2026-10-08: self-improving, never builds.
// Rows come from evidence in the event file; the person accepts (copies the row to NEXT.md),
// dismisses or snoozes. Nothing is ever built, written to settings or allowed.
import { DAY, TRIVIAL_SHAPES, type DashEvent, type Feed } from './collector-logic'
import { fnv1a } from './lib/util'

export const T = {
  /** The same command shape this many times... */
  cmdTimes: 5,
  /** ...across this many sessions... */
  cmdSessions: 3,
  /** ...within this many days. */
  cmdDays: 7,
  /** The same permission prompt shape this many times in 7 days. */
  permTimes: 3,
  permDays: 7,
  /** A listed skill with no fire for this many days (and listed at least that long). */
  unusedDays: 30,
  /** A skill fired by slash more than this share of its fires... */
  slashShare: 0.7,
  /** ...once it has at least this many fires in 30 days. */
  slashMinFires: 5,
  /** Context past 80% this many times in one day. */
  ctxTimesADay: 2,
  /** One skill past this share of the week's tokens... */
  skillTokenShare: 0.25,
  /** ...once the week holds at least this many tokens. */
  skillTokenMin: 200_000,
  /** A dismissed row stays quiet this long. */
  quietDays: 30,
  /** A snooze lasts this long. */
  snoozeDays: 7,
  /** At most this many rows are kept. */
  maxRows: 60,
} as const

export type SuggestKind = 'command' | 'allow' | 'unused' | 'description' | 'slim-context' | 'slim-skill'
export type SuggestState = 'new' | 'shown' | 'accepted' | 'dismissed' | 'snoozed'

export type Candidate = { key: string; kind: SuggestKind; title: string; evidence: string; action: string }

export type Suggestion = Candidate & {
  id: string
  state: SuggestState
  createdAt: number
  stateAt: number
  snoozeUntil?: number
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/** Every row the evidence supports today. One candidate per key. */
export const candidates = (events: readonly DashEvent[], feed: Feed, now: number): Candidate[] => {
  const out: Candidate[] = []
  // 1. The same normalised command, 5+ times in 3+ sessions in 7 days.
  const cmds = new Map<string, { n: number; sessions: Set<string> }>()
  const perms = new Map<string, number>()
  for (const e of events) {
    if (e.k === 'cmd' && now - e.t <= T.cmdDays * DAY && !TRIVIAL_SHAPES.has(e.shape)) {
      const c = cmds.get(e.shape) ?? { n: 0, sessions: new Set<string>() }
      c.n += 1
      c.sessions.add(e.s)
      cmds.set(e.shape, c)
    }
    if (e.k === 'perm' && now - e.t <= T.permDays * DAY) perms.set(e.shape, (perms.get(e.shape) ?? 0) + 1)
  }
  for (const [shape, c] of cmds) {
    if (c.n >= T.cmdTimes && c.sessions.size >= T.cmdSessions) {
      out.push({ key: `command:${shape}`, kind: 'command', title: `Make "${shape}" a command or a skill`, evidence: `${plural(c.n, 'run')} in ${plural(c.sessions.size, 'session')} in ${T.cmdDays} days`, action: 'Write a slash command or a skill for it (skillwright).' })
    }
  }
  // 2. The same permission prompt shape, 3+ times in 7 days.
  for (const [shape, n] of perms) {
    if (n >= T.permTimes) out.push({ key: `allow:${shape}`, kind: 'allow', title: `Review an allow rule for "${shape}"`, evidence: `asked ${plural(n, 'time')} in ${T.permDays} days`, action: 'Ask gatewarden (harden) whether an allow rule fits. dash writes and allows nothing.' })
  }
  for (const s of feed.skills) {
    // 3. Listed but unused for 30 days.
    if (s.listed && s.firstListed !== null && now - s.firstListed >= T.unusedDays * DAY && s.fires30 === 0) {
      out.push({ key: `unused:${s.name}`, kind: 'unused', title: `Probe or retire ${s.name}`, evidence: `listed for ${Math.floor((now - s.firstListed) / DAY)} days, no fire in ${T.unusedDays}`, action: 'Ask a should-fire query (skillwright evals); if it never fits, retire it.' })
    }
    // 4. Fired mostly by slash: Claude rarely picks it on its own.
    if (s.fires30 >= T.slashMinFires && s.slash30 / s.fires30 > T.slashShare) {
      out.push({ key: `description:${s.name}`, kind: 'description', title: `Rewrite the description of ${s.name}`, evidence: `${Math.round((s.slash30 / s.fires30) * 100)}% of ${plural(s.fires30, 'fire')} in 30 days were by slash`, action: 'Rewrite its description so Claude picks it when you ask (skillwright).' })
    }
  }
  // 5a. Context past 80% twice in one day.
  const days = new Map<string, number>()
  for (const e of events) if (e.k === 'ctx80' && now - e.t <= 7 * DAY) days.set(new Date(e.t).toISOString().slice(0, 10), (days.get(new Date(e.t).toISOString().slice(0, 10)) ?? 0) + 1)
  const hot = [...days.entries()].filter(([, n]) => n >= T.ctxTimesADay).map(([d]) => d).sort()
  if (hot.length > 0) out.push({ key: 'slim:context', kind: 'slim-context', title: 'Slim what loads every turn', evidence: `context passed 80% twice or more on ${hot.join(', ')}`, action: 'Measure and slim CLAUDE.md, rules and always-loaded skills (rigwright slim).' })
  // 5b. One skill over a quarter of the week's tokens.
  if (feed.tokens7 >= T.skillTokenMin) {
    for (const s of feed.skills) {
      if (s.tokens7 / feed.tokens7 > T.skillTokenShare) out.push({ key: `slim:${s.name}`, kind: 'slim-skill', title: `Slim ${s.name}`, evidence: `${Math.round((s.tokens7 / feed.tokens7) * 100)}% of the week's tokens`, action: 'Measure its footprint and cut what every run reads (skillwright slim).' })
    }
  }
  const seen = new Set<string>()
  return out.filter(c => (seen.has(c.key) ? false : (seen.add(c.key), true)))
}

/**
 * Merge today's candidates into the queue. Dedupe by key; an accepted row never comes back; a
 * dismissed row stays quiet for 30 days and returns only with fresh evidence; a snoozed row
 * returns when its snooze ends. Rows whose evidence went away keep their state.
 */
export const mergeSuggestions = (rows: readonly Suggestion[], cands: readonly Candidate[], now: number): Suggestion[] => {
  const byKey = new Map(rows.map(r => [r.key, r]))
  const out: Suggestion[] = rows.map(r => {
    const c = cands.find(x => x.key === r.key)
    if (r.state === 'snoozed' && (r.snoozeUntil ?? 0) <= now) {
      const { snoozeUntil: _drop, ...rest } = r
      return c ? { ...rest, ...c, state: 'new', stateAt: now } : { ...rest, state: 'new', stateAt: now }
    }
    if (r.state === 'dismissed' && c && now - r.stateAt >= T.quietDays * DAY) return { ...r, ...c, state: 'new', stateAt: now }
    if ((r.state === 'new' || r.state === 'shown') && c) return { ...r, ...c }
    return r
  })
  for (const c of cands) if (!byKey.has(c.key)) out.push({ ...c, id: fnv1a(c.key).slice(0, 6), state: 'new', createdAt: now, stateAt: now })
  // Oldest settled rows go first when the queue is full; open rows are kept.
  const open = out.filter(r => r.state === 'new' || r.state === 'shown' || r.state === 'snoozed')
  const settled = out.filter(r => !open.includes(r)).sort((a, b) => b.stateAt - a.stateAt)
  return [...open, ...settled].slice(0, T.maxRows)
}

/** At most one note per session: the oldest new row, marked shown. */
export const pickNote = (rows: readonly Suggestion[], notedThisSession: boolean, now: number): { rows: Suggestion[]; note: Suggestion | null } => {
  if (notedThisSession) return { rows: [...rows], note: null }
  const next = [...rows].filter(r => r.state === 'new').sort((a, b) => a.createdAt - b.createdAt)[0]
  if (!next) return { rows: [...rows], note: null }
  const shown: Suggestion = { ...next, state: 'shown', stateAt: now }
  return { rows: rows.map(r => (r.id === next.id ? shown : r)), note: shown }
}

/** The rows a person acts on, in a stable order: open first, then settled. Numbered from 1. */
export const listed = (rows: readonly Suggestion[]): Suggestion[] => {
  const rank: Record<SuggestState, number> = { new: 0, shown: 1, snoozed: 2, accepted: 3, dismissed: 4 }
  return [...rows].sort((a, b) => rank[a.state] - rank[b.state] || a.createdAt - b.createdAt || a.key.localeCompare(b.key))
}

/** The line the person copies to NEXT.md when they accept. dash never writes it there. */
export const nextMdLine = (r: Suggestion, now: number): string =>
  `- [ ] ${r.title}: ${r.action} Evidence: ${r.evidence}. (dash ${r.id}, ${new Date(now).toISOString().slice(0, 10)})`

export type SuggestVerb = 'accept' | 'dismiss' | 'snooze'

/** `/dash suggest accept|dismiss|snooze <n or id>`. */
export const actOn = (rows: readonly Suggestion[], verb: SuggestVerb, ref: string, now: number): { rows: Suggestion[]; text: string } => {
  const ordered = listed(rows)
  const n = Number(ref)
  const target = Number.isInteger(n) && n >= 1 ? ordered[n - 1] : ordered.find(r => r.id === ref)
  if (!target) return { rows: [...rows], text: `No suggestion "${ref}". /dash suggest lists them by number.` }
  const state: SuggestState = verb === 'accept' ? 'accepted' : verb === 'dismiss' ? 'dismissed' : 'snoozed'
  const next: Suggestion = { ...target, state, stateAt: now, ...(verb === 'snooze' ? { snoozeUntil: now + T.snoozeDays * DAY } : {}) }
  const out = rows.map(r => (r.id === target.id ? next : r))
  if (verb === 'accept') return { rows: out, text: `Accepted. Copy this line to NEXT.md yourself; dash writes nothing there:\n${nextMdLine(next, now)}` }
  if (verb === 'dismiss') return { rows: out, text: `Dismissed: ${target.title}. Quiet for ${T.quietDays} days; it comes back only with fresh evidence.` }
  return { rows: out, text: `Snoozed for ${T.snoozeDays} days: ${target.title}.` }
}

export const suggestionLines = (rows: readonly Suggestion[]): string[] => {
  const ordered = listed(rows)
  if (ordered.length === 0) return ['No suggestions yet. They come from what the collector counts (/dash records on).']
  return [
    ...ordered.map((r, i) => `${String(i + 1).padStart(2)}. [${r.state}] ${r.title} (${r.evidence})`),
    '/dash suggest accept|dismiss|snooze <n>. Accepting gives you a line for NEXT.md; nothing is built or allowed.',
  ]
}

export const parseSuggestions = (text: string | null): Suggestion[] => {
  if (!text) return []
  try {
    const raw = JSON.parse(text) as { rows?: unknown }
    const rows = Array.isArray(raw.rows) ? raw.rows : []
    const states: SuggestState[] = ['new', 'shown', 'accepted', 'dismissed', 'snoozed']
    return rows.filter((r): r is Suggestion => !!r && typeof r === 'object' && typeof (r as Suggestion).key === 'string' && typeof (r as Suggestion).id === 'string' && states.includes((r as Suggestion).state))
  } catch {
    return []
  }
}

export const serializeSuggestions = (rows: readonly Suggestion[], now: number): string =>
  `${JSON.stringify({ version: 1, updatedAt: new Date(now).toISOString(), rows }, null, 2)}\n`
