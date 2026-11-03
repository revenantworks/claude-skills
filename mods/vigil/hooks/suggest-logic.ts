// vigil suggestions: pure logic (no $). A short list of what is worth doing, never a log: at most
// `maxOpen` cards, strongest first. The person takes one (Claude drafts it in chat), hides it or
// says never. Nothing is ever built, written to settings or allowed.
import { DAY, type DashEvent, type Feed } from './collector-logic'
import { fnv1a } from './lib/util'

export const T = {
  /** The same permission prompt shape this many times in 7 days. */
  permTimes: 3,
  permDays: 7,
  /** The same work, stripped to its core steps, this many times... */
  cmdTimes: 20,
  /** ...across this many sessions... */
  cmdSessions: 5,
  /** ...within this many days. */
  cmdDays: 7,
  /** A listed skill with no fire for this many days (and listed at least that long). */
  unusedDays: 30,
  /** A skill fired by slash more than this share of its fires... */
  slashShare: 0.7,
  /** ...once it has at least this many fires in 30 days. */
  slashMinFires: 5,
  /** Context past 80% this many times in one day. */
  ctxTimesADay: 2,
  /** A skill whose turns average this many times the tokens of the turns without it... */
  skillLift: 1.5,
  /** ...holding at least this share of the week's tokens... */
  skillTokenShare: 0.1,
  /** ...over at least this many turns with it and this many without... */
  skillMinTurns: 5,
  /** ...once the week holds at least this many tokens. */
  skillTokenMin: 200_000,
  /** A dismissed row stays quiet this long. */
  quietDays: 30,
  /** A snooze lasts this long. */
  snoozeDays: 7,
  /** At most this many open cards; the weakest wait outside the queue until one clears. */
  maxOpen: 5,
  /** Settled rows kept, so a dismissal holds. An open row never pushes one out. */
  maxSettled: 60,
  /** An open row with no fresh evidence for this long leaves the queue. */
  staleDays: 3,
} as const

/** `allow` rows came from the retired `perm` count; they stay as the record and never reopen. */
export type SuggestKind = 'command' | 'prompt' | 'allow' | 'unused' | 'description' | 'slim-context' | 'slim-skill'
export type SuggestState = 'new' | 'shown' | 'accepted' | 'dismissed' | 'snoozed'

/** `count` is the evidence size the cards sort on: prompts for a prompt row, runs for a command. */
export type Candidate = { key: string; kind: SuggestKind; title: string; evidence: string; action: string; count?: number }

