// dash collector: pure logic (no $). What one event row may hold, how a command or a permission
// prompt becomes a shape, misroute detection, the 30-day retention and the roll-up into feed.json.
// Owner 2026-10-08: COUNTS only. No prompt or response text, no command text, no file path: names
// of skills, hashes and shapes. Every row passes `safeEvent` before it is kept.
import { parseShell, progName } from './lib/shell'
import { fnv1a } from './lib/util'

export const DAY = 86_400_000
export const KEEP_DAYS = 30
export const MAX_EVENTS = 20_000
/** A different skill this soon after an automatic fire marks the first one as a likely misroute. */
export const SWITCH_WINDOW_MS = 120_000
/** A reverted edit this soon after an automatic fire marks that skill as a likely misroute. */
export const REVERT_WINDOW_MS = 10 * 60_000
/** A fresh meter row at most this often (the status line moves every response). */
export const METER_EVERY_MS = 5 * 60_000

export type Via = 'slash' | 'auto'

/** One row of events.jsonl. `t` epoch ms, `s` an 8-hex hash of the session id. */
export type DashEvent =
  | { t: number; s: string; k: 'session' }
  | { t: number; s: string; k: 'listed'; skills: string[] }
  | { t: number; s: string; k: 'skill'; skill: string; via: Via }
  | { t: number; s: string; k: 'skill_fail'; skill: string }
  | { t: number; s: string; k: 'misroute'; skill: string; why: 'switch' | 'revert' }
  | { t: number; s: string; k: 'turn'; skill: string | null; input: number; output: number; cacheRead: number; cacheWrite: number; cost: number | null }
  | { t: number; s: string; k: 'meter'; five: number | null; week: number | null; weekReset: number | null; ctx: number | null }
  | { t: number; s: string; k: 'ctx80' }
  | { t: number; s: string; k: 'cmd'; shape: string }
  | { t: number; s: string; k: 'perm'; shape: string }

export type EventKind = DashEvent['k']

// ---------- what a row may hold ----------

const SKILL_RE = /^[A-Za-z0-9][\w:.-]{0,79}$/
const SHAPE_RE = /^[a-z0-9][\w.+-]*( (-{1,2}[A-Za-z][\w-]*|[a-z][\w.-]*|\*\.[a-z0-9]{1,8}|;))*$/
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) && v >= 0 ? Math.round(v) : 0)
const numOrNull = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? Math.round(v * 10) / 10 : null)

/** A skill's name as a row keeps it: the name itself when it looks like one, else a hash. */
export const skillKey = (name: string): string => (SKILL_RE.test(name) ? name : `skill-${fnv1a(name)}`)

/** A shape as a row keeps it, or null: only program names, subcommand words, flag names and `*.ext`. */
export const safeShape = (shape: string): string | null => (shape.length <= 120 && SHAPE_RE.test(shape) ? shape : null)

/**
 * The one door every row passes: known kinds and fields only, names checked, shapes checked,
 * numbers numbers. Anything else is dropped (null), so no text can reach the file.
 */
export const safeEvent = (e: DashEvent): DashEvent | null => {
  const base = { t: num(e.t), s: /^[0-9a-f]{8}$/.test(e.s) ? e.s : fnv1a(String(e.s)) }
  switch (e.k) {
    case 'session':
    case 'ctx80':
      return { ...base, k: e.k }
    case 'listed':
      return { ...base, k: 'listed', skills: [...new Set(e.skills.map(skillKey))].slice(0, 300) }
    case 'skill':
      return { ...base, k: 'skill', skill: skillKey(e.skill), via: e.via === 'slash' ? 'slash' : 'auto' }
    case 'skill_fail':
      return { ...base, k: 'skill_fail', skill: skillKey(e.skill) }
    case 'misroute':
      return { ...base, k: 'misroute', skill: skillKey(e.skill), why: e.why === 'revert' ? 'revert' : 'switch' }
    case 'turn':
      return { ...base, k: 'turn', skill: e.skill === null ? null : skillKey(e.skill), input: num(e.input), output: num(e.output), cacheRead: num(e.cacheRead), cacheWrite: num(e.cacheWrite), cost: e.cost === null ? null : Math.round(Math.max(0, e.cost) * 1e6) / 1e6 }
    case 'meter':
      return { ...base, k: 'meter', five: numOrNull(e.five), week: numOrNull(e.week), weekReset: e.weekReset === null ? null : num(e.weekReset), ctx: numOrNull(e.ctx) }
    case 'cmd':
    case 'perm': {
      const shape = safeShape(e.shape)
      return shape ? { ...base, k: e.k, shape } : null
    }
    default:
      return null
  }
}

