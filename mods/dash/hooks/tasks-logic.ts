// dash tasks: pure logic (no $). Background tasks and agents (F3, F3f), the dispatch ledger and
// its cost sidecar (F3e, now D7), and your open PRs (X5, now D12). Ported from foundation-mods.

import { fnv1a } from './lib/util'

export type TaskState = 'running' | 'completed' | 'failed' | 'killed'
export type TaskKind = 'bash' | 'monitor' | 'agent'
export type TaskRecord = {
  id: string
  kind: TaskKind
  label: string
  group: string
  startedAt: number
  endedAt?: number
  state: TaskState
  outputFile?: string
  /** What runs: the command, or the agent's type and description. */
  detail?: string
  /** The Bash timeout the call set, an upper bound on the run. */
  timeoutMs?: number
  /** Normalised key for "the same task", used to learn how long it usually takes. */
  sig?: string
}
export type LedgerRow = {
  unit: string
  task: string
  model: string
  status: string
  surface?: string
  estWall?: string
  dispatchTs?: string
  remoteSha?: string
}
export type LedgerSummary = { runId: string; rows: LedgerRow[]; line: string }

export const TASKS_KEEP_FINISHED_MS = 90_000
export const TASKS_BAND_MAX = 4

export const LEDGER_STATUSES = [
  'dispatched', 'committed', 'landed locally', 'pushed', 'verified',
  'done', 'unverified', 'stalled', 'failed', 'resumed',
] as const

/** Map a <status> word from a task-notification to a task state. */
export function notificationState(status: string): TaskState {
  const s = status.trim().toLowerCase()
  if (s === 'completed' || s === 'complete' || s === 'success' || s === 'done') return 'completed'
  if (s === 'killed' || s === 'stopped' || s === 'cancelled' || s === 'canceled') return 'killed'
  if (s === 'running') return 'running'
  return 'failed'
}

/** Parse a task-notification body: <task-id>…</task-id> and <status>…</status>. */
export function parseTaskNotification(text: string): { id: string; status: TaskState } | undefined {
  const id = /<task-id>\s*([^<\s]+)\s*<\/task-id>/.exec(text)?.[1]
  const status = /<status>\s*([^<]+?)\s*<\/status>/.exec(text)?.[1]
  if (!id) return undefined
  return { id, status: notificationState(status ?? 'completed') }
}

export function addTask(list: TaskRecord[], rec: TaskRecord): TaskRecord[] {
  return [...list.filter(t => t.id !== rec.id), rec].slice(-200)
}

export function settleTask(list: TaskRecord[], id: string, state: TaskState, now: number): TaskRecord[] {
  return list.map(t => (t.id === id && t.state === 'running' ? { ...t, state, endedAt: now } : t))
}

/** Rows the band shows: running ones, plus finished ones younger than 90 s. */
export function visibleTasks(list: TaskRecord[], now: number): TaskRecord[] {
  return list.filter(t => t.state === 'running' || (t.endedAt !== undefined && now - t.endedAt < TASKS_KEEP_FINISHED_MS))
}

export function runningCount(list: TaskRecord[]): number {
  return list.filter(t => t.state === 'running').length
}

/** The one line the task band leads with, for surfaces that cannot draw it: "Tasks: 2 running · run x: 1 done". */
export function tasksHeadline(list: TaskRecord[], ledgerLine: string | null): string {
  const running = runningCount(list)
  const failed = list.filter(t => t.state === 'failed').length
  const parts: string[] = [`${running} running`]
  if (failed) parts.push(`${failed} failed`)
  if (ledgerLine) parts.push(ledgerLine)
  return `Tasks: ${parts.join(' · ')}`
}

/** Group label: 'main' for the main loop, else the agent id. */
export function groupOf(agentId: string | undefined): string {
  return agentId ? agentId : 'main'
}

/** Split a markdown table line into trimmed cells. */
function cells(line: string): string[] {
  const t = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  return t.split('|').map(c => c.trim())
}