export type Suggestion = Candidate & {
  id: string
  state: SuggestState
  createdAt: number
  stateAt: number
  snoozeUntil?: number
  /** When a roll last found evidence for it; an open row unseen for `staleDays` drops out. */
  lastSeen?: number
  /** Never: a dismissal the quiet window does not end. */
  forever?: boolean
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

// ---------- what counts as the same work ----------

/** Programs that only read, print or wait: never the work itself. */
const READ_ONLY = new Set([
  'sed', 'grep', 'rg', 'cat', 'head', 'tail', 'cut', 'wc', 'ls', 'echo', 'find', 'pwd', 'sort', 'uniq',
  'date', 'for', 'while', 'if', 'seq', 'tr', 'awk', 'which', 'type', 'printf', 'stat', 'file', 'true', 'false',
  'sleep', 'test', 'xargs', 'tee', 'basename', 'dirname',
  'get-content', 'select-string', 'get-childitem', 'select-object', 'write-output', 'measure-object',
])
/** Tools that ask by design (a question to you, a plan to approve): an allow rule never fits. */
const ASKS_BY_DESIGN = new Set(['askuserquestion', 'exitplanmode', 'enterplanmode'])
const CLOSER = new Set(['done', 'fi', 'esac'])
/** A step that names no particular job: `git anything`, a bare interpreter, an unnamed script. */
const GENERIC_STEP = /^(?:git\b.*|(?:python3?|py|node|bash|sh|pwsh|powershell)(?: -[cIeE]| \*\.\w+)*)$/

/**
 * A chain with its noise taken out: `cd`, read-only steps and block closers go, a repeated step
 * counts once. `cd ; python -m unittest ; tail` and `python -m unittest ; grep -E` are one job. Empty when
 * nothing is left.
 */
export const coreShape = (shape: string): string => {
  const steps = shape.split(' ; ').map(x => x.trim()).filter(x => {
    const prog = x.split(' ')[0] ?? ''
    return prog && prog !== 'cd' && !READ_ONLY.has(prog) && !CLOSER.has(prog)
  })
  return [...new Set(steps)].join(' ; ')
}

/** Whether a core shape is a job worth naming: at least one step says what it does. */
const namesAJob = (core: string): boolean => core.split(' ; ').some(x => x !== '' && !GENERIC_STEP.test(x))

const isOpenState = (s: SuggestState) => s === 'new' || s === 'shown'

/** Evidence that should never hold a card, in the current rules or the retired ones. */
export const suppressed = (key: string): boolean => {
  if (key.startsWith('command:')) {
    const shape = key.slice('command:'.length)
    return coreShape(shape) !== shape || !namesAJob(shape)
  }
  if (key.startsWith('prompt:')) return ASKS_BY_DESIGN.has(key.slice('prompt:'.length).split(' ')[0] ?? '')
  return key.startsWith('allow:') || (key.startsWith('slim:') && key !== 'slim:context') || (key.startsWith('unused:') && key !== UNUSED_KEY)
}

const UNUSED_KEY = 'unused:skills'

/** Every row the evidence supports today. One candidate per key. */
export const candidates = (events: readonly DashEvent[], feed: Feed, now: number): Candidate[] => {
  const out: Candidate[] = []
  const cmds = new Map<string, { n: number; sessions: Set<string> }>()
  const perms = new Map<string, number>()
  for (const e of events) {
    if (e.k === 'cmd' && now - e.t <= T.cmdDays * DAY) {
      const core = coreShape(e.shape)
      if (!core || !namesAJob(core)) continue
      const c = cmds.get(core) ?? { n: 0, sessions: new Set<string>() }
      c.n += 1
      c.sessions.add(e.s)
      cmds.set(core, c)
    }
    if (e.k === 'prompt' && e.shape && now - e.t <= T.permDays * DAY) perms.set(e.shape, (perms.get(e.shape) ?? 0) + 1)
  }
  for (const [shape, c] of cmds) {
    if (c.n >= T.cmdTimes && c.sessions.size >= T.cmdSessions) {
      out.push({ key: `command:${shape}`, kind: 'command', title: `Claude keeps running "${shape}"`, evidence: `${plural(c.n, 'run')} in ${plural(c.sessions.size, 'session')} this week`, action: 'A script or a skill could make this one step (skillwright).', count: c.n })
    }
  }
  for (const [shape, n] of perms) {
    if (n >= T.permTimes) out.push({ key: `prompt:${shape}`, kind: 'prompt', title: `You keep being asked about "${shape}"`, evidence: `asked you ${plural(n, 'time')} this week`, action: 'Allow it (gatewarden harden checks the rule first) or change how Claude makes the call. vigil writes and allows nothing.', count: n })
  }
  // Skills nobody fires are one decision, not one card each.
  const quiet = feed.skills.filter(s => s.listed && s.firstListed !== null && now - s.firstListed >= T.unusedDays * DAY && s.fires30 === 0).map(s => s.name).sort()
  if (quiet.length > 0) out.push({ key: UNUSED_KEY, kind: 'unused', title: `${plural(quiet.length, 'skill')} never fired in ${T.unusedDays} days`, evidence: quiet.length > 3 ? `${quiet.slice(0, 3).join(', ')} and ${quiet.length - 3} more` : quiet.join(', '), action: 'Check them with /skill-doctor, then probe with a should-fire query or retire them (skillwright evals).', count: quiet.length })
  for (const s of feed.skills) {
    if (s.fires30 >= T.slashMinFires && s.slash30 / s.fires30 > T.slashShare) {
      out.push({ key: `description:${s.name}`, kind: 'description', title: `Rewrite the description of ${s.name}`, evidence: `${Math.round((s.slash30 / s.fires30) * 100)}% of ${plural(s.fires30, 'fire')} in 30 days were by slash`, action: 'Rewrite its description so Claude picks it when you ask (skillwright).' })
    }
  }
  const days = new Map<string, number>()
  for (const e of events) if (e.k === 'ctx80' && now - e.t <= 7 * DAY) days.set(new Date(e.t).toISOString().slice(0, 10), (days.get(new Date(e.t).toISOString().slice(0, 10)) ?? 0) + 1)
  const hot = [...days.entries()].filter(([, n]) => n >= T.ctxTimesADay).map(([d]) => d).sort()
  if (hot.length > 0) out.push({ key: 'slim:context', kind: 'slim-context', title: 'Slim what loads every turn', evidence: `context passed 80% twice or more on ${hot.join(', ')}`, action: 'Measure and slim CLAUDE.md, rules and always-loaded skills (rigwright slim).' })
  // A turn's tokens are the whole turn's, so a skill that loads in most turns owns most tokens and
  // proves nothing; only the lift over its own week's other turns says the skill makes a turn heavier.
  const turnsAll = feed.turns7 ?? 0
  if (feed.tokens7 >= T.skillTokenMin) {
    for (const s of feed.skills) {
      const turns = s.turns7 ?? 0
      const otherTurns = turnsAll - turns
      if (turns < T.skillMinTurns || otherTurns < T.skillMinTurns || s.tokens7 / feed.tokens7 < T.skillTokenShare) continue
      const lift = s.tokens7 / turns / ((feed.tokens7 - s.tokens7) / otherTurns)
      if (lift >= T.skillLift) out.push({ key: `heavy:${s.name}`, kind: 'slim-skill', title: `Slim ${s.name}`, evidence: `its turns average ${lift.toFixed(1)}x the tokens of turns without it (${plural(turns, 'turn')} this week)`, action: 'Measure its footprint and cut what every run reads (skillwright slim).' })
    }
  }
  const seen = new Set<string>()
  return out.filter(c => !suppressed(c.key) && (seen.has(c.key) ? false : (seen.add(c.key), true)))
}

/** What interrupts the person ranks first; what only tidies ranks last. */
const RANK: Record<SuggestKind, number> = { prompt: 0, 'slim-skill': 1, 'slim-context': 1, description: 2, unused: 3, command: 4, allow: 5 }

/** Strongest first: by kind, then by evidence, then oldest. Stable across redraws. */
export const listed = (rows: readonly Suggestion[]): Suggestion[] =>
  [...rows].sort((a, b) => RANK[a.kind] - RANK[b.kind] || (b.count ?? 0) - (a.count ?? 0) || a.createdAt - b.createdAt || a.key.localeCompare(b.key))

/**
 * Merge today's candidates into the queue. Dedupe by key; an accepted row never comes back; a
 * dismissed row stays quiet for 30 days and returns only with fresh evidence; a snoozed row returns
 * when its snooze ends. Open rows are capped and settled rows are kept apart, so a full queue can
 * never push a dismissal out and bring the row back.
 */
export const mergeSuggestions = (rows: readonly Suggestion[], cands: readonly Candidate[], now: number): Suggestion[] => {
  const byKey = new Map(rows.map(r => [r.key, r]))
  const fresh = new Map(cands.map(c => [c.key, c]))
  const out: Suggestion[] = rows.map(r => {
    const c = fresh.get(r.key)
    const seen = c ? { lastSeen: now } : {}
    if (r.state === 'snoozed' && (r.snoozeUntil ?? 0) <= now) {
      const { snoozeUntil: _drop, ...rest } = r
      return c ? { ...rest, ...c, ...seen, state: 'new', stateAt: now } : { ...rest, state: 'new', stateAt: now }
    }
    if (r.state === 'dismissed' && !r.forever && c && now - r.stateAt >= T.quietDays * DAY) return { ...r, ...c, ...seen, state: 'new', stateAt: now }
    if (isOpenState(r.state) && c) return { ...r, ...c, ...seen }
    return r
  })
  for (const c of cands) if (!byKey.has(c.key)) out.push({ ...c, id: fnv1a(c.key).slice(0, 6), state: 'new', createdAt: now, stateAt: now, lastSeen: now })
  const live = out.filter(r => !(isOpenState(r.state) && (suppressed(r.key) || now - (r.lastSeen ?? r.stateAt) > T.staleDays * DAY)))
  const open = listed(live.filter(r => isOpenState(r.state))).slice(0, T.maxOpen)
  const snoozed = live.filter(r => r.state === 'snoozed')
  const settled = live.filter(r => r.state === 'accepted' || r.state === 'dismissed').sort((a, b) => b.stateAt - a.stateAt).slice(0, T.maxSettled)
  return [...open, ...snoozed, ...settled]
}

/** At most one note per session: the strongest new row, marked shown, so it is never raised twice. */
export const pickNote = (rows: readonly Suggestion[], notedThisSession: boolean, now: number): { rows: Suggestion[]; note: Suggestion | null } => {
  if (notedThisSession) return { rows: [...rows], note: null }
  const next = listed(rows.filter(r => r.state === 'new'))[0]
  if (!next) return { rows: [...rows], note: null }
  const shown: Suggestion = { ...next, state: 'shown', stateAt: now }
  return { rows: rows.map(r => (r.id === next.id ? shown : r)), note: shown }
}

/** A card by its number in the list (`2`) or its id. */
export const resolveRef = (rows: readonly Suggestion[], ref: string): Suggestion | null => {
  const r = ref.trim()
  const open = listed(rows.filter(x => isOpenState(x.state)))
  return /^\d+$/.test(r) ? (open[Number(r) - 1] ?? null) : (rows.find(x => x.id === r) ?? null)
}

export type SuggestVerb = 'accept' | 'dismiss' | 'snooze'

/** `/rw-vigil suggest dismiss|snooze <n>`, or an accept with no reply of its own (the caller drafts it). */
export const actOn = (rows: readonly Suggestion[], verb: SuggestVerb, ref: string, now: number): { rows: Suggestion[]; text: string; hit: Suggestion | null } => {
  const hit = resolveRef(rows, ref)
  if (!hit) return { rows: [...rows], text: `No suggestion "${ref}". /rw-vigil suggest numbers them.`, hit: null }
  const state: SuggestState = verb === 'accept' ? 'accepted' : verb === 'dismiss' ? 'dismissed' : 'snoozed'
  const done: Suggestion = { ...hit, state, stateAt: now, ...(verb === 'snooze' ? { snoozeUntil: now + T.snoozeDays * DAY } : {}) }
  const text = verb === 'accept' ? `Taken: ${hit.title}.` : verb === 'dismiss' ? `Dismissed: ${hit.title}. Quiet for ${T.quietDays} days; it comes back only with fresh evidence.` : `Snoozed for ${T.snoozeDays} days: ${hit.title}.`
  return { rows: rows.map(r => (r.id === hit.id ? done : r)), text, hit: done }
}

/** Never: this row stays dismissed, whatever the evidence says later. */
export const neverAgain = (rows: readonly Suggestion[], id: string, now: number): Suggestion[] =>
  rows.map(r => (r.id === id ? { ...r, state: 'dismissed' as const, stateAt: now, forever: true } : r))

/** A row written before `count` existed carries it only in its evidence ("asked 91 times", "247 runs"). */
const countFromEvidence = (evidence: unknown): number | null => {
  const m = typeof evidence === 'string' ? /^(?:asked )?(\d+) (?:times?|runs?)\b/.exec(evidence) : null
  return m ? Number(m[1]) : null
}

export const parseSuggestions = (text: string | null): Suggestion[] => {
  if (!text) return []
  try {
    const raw = JSON.parse(text) as { rows?: unknown }
    const rows = Array.isArray(raw.rows) ? raw.rows : []
    const states: SuggestState[] = ['new', 'shown', 'accepted', 'dismissed', 'snoozed']
    return rows
      .filter((r): r is Suggestion => !!r && typeof r === 'object' && typeof (r as Suggestion).key === 'string' && typeof (r as Suggestion).id === 'string' && states.includes((r as Suggestion).state))
      .map(r => (typeof r.count === 'number' || !countFromEvidence(r.evidence) ? r : { ...r, count: countFromEvidence(r.evidence)! }))
  } catch {
    return []
  }
}

export const serializeSuggestions = (rows: readonly Suggestion[], now: number): string =>
  `${JSON.stringify({ version: 1, updatedAt: new Date(now).toISOString(), rows }, null, 2)}\n`