export const sessionKey = (sessionId: string): string => fnv1a(`dash:${sessionId}`)

/** `/dash purge`: the remove command for the dash records folder, or null. Only a path that ends in
 * `.claude/revenantworks/dash` passes, and on Windows none with a character cmd re-parses (& ^ % | < > "). */
export const purgeArgv = (isWin: boolean, dir: string): string[] | null => {
  const p = dir.replace(/\\/g, '/')
  if (!/^.+\/\.claude\/revenantworks\/dash$/.test(p) || /(^|\/)\.\.(\/|$)/.test(p) || /[\r\n\0]/.test(p)) return null
  if (isWin) return /[&^%|<>"]/.test(p) ? null : ['cmd', '/c', 'rmdir', '/s', '/q', p.replace(/\//g, '\\')]
  return ['rm', '-rf', p]
}

// ---------- shapes: a command without its text ----------

/** Programs whose second word picks what runs (`git status`, `npm test`). */
const SUBCOMMANDS = new Set([
  'git', 'gh', 'npm', 'pnpm', 'yarn', 'bun', 'npx', 'docker', 'kubectl', 'cargo', 'go', 'pip', 'pip3', 'uv', 'poetry',
  'dotnet', 'az', 'gcloud', 'aws', 'terraform', 'claude', 'brew', 'apt', 'apt-get', 'systemctl', 'make', 'just', 'deno', 'conda', 'helm',
])
/** Interpreters whose first file argument says what runs; only its file name's suffix is kept. */
const INTERPRETERS = new Set(['python', 'python3', 'py', 'node', 'bash', 'sh', 'zsh', 'pwsh', 'powershell', 'ruby', 'perl', 'tsx', 'ts-node'])

/** A flag's name: `--name` up to any `=value`; a short flag only as `-x` to `-xyz`, since a longer
 * single-dash word can carry its value attached (`-pSECRET`). */
const flagName = (w: string): string | null => {
  const long = /^(--[A-Za-z][\w-]{0,28})(=.*)?$/.exec(w)
  if (long) return long[1]!
  return /^-[A-Za-z]{1,3}$/.test(w) ? w : null
}

/**
 * One command's shape: the program, its subcommand word for the programs that have one, a script's
 * suffix for an interpreter (`python *.py`), and its flag names sorted, never their values. Every
 * other word (paths, strings, ids) is dropped.
 */
export const commandShape = (command: string, shell: 'sh' | 'ps' = 'sh'): string | null => {
  const parsed = parseShell(command, shell)
  if (parsed.indeterminate || parsed.commands.length === 0) return null
  const parts: string[] = []
  for (const c of parsed.commands.slice(0, 3)) {
    const prog = progName(c.argv[0] ?? '').replace(/[^\w.+-]/g, '')
    if (!/^[a-z0-9]/.test(prog)) return null
    const words = [prog]
    const rest = c.argv.slice(1)
    const firstWord = rest.find(w => !w.startsWith('-'))
    if (SUBCOMMANDS.has(prog) && firstWord && /^[a-z][\w-]{0,30}$/.test(firstWord)) words.push(firstWord)
    if (INTERPRETERS.has(prog)) {
      if (rest[0] === '-m' && rest[1] && /^[a-z][\w.]{0,40}$/.test(rest[1])) words.push('-m', rest[1])
      else {
        const script = rest.find(w => !w.startsWith('-'))
        const ext = script ? /\.([a-z0-9]{1,8})$/i.exec(script)?.[1]?.toLowerCase() : undefined
        if (ext) words.push(`*.${ext}`)
      }
    }
    const flags = [...new Set(rest.map(flagName).filter((x): x is string => x !== null))].sort().slice(0, 6)
    words.push(...flags.filter(f => !words.includes(f)))
    parts.push(words.join(' '))
  }
  return safeShape(parts.join(' ; '))
}

/** A permission prompt's shape: the shell command's shape, or the tool and a file's suffix. */
export const permissionShape = (tool: string, input: Record<string, unknown> | undefined): string | null => {
  const t = tool.toLowerCase().replace(/[^\w.-]/g, '_').slice(0, 60)
  const command = typeof input?.command === 'string' ? input.command : null
  if ((tool === 'Bash' || tool === 'PowerShell') && command) {
    const shape = commandShape(command, tool === 'Bash' ? 'sh' : 'ps')
    return shape ? safeShape(`${t} ${shape}`.slice(0, 120)) : null
  }
  const path = typeof input?.file_path === 'string' ? input.file_path : typeof input?.notebook_path === 'string' ? input.notebook_path : null
  const ext = path ? /\.([a-z0-9]{1,8})$/i.exec(path)?.[1]?.toLowerCase() : undefined
  return safeShape(ext ? `${t} *.${ext}` : t)
}

/** Commands too ordinary to suggest anything about. */
export const TRIVIAL_SHAPES = new Set(['ls', 'cd', 'cat', 'pwd', 'echo', 'head', 'tail', 'grep', 'rg', 'find', 'wc', 'true', 'sleep', 'git status', 'git diff', 'git log', 'which', 'type'])

// ---------- misroutes ----------

export type MisrouteState = {
  last: { skill: string; via: Via; t: number; flagged: boolean } | null
  /** Recent edits by hashes only: file, the text replaced and the text written. */
  edits: Array<{ file: string; from: string; to: string; t: number }>
}

export const emptyMisroute = (): MisrouteState => ({ last: null, edits: [] })

/** A skill fired. A different skill this soon after an automatic fire flags the first one. */
export const onSkillFire = (st: MisrouteState, skill: string, via: Via, t: number): { st: MisrouteState; misroute: string | null } => {
  const prev = st.last
  const misroute = prev && !prev.flagged && prev.via === 'auto' && prev.skill !== skill && t - prev.t >= 0 && t - prev.t <= SWITCH_WINDOW_MS ? prev.skill : null
  return { st: { ...st, last: { skill, via, t, flagged: false } }, misroute }
}

const flagRevert = (st: MisrouteState, t: number): { st: MisrouteState; misroute: string | null } => {
  const prev = st.last
  if (prev && !prev.flagged && prev.via === 'auto' && t - prev.t >= 0 && t - prev.t <= REVERT_WINDOW_MS) {
    return { st: { ...st, last: { ...prev, flagged: true } }, misroute: prev.skill }
  }
  return { st, misroute: null }
}

/** An Edit (hashes of file, old and new text). One that undoes an earlier edit is a revert. */
export const onEdit = (st: MisrouteState, file: string, from: string, to: string, t: number): { st: MisrouteState; misroute: string | null } => {
  const undoes = st.edits.some(x => x.file === file && x.from === to && x.to === from)
  const edits = [...st.edits, { file, from, to, t }].slice(-30)
  return undoes ? flagRevert({ ...st, edits }, t) : { st: { ...st, edits }, misroute: null }
}

/** A shell command that throws work away (`git checkout -- x`, `git restore`, `git reset --hard`, `git revert`). */
export const isRevertCommand = (command: string): boolean => {
  const parsed = parseShell(command, 'sh')
  return parsed.commands.some(c => {
    if (c.prog !== 'git') return false
    const sub = c.argv.find((w, i) => i > 0 && !w.startsWith('-')) ?? ''
    return sub === 'restore' || sub === 'revert' || (sub === 'checkout' && c.argv.includes('--')) || (sub === 'reset' && c.argv.includes('--hard'))
  })
}

export const onRevertCommand = (st: MisrouteState, t: number): { st: MisrouteState; misroute: string | null } => flagRevert(st, t)

// ---------- the file: parse, prune ----------

export const parseEvents = (text: string | null): DashEvent[] => {
  if (!text) return []
  const out: DashEvent[] = []
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    try {
      const e = safeEvent(JSON.parse(line) as DashEvent)
      if (e) out.push(e)
    } catch {
      // A torn line (a crash mid-write) is skipped.
    }
  }
  return out
}

