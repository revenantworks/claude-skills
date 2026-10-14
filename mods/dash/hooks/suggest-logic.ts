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
  /** At most this many rows are kept; the views group them, so the cap is generous. */
  maxRows: 200,
  /** An open row with no fresh evidence for this long leaves the queue. */
  staleDays: 14,
} as const

/** `allow` rows came from the retired `perm` count; they stay as the record and never reopen. */
export type SuggestKind = 'command' | 'prompt' | 'allow' | 'unused' | 'description' | 'slim-context' | 'slim-skill'
export type SuggestState = 'new' | 'shown' | 'accepted' | 'dismissed' | 'snoozed'

/** `count` is the evidence size the views sort on: prompts for an allow row, runs for a command. */
export type Candidate = { key: string; kind: SuggestKind; title: string; evidence: string; action: string; count?: number }

export type Suggestion = Candidate & {
  id: string
  state: SuggestState
  createdAt: number
  stateAt: number
  snoozeUntil?: number
  /** When a roll last found evidence for it; an open row unseen for `staleDays` drops out. */
  lastSeen?: number
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

// ---------- grouping ----------

/** Programs that only read or print. A chain of these alone is one group, never a command row. */
const READ_ONLY = new Set([
  'sed', 'grep', 'rg', 'cat', 'head', 'tail', 'cut', 'wc', 'ls', 'echo', 'find', 'pwd', 'sort', 'uniq',
  'date', 'for', 'tr', 'awk', 'which', 'type', 'printf', 'stat', 'file', 'true', 'sleep', 'test', 'xargs',
  'get-content', 'select-string', 'get-childitem', 'select-object', 'write-output', 'measure-object',
])
/** Tools that ask by design (a question to you, a plan to approve): an allow rule never fits. */
const ASKS_BY_DESIGN = new Set(['askuserquestion', 'exitplanmode', 'enterplanmode'])
const SHELLS = new Set(['bash', 'powershell'])

export const READ_ONLY_GROUP = 'shell: read-only'
export const TOOLS_GROUP = 'Claude Code tools'

/** A shell shape's lead program: the first one that is not `cd` or read-only; null when none. */
const leadProgram = (shape: string): string | null => {
  for (const seg of shape.split(' ; ')) {
    const prog = seg.trim().split(' ')[0] ?? ''
    if (prog && prog !== 'cd' && !READ_ONLY.has(prog)) return prog
  }
  return null
}

/** The key's shape with the tool word dropped from a shell prompt, so a run and a prompt line up. */
export const subLabel = (key: string): string => {
  const i = key.indexOf(':')
  const kind = key.slice(0, i)
  const rest = key.slice(i + 1)
  if (kind === 'allow' || kind === 'prompt') {
    const [tool, ...shell] = rest.split(' ')
    return SHELLS.has(tool ?? '') && shell.length > 0 ? shell.join(' ') : rest
  }
  return rest
}

/** The command type a row rolls up under. Derived from the key, so stored rows need no migration. */
export const groupOf = (key: string): string => {
  const i = key.indexOf(':')
  const kind = key.slice(0, i)
  const rest = key.slice(i + 1)
  if (kind === 'unused' || kind === 'description') return 'skills'
  if (kind === 'slim') return rest === 'context' ? 'context' : 'skills'
  if (kind === 'heavy') return 'skills'
  let shell = rest
  if (kind === 'allow' || kind === 'prompt') {
    const tool = rest.split(' ')[0] ?? ''
    if (tool.startsWith('mcp__')) return `mcp: ${tool.split('__')[1] ?? tool}`
    if (!SHELLS.has(tool)) return TOOLS_GROUP
    shell = subLabel(key)
  }
  const lead = leadProgram(shell)
  return lead ? `shell: ${lead}` : READ_ONLY_GROUP
}

/** A block closer as a whole segment, a prompt's tool word allowed before it (`bash done`). */
const CLOSER_SEG = /^(?:(?:bash|powershell) )?(?:done|fi|esac)$/

/** A shape stored before the reader dropped the block closers: `grep -q ; sleep ; done` is `grep -q ; sleep`. */
export const withoutClosers = (shape: string): string => shape.split(' ; ').filter(seg => !CLOSER_SEG.test(seg.trim())).join(' ; ')

/** Evidence that should never become a row: a read-only chain as a command, a by-design question. */
export const suppressed = (key: string): boolean =>
  (key.startsWith('command:') && groupOf(key) === READ_ONLY_GROUP) ||
  (key.startsWith('prompt:') && ASKS_BY_DESIGN.has(key.slice('prompt:'.length).split(' ')[0] ?? '')) ||
  // Built from the retired count, which held auto mode's classifier reviews too: never an open row.
  key.startsWith('allow:') ||
  // Retired 2026-10-13: a skill's share of all tokens, which billed a whole turn to the skill that
  // loaded in it, so a skill loaded every turn looked like most of the week. `heavy:` replaced it.
  (key.startsWith('slim:') && key !== 'slim:context') ||
  // A shape stored before the reader dropped `done`, `fi` and `esac` (2026-10-13).
  ((key.startsWith('command:') || key.startsWith('prompt:')) && withoutClosers(key) !== key)

/** What to do about a whole group, in one line. */
export const groupAction = (group: string): string => {
  if (group === READ_ONLY_GROUP) return 'These only read (sed, grep, cat...); the same reads without a leading cd are rarely asked. Run cd in its own call or use absolute paths, and prefer the Read and Grep tools.'
  if (group === TOOLS_GROUP) return "Claude Code's own tools. Ask gatewarden (harden) whether an allow rule fits; dash allows nothing."
  if (group.startsWith('mcp: ')) return "One MCP server's tools. Ask gatewarden whether the server's read tools fit an allow rule."
  if (group.startsWith('shell: ')) return 'Repeated runs: a slash command or skill (skillwright). Repeated prompts: ask gatewarden about an allow rule.'
  if (group === 'context') return 'Measure and slim what loads every turn (rigwright slim).'
  return 'Probe, rewrite or slim the skills named (skillwright).'
}

/** Every row the evidence supports today. One candidate per key. */
export const candidates = (events: readonly DashEvent[], feed: Feed, now: number): Candidate[] => {
  const out: Candidate[] = []
  // 1. The same normalised command, 5+ times in 3+ sessions in 7 days.
  const cmds = new Map<string, { n: number; sessions: Set<string> }>()
  const perms = new Map<string, number>()
  for (const e of events) {
    const shape = e.k === 'cmd' || e.k === 'prompt' ? withoutClosers(e.shape) : ''
    if (e.k === 'cmd' && shape && now - e.t <= T.cmdDays * DAY && !TRIVIAL_SHAPES.has(shape)) {
      const c = cmds.get(shape) ?? { n: 0, sessions: new Set<string>() }
      c.n += 1
      c.sessions.add(e.s)
      cmds.set(shape, c)
    }
    if (e.k === 'prompt' && shape && now - e.t <= T.permDays * DAY) perms.set(shape, (perms.get(shape) ?? 0) + 1)
  }
  for (const [shape, c] of cmds) {
    if (c.n >= T.cmdTimes && c.sessions.size >= T.cmdSessions) {
      out.push({ key: `command:${shape}`, kind: 'command', title: `Make "${shape}" a command or a skill`, evidence: `${plural(c.n, 'run')} in ${plural(c.sessions.size, 'session')} in ${T.cmdDays} days`, action: 'Write a slash command or a skill for it (skillwright).', count: c.n })
    }
  }
  // 2. The same permission prompt shape, 3+ times in 7 days.
  for (const [shape, n] of perms) {
    if (n >= T.permTimes) out.push({ key: `prompt:${shape}`, kind: 'prompt', title: `You were asked about "${shape}"`, evidence: `asked you ${plural(n, 'time')} in ${T.permDays} days`, action: 'Allow it (gatewarden harden checks the rule first) or change how Claude makes the call. dash writes and allows nothing.', count: n })
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
  // 5b. A skill whose turns cost clearly more than the turns without it. A turn's tokens are the
  // whole turn's, so a skill that loads in most turns owns most tokens and proves nothing; only
  // the lift over its own week's other turns says the skill makes a turn heavier.
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

/**
 * Merge today's candidates into the queue. Dedupe by key; an accepted row never comes back; a
 * dismissed row stays quiet for 30 days and returns only with fresh evidence; a snoozed row
 * returns when its snooze ends. Rows whose evidence went away keep their state.
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
    if (r.state === 'dismissed' && c && now - r.stateAt >= T.quietDays * DAY) return { ...r, ...c, ...seen, state: 'new', stateAt: now }
    if ((r.state === 'new' || r.state === 'shown') && c) return { ...r, ...c, ...seen }
    return r
  })
  for (const c of cands) if (!byKey.has(c.key)) out.push({ ...c, id: fnv1a(c.key).slice(0, 6), state: 'new', createdAt: now, stateAt: now, lastSeen: now })
  // Open rows leave when their evidence has gone quiet, or when the evidence is now suppressed
  // (a read-only chain, a tool that asks by design). Settled rows stay as the record.
  const isOpen = (r: Suggestion) => r.state === 'new' || r.state === 'shown'
  const live = out.filter(r => !(isOpen(r) && (suppressed(r.key) || now - (r.lastSeen ?? r.stateAt) > T.staleDays * DAY)))
  // When the queue is full the weakest open rows and the oldest settled rows go first.
  const open = live.filter(r => isOpen(r) || r.state === 'snoozed').sort((a, b) => (b.count ?? 0) - (a.count ?? 0))
  const settled = live.filter(r => !open.includes(r)).sort((a, b) => b.stateAt - a.stateAt)
  return [...open, ...settled].slice(0, T.maxRows)
}

/** At most one note per session: the new row with the most evidence (oldest on a tie), marked shown. */
export const pickNote = (rows: readonly Suggestion[], notedThisSession: boolean, now: number): { rows: Suggestion[]; note: Suggestion | null } => {
  if (notedThisSession) return { rows: [...rows], note: null }
  const next = [...rows].filter(r => r.state === 'new').sort((a, b) => (b.count ?? 0) - (a.count ?? 0) || a.createdAt - b.createdAt)[0]
  if (!next) return { rows: [...rows], note: null }
  const shown: Suggestion = { ...next, state: 'shown', stateAt: now }
  return { rows: rows.map(r => (r.id === next.id ? shown : r)), note: shown }
}

const RANK: Record<SuggestState, number> = { new: 0, shown: 1, snoozed: 2, accepted: 3, dismissed: 4 }
const isOpenState = (s: SuggestState) => s === 'new' || s === 'shown'

/** The rows in a stable order: open first, then by evidence (most first), then oldest. */
export const listed = (rows: readonly Suggestion[]): Suggestion[] =>
  [...rows].sort((a, b) => Number(isOpenState(b.state)) - Number(isOpenState(a.state)) || (b.count ?? 0) - (a.count ?? 0) || RANK[a.state] - RANK[b.state] || a.createdAt - b.createdAt || a.key.localeCompare(b.key))

/** One shape under a group: its prompt row and its run row, side by side. */
export type SubRow = { label: string; asked: number; ran: number; open: number; rows: Suggestion[] }
export type Group = { name: string; asked: number; ran: number; open: number; states: Partial<Record<SuggestState, number>>; subs: SubRow[]; rows: Suggestion[] }

const tally = (rows: readonly Suggestion[]) => ({
  asked: rows.reduce((n, r) => n + (r.kind === 'prompt' && isOpenState(r.state) ? (r.count ?? 0) : 0), 0),
  ran: rows.reduce((n, r) => n + (r.kind === 'command' && isOpenState(r.state) ? (r.count ?? 0) : 0), 0),
  open: rows.filter(r => isOpenState(r.state)).length,
})
const byEvidence = <X extends { asked: number; ran: number; open: number }>(a: X, b: X) =>
  Number(b.open > 0) - Number(a.open > 0) || b.asked - a.asked || b.ran - a.ran

/**
 * The queue rolled up by command type, most-asked first, each group's shapes the same way. A group
 * with nothing open sinks to the bottom. Numbered from 1 in this order; a shape is `<group>.<n>`.
 */
export const grouped = (rows: readonly Suggestion[]): Group[] => {
  const groups = new Map<string, Suggestion[]>()
  for (const r of listed(rows)) {
    const g = groupOf(r.key)
    groups.set(g, [...(groups.get(g) ?? []), r])
  }
  return [...groups.entries()]
    .map(([name, rs]) => {
      const subs = new Map<string, Suggestion[]>()
      for (const r of rs) {
        const label = r.kind === 'prompt' || r.kind === 'allow' || r.kind === 'command' ? subLabel(r.key) : r.title
        subs.set(label, [...(subs.get(label) ?? []), r])
      }
      const states: Partial<Record<SuggestState, number>> = {}
      for (const r of rs) states[r.state] = (states[r.state] ?? 0) + 1
      return {
        name, ...tally(rs), states, rows: rs,
        subs: [...subs.entries()].map(([label, xs]) => ({ label, ...tally(xs), rows: xs })).sort((a, b) => byEvidence(a, b) || a.label.localeCompare(b.label)),
      }
    })
    .sort((a, b) => byEvidence(a, b) || a.name.localeCompare(b.name))
}

/** `3` is a group, `3.2` one shape in it, a six-character id one row; `ref` may also name a group. */
export const resolveRef = (rows: readonly Suggestion[], ref: string): { label: string; rows: Suggestion[] } | null => {
  const gs = grouped(rows)
  const m = /^(\d+)(?:\.(\d+))?$/.exec(ref.trim())
  if (m) {
    const g = gs[Number(m[1]) - 1]
    if (!g) return null
    if (m[2] === undefined) return { label: g.name, rows: g.rows }
    const sub = g.subs[Number(m[2]) - 1]
    return sub ? { label: sub.label, rows: sub.rows } : null
  }
  const byId = rows.find(r => r.id === ref.trim())
  if (byId) return { label: byId.title, rows: [byId] }
  const byName = gs.find(g => g.name.toLowerCase() === ref.trim().toLowerCase() || g.name.toLowerCase().replace(/^\w+: /, '') === ref.trim().toLowerCase())
  return byName ? { label: byName.name, rows: byName.rows } : null
}

/** The line the person copies to NEXT.md when they accept. dash never writes it there. */
export const nextMdLine = (r: Suggestion, now: number): string =>
  `- [ ] ${r.title}: ${r.action} Evidence: ${r.evidence}. (dash ${r.id}, ${new Date(now).toISOString().slice(0, 10)})`

export type SuggestVerb = 'accept' | 'dismiss' | 'snooze'

/** At most this many NEXT.md lines in one accept reply; the rest are counted. */
const ACCEPT_LINES = 10

/**
 * `/dash suggest accept|dismiss|snooze <ref>`: a group (`3`), a shape (`3.2`) or a row id. A group or
 * shape acts on its rows not yet accepted or dismissed (a lone id acts on that row whatever its state).
 */
export const actOn = (rows: readonly Suggestion[], verb: SuggestVerb, ref: string, now: number): { rows: Suggestion[]; text: string } => {
  const hit = resolveRef(rows, ref)
  if (!hit) return { rows: [...rows], text: `No suggestion "${ref}". /dash suggest lists the groups by number; /dash suggest <n> drills in.` }
  const lone = hit.rows.length === 1 && hit.rows[0]!.id === ref.trim()
  return actOnRows(rows, verb, hit.label, hit.rows.map(r => r.id), now, lone, ref)
}

/**
 * The same, on rows named by id: what a pane button carries, so a press acts on the rows it was
 * drawn for even when the numbering moved before the redraw. `lone` acts whatever the state.
 */
export const actOnRows = (rows: readonly Suggestion[], verb: SuggestVerb, label: string, ids: readonly string[], now: number, lone = false, ref = label): { rows: Suggestion[]; text: string } => {
  const named = new Set(ids)
  const targets = rows.filter(r => named.has(r.id) && (lone || r.state === 'new' || r.state === 'shown' || r.state === 'snoozed'))
  if (targets.length === 0) return { rows: [...rows], text: `Nothing open under "${label}".` }
  const state: SuggestState = verb === 'accept' ? 'accepted' : verb === 'dismiss' ? 'dismissed' : 'snoozed'
  const hitIds = new Set(targets.map(r => r.id))
  const out = rows.map(r => (hitIds.has(r.id) ? { ...r, state, stateAt: now, ...(verb === 'snooze' ? { snoozeUntil: now + T.snoozeDays * DAY } : {}) } : r))
  const done = out.filter(r => hitIds.has(r.id))
  const what = done.length === 1 ? done[0]!.title : `${label} (${plural(done.length, 'row')})`
  if (verb === 'accept') {
    const lines = done.slice(0, ACCEPT_LINES).map(r => nextMdLine(r, now))
    const more = done.length > ACCEPT_LINES ? [`(+${done.length - ACCEPT_LINES} more accepted; /dash suggest ${ref} lists them)`] : []
    return { rows: out, text: [`Accepted. Copy ${done.length === 1 ? 'this line' : 'these lines'} to NEXT.md yourself; dash writes nothing there:`, ...lines, ...more].join('\n') }
  }
  if (verb === 'dismiss') return { rows: out, text: `Dismissed: ${what}. Quiet for ${T.quietDays} days; it comes back only with fresh evidence.` }
  return { rows: out, text: `Snoozed for ${T.snoozeDays} days: ${what}.` }
}

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