/** Parse the first markdown table holding unit_id and status columns. */
export function parseLedgerMarkdown(text: string): LedgerRow[] {
  const lines = text.split(/\r?\n/)
  for (let i = 0; i < lines.length - 1; i++) {
    const line = lines[i] ?? ''
    if (!line.trim().startsWith('|')) continue
    const head = cells(line).map(c => c.replace(/`/g, '').toLowerCase())
    const iUnit = head.indexOf('unit_id')
    const iStatus = head.indexOf('status')
    if (iUnit < 0 || iStatus < 0) continue
    const iModel = head.indexOf('model')
    const iTask = head.indexOf('task')
    const opt = (c: string[], name: string): string | undefined => {
      const k = head.indexOf(name)
      const v = k >= 0 ? (c[k] ?? '').replace(/`/g, '').trim() : ''
      return v && v !== '—' && v !== '-' ? v : undefined
    }
    const rows: LedgerRow[] = []
    for (let j = i + 2; j < lines.length; j++) {
      const l = lines[j] ?? ''
      if (!l.trim().startsWith('|')) break
      const c = cells(l)
      const unit = (c[iUnit] ?? '').replace(/`/g, '')
      if (!unit) continue
      rows.push({
        unit,
        task: iTask >= 0 ? (c[iTask] ?? '') : '',
        model: iModel >= 0 ? (c[iModel] ?? '').replace(/`/g, '') : '',
        status: (c[iStatus] ?? '').replace(/`/g, '').toLowerCase(),
        surface: opt(c, 'surface'),
        estWall: opt(c, 'est_wall'),
        dispatchTs: opt(c, 'dispatch_ts'),
        remoteSha: opt(c, 'remote_sha'),
      })
    }
    return rows
  }
  return []
}

/** Parse a CSV ledger (simple, no quoted commas inside cells). */
export function parseLedgerCsv(text: string): LedgerRow[] {
  const lines = text.split(/\r?\n/).filter(l => l.trim())
  const head = (lines[0] ?? '').split(',').map(c => c.trim().toLowerCase())
  const iUnit = head.indexOf('unit_id')
  const iStatus = head.indexOf('status')
  if (iUnit < 0 || iStatus < 0) return []
  const iModel = head.indexOf('model')
  const iTask = head.indexOf('task')
  return lines.slice(1).map(l => {
    const c = l.split(',').map(x => x.trim())
    return {
      unit: c[iUnit] ?? '',
      task: iTask >= 0 ? (c[iTask] ?? '') : '',
      model: iModel >= 0 ? (c[iModel] ?? '') : '',
      status: (c[iStatus] ?? '').toLowerCase(),
    }
  }).filter(r => r.unit)
}

export function parseLedger(path: string, text: string): LedgerRow[] {
  return path.toLowerCase().endsWith('.csv') ? parseLedgerCsv(text) : parseLedgerMarkdown(text)
}

/** The run id: the directory name above ledger.md under .dispatch/runs/<id>/. */
export function runIdFromPath(path: string): string {
  const m = /\.dispatch\/runs\/([^/]+)\/ledger\.(md|csv)$/.exec(path.replace(/\\/g, '/'))
  if (m?.[1]) return m[1]
  const parts = path.replace(/\\/g, '/').split('/')
  return parts[parts.length - 2] ?? 'ledger'
}

/** A status cell's state word: a known status it opens with, else the text before a note ("complete — job 7a" → "complete"). */
export function statusWord(status: string): string {
  const s = status.trim()
  const known = [...LEDGER_STATUSES].sort((a, b) => b.length - a.length).find(k => s === k || s.startsWith(`${k} `))
  if (known) return known
  return s.split(/\s+[—–(:;,-]\s*|[(:;,]/)[0]?.trim() || 'unknown'
}

export function summariseLedger(runId: string, rows: LedgerRow[]): LedgerSummary {
  const counts: Record<string, number> = {}
  for (const r of rows) { const w = statusWord(r.status); counts[w] = (counts[w] ?? 0) + 1 }
  const order = [...LEDGER_STATUSES, ...Object.keys(counts).filter(k => !(LEDGER_STATUSES as readonly string[]).includes(k))]
  const parts = order.filter(s => counts[s]).map(s => `${counts[s]} ${s}`)
  const remote = rows.filter(isDoneWithRemote).length
  if (remote) parts.push(`${remote} done with remote_sha`)
  return { runId, rows, line: `run ${runId}: ${parts.length ? parts.join(' · ') : 'no rows'}` }
}

/** Find the ledger row whose unit_id appears as a whole word in any of the texts. */
export function matchLedgerRow(rows: LedgerRow[], texts: string[]): LedgerRow | undefined {
  const hay = texts.filter(Boolean).join('\n')
  // Longest ids first so U12 wins over U1.
  const sorted = [...rows].sort((a, b) => b.unit.length - a.unit.length)
  return sorted.find(r => new RegExp(`(^|[^A-Za-z0-9_])${r.unit.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^A-Za-z0-9_]|$)`).test(hay))
}

export const DISPATCH_WAVE_CAP = 6
const CLOSED = new Set(['verified', 'done', 'failed'])

/** Units a row counts for: the last x<N> token on its surface cell; missing or malformed = 1. */
export function unitWeight(surface: string | undefined): number {
  const all = [...(surface ?? '').matchAll(/\bx(\w+)\b/g)]
  const last = all[all.length - 1]?.[1]
  const n = last !== undefined && /^\d+$/.test(last) ? Number(last) : 1
  return n > 0 ? n : 1
}

/** Open units against the 6-unit wave cap. */
export function openUnits(rows: LedgerRow[]): { open: number; cap: number; over: boolean; line: string } {
  const open = rows.filter(r => !CLOSED.has(r.status)).reduce((s, r) => s + unitWeight(r.surface), 0)
  return { open, cap: DISPATCH_WAVE_CAP, over: open > DISPATCH_WAVE_CAP, line: `${open} of ${DISPATCH_WAVE_CAP} units open${open > DISPATCH_WAVE_CAP ? ' (over cap)' : ''}` }
}

export function isDoneWithRemote(r: LedgerRow): boolean {
  return (r.status === 'done' || r.status === 'verified') && !!r.remoteSha
}

/** Distinct display word for a row: keeps 'landed locally' and 'unverified' apart from closed. */
export function rowStateWord(r: LedgerRow): string {
  if (isDoneWithRemote(r)) return `${r.status} (remote ${r.remoteSha!.slice(0, 7)})`
  return r.status || 'unknown'
}

/** "30m", "1h", "1h30m", "45 min", "90" (minutes) -> ms. */
export function parseDurationMs(text: string | undefined): number | undefined {
  if (!text) return undefined
  const t = text.trim().toLowerCase()
  if (/^\d+(\.\d+)?$/.test(t)) return Number(t) * 60_000
  let ms = 0, hit = false
  for (const m of t.matchAll(/(\d+(?:\.\d+)?)\s*(h|hr|hours?|m|min|mins|minutes?|s|sec|seconds?)\b/g)) {
    hit = true
    const v = Number(m[1]); const u = m[2] ?? 'm'
    ms += u.startsWith('h') ? v * 3600_000 : u.startsWith('s') ? v * 1000 : v * 60_000
  }
  return hit ? ms : undefined
}

/** Ledger timestamp "YYYY-MM-DD HH:MMZ" -> epoch ms. */
export function parseLedgerTs(text: string | undefined): number | undefined {
  const m = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})Z$/.exec((text ?? '').trim())
  if (!m) return undefined
  const d = Date.parse(`${m[1]}T${m[2]}:00Z`)
  return Number.isNaN(d) ? undefined : d
}

/** An open unit whose elapsed time since dispatch is over 2x its est_wall. */
export function needsOwner(r: LedgerRow, now: number): boolean {
  if (CLOSED.has(r.status)) return false
  const est = parseDurationMs(r.estWall), start = parseLedgerTs(r.dispatchTs)
  return est !== undefined && est > 0 && start !== undefined && now - start > 2 * est
}

export const USAGE_WINDOWS_MAX_AGE_MS = 15 * 60_000

/** Launch-throttle line during an active run: absent or stale meter file = "not enforced". */
export function throttleLine(runActive: boolean, meterMtime: number | undefined, now: number): string | undefined {
  if (!runActive) return undefined
  if (meterMtime === undefined) return 'launch throttle not enforced (usage-windows.json missing)'
  if (now - meterMtime > USAGE_WINDOWS_MAX_AGE_MS) return 'launch throttle not enforced (usage-windows.json stale)'
  return undefined
}

// ---------- D7: is a dispatch run active here ----------

export const TIERS_RUN_MAX_AGE_MS = 12 * 60 * 60 * 1000

/**
 * Read the flag file's timestamp. UNVERIFIED schema: accepts `ts` as epoch seconds,
 * epoch milliseconds or an ISO string (the dispatch gate's own schema was not read).
 */
export function flagTimestamp(json: string): number | undefined {
  let v: unknown
  try { v = JSON.parse(json) } catch { return undefined }
  if (!v || typeof v !== 'object') return undefined
  const ts = (v as Record<string, unknown>).ts
  if (typeof ts === 'number' && Number.isFinite(ts)) return ts < 1e12 ? ts * 1000 : ts
  if (typeof ts === 'string') {
    const n = Number(ts)
    if (Number.isFinite(n) && ts.trim() !== '') return n < 1e12 ? n * 1000 : n
    const d = Date.parse(ts)
    return Number.isNaN(d) ? undefined : d
  }
  return undefined
}

export function isRunActive(json: string | undefined, now: number): boolean {
  if (json === undefined) return false
  const ts = flagTimestamp(json)
  return ts !== undefined && now - ts >= 0 && now - ts < TIERS_RUN_MAX_AGE_MS
}

/** Ledger rows marked done with no remote sha the origin holds. */
export const reconcileFlags = (rows: Array<{ unit: string; status: string; remoteSha?: string }>, originHas: (sha: string) => boolean): string[] =>
  rows
    .filter(r => /^(done|verified|pushed)$/i.test(r.status.trim()))
    .filter(r => !r.remoteSha || !originHas(r.remoteSha))
    .map(r => r.unit)

// ---------- D12 (was X5): PR state ----------

export type PrRow = { number: number; title: string; state: string; checks: string; review: string; mergeable: string }

export const parsePrList = (json: string): PrRow[] => {
  try {
    const raw = JSON.parse(json) as Array<Record<string, unknown>>
    return raw.map(r => {
      const rollup = (r.statusCheckRollup as Array<{ conclusion?: string; state?: string }> | undefined) ?? []
      const states = rollup.map(c => (c.conclusion ?? c.state ?? '').toUpperCase())
      const checks = states.length === 0 ? 'no checks' : states.some(s => /FAIL|ERROR|CANCELLED|TIMED_OUT/.test(s)) ? 'red' : states.every(s => /SUCCESS|NEUTRAL|SKIPPED/.test(s)) ? 'green' : 'pending'
      return {
        number: Number(r.number),
        title: String(r.title ?? ''),
        state: String(r.state ?? ''),
        checks,
        review: String(r.reviewDecision ?? '') || 'no review',
        mergeable: String(r.mergeStateStatus ?? ''),
      }
    })
  } catch {
    return []
  }
}

/** D12 refreshes after a command that can change a PR: a push, or a gh pr action. */
export const changesPrs = (command: string): boolean =>
  /\bgit\b[^;&|\n]*\bpush\b/.test(command) || /\bgh\s+pr\s+(create|merge|ready|close|reopen|edit|review)\b/.test(command)

export const prLine = (rows: PrRow[]): string =>
  rows.length === 0 ? 'No open PRs of yours here.' : rows.map(r => `#${r.number} ${r.checks}, ${r.review.toLowerCase().replace(/_/g, ' ')}${r.mergeable === 'DIRTY' ? ', conflict' : ''}`).join(' · ')

export const prChanges = (before: PrRow[], after: PrRow[]): string[] =>
  after.flatMap(a => {
    const b = before.find(x => x.number === a.number)
    if (!b) return []
    const out: string[] = []
    if (b.checks !== a.checks) out.push(`#${a.number} checks ${b.checks} → ${a.checks}`)
    if (b.review !== a.review) out.push(`#${a.number} review ${a.review.toLowerCase().replace(/_/g, ' ')}`)
    return out
  })

// ---------- F3f: background task status ----------

/** "the same task" for estimates: kind plus a hash of the command with numbers, paths and quotes
 * flattened. Only the hash is kept, so no command or agent text is ever stored (counts only, never text). */
export const taskSignature = (kind: string, text: string): string =>
  `${kind}:${fnv1a(text.toLowerCase().replace(/(["']).*?\1/g, 'S').replace(/\d+/g, 'N').replace(/[\w.-]*[\\/][\w./\\-]*/g, 'P').replace(/\s+/g, ' ').trim())}`

const SIG_RE = /^[a-z]+:[0-9a-f]{8}$/
const MAX_TASK_KEYS = 200

/** A ledger `est_wall` such as "20m", "1h30m", "90s" or "45" (minutes), in ms. */
export const parseEstWall = (s: string | undefined): number | null => {
  if (!s) return null
  const t = s.trim().toLowerCase()
  if (/^\d+$/.test(t)) return Number(t) * 60_000
  let ms = 0
  let hit = false
  for (const m of t.matchAll(/(\d+(?:\.\d+)?)\s*(hours?|hr|h|minutes?|min|m|seconds?|sec|s)(?![a-z])/g)) {
    hit = true
    const n = Number(m[1])
    ms += m[2]!.startsWith('h') ? n * 3600_000 : m[2]!.startsWith('m') ? n * 60_000 : n * 1000
  }
  return hit ? ms : null
}

export type TaskHistory = Record<string, number[]>

/** Up to 20 durations per task and 200 tasks; the task just run moves to the end, the oldest drops. */
export const recordDuration = (h: TaskHistory, sig: string, ms: number): TaskHistory => {
  const runs = [...(h[sig] ?? []), ms].slice(-20)
  const keys = Object.keys(h).filter(k => k !== sig).slice(-(MAX_TASK_KEYS - 1))
  const out: TaskHistory = {}
  for (const k of keys) out[k] = h[k]!
  out[sig] = runs
  return out
}

/** Read-side guard: keep only hash keys and numeric durations, so text stored by an older build is dropped. */
export const sanitizeTaskHistory = (raw: unknown): TaskHistory => {
  const out: TaskHistory = {}
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return out
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (!SIG_RE.test(k) || !Array.isArray(v)) continue
    const runs = v.filter((n): n is number => typeof n === 'number' && Number.isFinite(n)).slice(-20)
    if (runs.length) out[k] = runs
  }
  const keys = Object.keys(out)
  for (const k of keys.slice(0, Math.max(0, keys.length - MAX_TASK_KEYS))) delete out[k]
  return out
}

export type Estimate = { ms: number; source: 'ledger' | 'history' | 'timeout' } | null

/** Ledger row first, then the median of past runs of the same task, then the call's own timeout as a ceiling. */
export const estimateFor = (sig: string | undefined, history: TaskHistory, ledgerEst: number | null, timeoutMs: number | undefined): Estimate => {
  if (ledgerEst) return { ms: ledgerEst, source: 'ledger' }
  const past = sig ? history[sig] ?? [] : []
  if (past.length >= 2) {
    const sorted = [...past].sort((a, b) => a - b)
    return { ms: sorted[Math.floor(sorted.length / 2)]!, source: 'history' }
  }
  if (timeoutMs) return { ms: timeoutMs, source: 'timeout' }
  return null
}

const dur = (ms: number): string => {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s}s`
  const m = Math.round(s / 60)
  return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}m`
}

export type Progress = { lastLine: string | null; idleMs: number | null; bytes: number | null }

/** One task as a few plain lines: what, who, how long, estimate, progress. */
export const taskStatusLines = (
  t: { id: string; kind: string; label: string; group: string; startedAt: number; endedAt?: number; state: string; detail?: string },
  now: number, est: Estimate, p: Progress | null,
): string[] => {
  const ran = (t.endedAt ?? now) - t.startedAt
  const head = `${t.state === 'running' ? 'RUNNING' : t.state.toUpperCase()} ${t.kind} · ${t.label}`
  const lines = [head]
  if (t.detail && t.detail !== t.label) lines.push(`  what: ${t.detail.replace(/\s+/g, ' ').slice(0, 140)}`)
  lines.push(`  started by ${t.group === 'main' ? 'this session' : 'a subagent'} at ${new Date(t.startedAt).toISOString().slice(11, 16)} UTC · ${t.state === 'running' ? 'running for' : 'ran'} ${dur(ran)}`)
  if (t.state === 'running') {
    if (!est) lines.push('  estimate: none yet (no ledger row, timeout or earlier run of this task)')
    else {
      const left = est.ms - ran
      const how = est.source === 'ledger' ? 'from its ledger row' : est.source === 'history' ? 'from earlier runs' : 'its timeout, an upper bound'
      lines.push(left >= 0 ? `  estimate: about ${dur(left)} left of ${dur(est.ms)} (${how})` : `  estimate: ${dur(-left)} over ${dur(est.ms)} (${how})`)
    }
    if (p?.idleMs !== null && p?.idleMs !== undefined && p.idleMs > 5 * 60_000) lines.push(`  no new output for ${dur(p.idleMs)}: stalled, or quiet by design`)
  }
  if (p?.lastLine) lines.push(`  last output: ${p.lastLine.slice(0, 140)}`)
  lines.push(`  id: ${t.id}`)
  return lines
}

export const lastLineOf = (text: string): string | null => {
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  return lines.length ? lines[lines.length - 1]! : null
}