export const serializeEvents = (events: readonly DashEvent[]): string =>
  events.map(e => safeEvent(e)).filter((e): e is DashEvent => e !== null).map(e => JSON.stringify(e)).join('\n') + (events.length ? '\n' : '')

/** Keeps the last 30 days, at most MAX_EVENTS rows. */
export const pruneEvents = (events: readonly DashEvent[], now: number): DashEvent[] =>
  events.filter(e => now - e.t <= KEEP_DAYS * DAY).slice(-MAX_EVENTS)

// ---------- gatewarden's event log, counted ----------

export type GatewardenCounts = { total7: number; byMode: Record<string, number>; byOutcome: Record<string, number>; topRules: Array<{ rule: string; n: number }> } | null

/** Counts the last 7 days of ~/.claude/gatewarden/events.jsonl: by mode, by outcome, top rules. */
export const gatewardenCounts = (text: string | null, now: number): GatewardenCounts => {
  if (text === null) return null
  const byMode: Record<string, number> = {}
  const byOutcome: Record<string, number> = {}
  const byRule: Record<string, number> = {}
  let total7 = 0
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    let r: Record<string, unknown>
    try {
      r = JSON.parse(line) as Record<string, unknown>
    } catch {
      continue
    }
    const at = typeof r.at === 'number' ? (r.at > 1e12 ? r.at : r.at * 1000) : NaN
    if (!Number.isFinite(at) || now - at > 7 * DAY) continue
    total7 += 1
    const word = (v: unknown) => (typeof v === 'string' && /^[\w.-]{1,60}$/.test(v) ? v : 'other')
    byMode[word(r.mode)] = (byMode[word(r.mode)] ?? 0) + 1
    byOutcome[word(r.outcome)] = (byOutcome[word(r.outcome)] ?? 0) + 1
    byRule[word(r.rule)] = (byRule[word(r.rule)] ?? 0) + 1
  }
  const topRules = Object.entries(byRule).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 5).map(([rule, n]) => ({ rule, n }))
  return { total7, byMode, byOutcome, topRules }
}

// ---------- the roll-up: feed.json ----------

export type SkillRow = {
  name: string
  listed: boolean
  /** When the collector first saw it listed (null: never listed, only fired). */
  firstListed: number | null
  fires7: number
  fires30: number
  slash30: number
  auto30: number
  failures30: number
  misroutes30: number
  tokens7: number
  cost7: number | null
  lastFired: number | null
}

export type Meters = { at: number; five: number | null; week: number | null; weekReset: number | null; ctx: number | null; pace: number | null; gap: number | null; cacheHit: number | null; stale: boolean } | null

export type Health = {
  plugins: Record<string, { loaded: boolean; at: number | null; version: string | null; caught: number }>
  drift: Array<{ hook: string; state: 'same' | 'differs' | 'not installed' }>
  gatewarden: GatewardenCounts
  pinsChanged: number
}

export type Feed = {
  version: 1
  generatedAt: number
  recording: boolean
  sessions7: number
  tokens7: number
  cost7: number | null
  ctx80Days7: number
  skills: SkillRow[]
  meters: Meters
  health: Health
  suggestionsNew: number
}

export const emptyHealth = (): Health => ({ plugins: {}, drift: [], gatewarden: null, pinsChanged: 0 })

/** PACE = 95 x the fraction of the 7-day window gone (pacewright); gap = weekly minus PACE. */
export const paceOf = (week: number, resetMs: number, now: number): { pace: number; gap: number } => {
  const fraction = Math.min(1, Math.max(0, (now - (resetMs - 7 * DAY)) / (7 * DAY)))
  const pace = Math.round(95 * fraction * 10) / 10
  return { pace, gap: Math.round((week - pace) * 10) / 10 }
}

const tokensOf = (e: Extract<DashEvent, { k: 'turn' }>): number => e.input + e.output + e.cacheRead + e.cacheWrite

/** Folds the events into the feed: per-skill counts, meters, totals. Pure; `now` decides the windows. */
export const rollup = (events: readonly DashEvent[], args: { now: number; recording: boolean; health?: Health; suggestionsNew?: number }): Feed => {
  const { now } = args
  const in7 = (t: number) => now - t <= 7 * DAY
  const in30 = (t: number) => now - t <= 30 * DAY
  const rows = new Map<string, SkillRow>()
  const row = (name: string): SkillRow => {
    let r = rows.get(name)
    if (!r) {
      r = { name, listed: false, firstListed: null, fires7: 0, fires30: 0, slash30: 0, auto30: 0, failures30: 0, misroutes30: 0, tokens7: 0, cost7: null, lastFired: null }
      rows.set(name, r)
    }
    return r
  }
  let lastListed: { t: number; skills: string[] } | null = null
  const sessions = new Set<string>()
  let tokens7 = 0
  let cost7: number | null = null
  const ctx80 = new Map<string, number>()
  let meter: Extract<DashEvent, { k: 'meter' }> | null = null
  let lastTurn: Extract<DashEvent, { k: 'turn' }> | null = null
  for (const e of events) {
    if (in7(e.t)) sessions.add(e.s)
    switch (e.k) {
      case 'listed':
        for (const s of e.skills) {
          const r = row(s)
          r.firstListed = r.firstListed === null ? e.t : Math.min(r.firstListed, e.t)
        }
        if (!lastListed || e.t >= lastListed.t) lastListed = { t: e.t, skills: e.skills }
        break
      case 'skill': {
        const r = row(e.skill)
        r.lastFired = Math.max(r.lastFired ?? 0, e.t)
        if (in7(e.t)) r.fires7 += 1
        if (in30(e.t)) {
          r.fires30 += 1
          if (e.via === 'slash') r.slash30 += 1
          else r.auto30 += 1
        }
        break
      }
      case 'skill_fail':
        if (in30(e.t)) row(e.skill).failures30 += 1
        break
      case 'misroute':
        if (in30(e.t)) row(e.skill).misroutes30 += 1
        break
      case 'turn':
        lastTurn = e
        if (in7(e.t)) {
          tokens7 += tokensOf(e)
          if (e.cost !== null) cost7 = (cost7 ?? 0) + e.cost
          if (e.skill) {
            const r = row(e.skill)
            r.tokens7 += tokensOf(e)
            if (e.cost !== null) r.cost7 = (r.cost7 ?? 0) + e.cost
          }
        }
        break
      case 'meter':
        if (!meter || e.t >= meter.t) meter = e
        break
      case 'ctx80':
        if (in7(e.t)) {
          const day = new Date(e.t).toISOString().slice(0, 10)
          ctx80.set(day, (ctx80.get(day) ?? 0) + 1)
        }
        break
      default:
        break
    }
  }
  if (lastListed) for (const s of lastListed.skills) row(s).listed = true
  const turnAll = lastTurn ? lastTurn.input + lastTurn.cacheRead + lastTurn.cacheWrite : 0
  const pace = meter && meter.week !== null && meter.weekReset !== null ? paceOf(meter.week, meter.weekReset, now) : null
  const meters: Meters = meter
    ? {
        at: meter.t, five: meter.five, week: meter.week, weekReset: meter.weekReset, ctx: meter.ctx,
        pace: pace?.pace ?? null, gap: pace?.gap ?? null,
        cacheHit: lastTurn && turnAll > 0 ? Math.round((lastTurn.cacheRead / turnAll) * 1000) / 1000 : null,
        stale: now - meter.t > 15 * 60_000,
      }
    : null
  const skills = [...rows.values()].sort((a, b) => b.fires30 - a.fires30 || b.tokens7 - a.tokens7 || a.name.localeCompare(b.name))
  return {
    version: 1,
    generatedAt: now,
    recording: args.recording,
    sessions7: sessions.size,
    tokens7,
    cost7: cost7 === null ? null : Math.round(cost7 * 100) / 100,
    ctx80Days7: [...ctx80.values()].filter(n => n >= 2).length,
    skills,
    meters,
    health: args.health ?? emptyHealth(),
    suggestionsNew: args.suggestionsNew ?? 0,
  }
}

/** The mobile snapshot: the feed's counts with every name that could be a path or a host dropped. */
export const publishSnapshot = (feed: Feed): Record<string, unknown> => ({
  kind: 'revenantworks-dash-snapshot',
  version: 1,
  takenAt: new Date(feed.generatedAt).toISOString(),
  note: 'A rolled-up snapshot, not live. Counts only: no prompts, commands, paths or secrets.',
  sessions7: feed.sessions7,
  tokens7: feed.tokens7,
  cost7: feed.cost7,
  meters: feed.meters,
  skills: feed.skills.slice(0, 40).map(s => ({ name: s.name, listed: s.listed, fires7: s.fires7, fires30: s.fires30, slash30: s.slash30, auto30: s.auto30, failures30: s.failures30, misroutes30: s.misroutes30, tokens7: s.tokens7, cost7: s.cost7 })),
  health: {
    plugins: Object.fromEntries(Object.entries(feed.health.plugins).map(([k, v]) => [k, { loaded: v.loaded, caught: v.caught }])),
    driftCount: feed.health.drift.filter(d => d.state !== 'same').length,
    gatewarden: feed.health.gatewarden ? { total7: feed.health.gatewarden.total7, byMode: feed.health.gatewarden.byMode, byOutcome: feed.health.gatewarden.byOutcome } : null,
  },
  suggestionsNew: feed.suggestionsNew,
})
