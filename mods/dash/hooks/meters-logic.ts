// dash meters: pure logic (no $). The status-line segment, the meter file pacewright reads, and
// the fallback reading where no measure event arrives (Remote Control, the VS Code chat panel).
import { paceOf } from './collector-logic'

export const STALE_MS = 15 * 60_000

export type Live = {
  at: number
  five: number | null
  week: number | null
  weekResetMs: number | null
  ctx: number | null
  cacheHit: number | null
  costUsd: number | null
  fromFile: boolean
}

/** pacewright's PACE (re-exported for tests that pin the formula). */
export const pacewrightPace = (weeklyPct: number, resetsAtMs: number, now: number): { weekly: number; pace: number; gap: number } => ({ weekly: weeklyPct, ...paceOf(weeklyPct, resetsAtMs, now) })

/** The live reading from a session.measure event. */
export const liveFromMeasure = (
  rateLimits: readonly { kind: string; percentUsed: number; resetsAt?: string }[],
  ctxPercent: number | undefined,
  cost: number | null,
  cacheHit: number | null,
  now: number,
): Live => {
  const five = rateLimits.find(r => r.kind === 'five_hour')
  const week = rateLimits.find(r => r.kind === 'seven_day')
  const reset = week?.resetsAt ? Date.parse(week.resetsAt) : NaN
  return { at: now, five: five?.percentUsed ?? null, week: week?.percentUsed ?? null, weekResetMs: Number.isFinite(reset) ? reset : null, ctx: ctxPercent ?? null, cacheHit, costUsd: cost, fromFile: false }
}

const fileMs = (v: unknown): number | null => {
  if (typeof v === 'number' && Number.isFinite(v)) return v > 1e12 ? v : v * 1000
  if (typeof v === 'string' && v.trim() !== '') {
    const ms = Date.parse(v)
    return Number.isFinite(ms) ? ms : null
  }
  return null
}

const filePct = (w: unknown): number | null => {
  const v = w && typeof w === 'object' ? (w as Record<string, unknown>).used_percentage : null
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

/** Reads ~/.claude/usage-windows.json; null when unreadable or it holds neither window. */
export const liveFromMeterFile = (text: string | null): Live | null => {
  if (!text) return null
  let o: Record<string, unknown>
  try {
    const raw = JSON.parse(text) as unknown
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
    o = raw as Record<string, unknown>
  } catch {
    return null
  }
  const five = filePct(o.five_hour)
  const week = filePct(o.seven_day)
  if (five === null && week === null) return null
  const w = o.seven_day && typeof o.seven_day === 'object' ? (o.seven_day as Record<string, unknown>) : {}
  const ctx = typeof o.context_used_percentage === 'number' && Number.isFinite(o.context_used_percentage) ? o.context_used_percentage : null
  return { at: fileMs(o.written_at) ?? 0, five, week, weekResetMs: fileMs(w.resets_at), ctx, cacheHit: null, costUsd: null, fromFile: true }
}

/** "5h 23% · W 41% · PACE 38 +3 · ctx 38% · cache 92%"; "meters ?" leads when stale. */
export const statusText = (live: Live | null, now: number, sep = ' · '): string => {
  if (!live) return 'dash: no meter reading yet'
  const parts: string[] = []
  if (now - live.at > STALE_MS) parts.push('meters stale')
  if (live.five !== null) parts.push(`5h ${Math.round(live.five)}%`)
  if (live.week !== null) parts.push(`wk ${Math.round(live.week)}%`)
  if (live.week !== null && live.weekResetMs !== null) {
    const p = paceOf(live.week, live.weekResetMs, now)
    parts.push(`pace ${Math.round(p.pace)} ${p.gap >= 0 ? '+' : ''}${Math.round(p.gap)}`)
  }
  if (live.ctx !== null) parts.push(`ctx ${Math.round(live.ctx)}%`)
  if (live.cacheHit !== null) parts.push(`cache ${Math.round(live.cacheHit * 100)}%`)
  if (live.fromFile) parts.push('from meter file')
  return parts.join(sep) || 'dash: no meter reading yet'
}

export type Usage = { input_tokens: number; output_tokens: number; cache_read_input_tokens: number; cache_creation_input_tokens: number }

/** cache_read / (input + cache_read + cache_write); null with no input. */
export const cacheHit = (u: Usage): number | null => {
  const all = u.input_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens
  return all > 0 ? u.cache_read_input_tokens / all : null
}

/** D6: the fallback writer runs only when no other writer kept the meter file fresh. */
export const shouldWriteMeterFile = (fileMtimeMs: number | null, ourLastWriteMs: number | null, now: number): boolean => {
  if (fileMtimeMs === null) return true
  if (ourLastWriteMs !== null && Math.abs(fileMtimeMs - ourLastWriteMs) < 2000) return true
  return now - fileMtimeMs > STALE_MS
}

/** D6: pacewright's meter file from a measure event; null when no window is present. */
export const meterFile = (rateLimits: readonly { kind: string; percentUsed: number; resetsAt?: string }[], ctxPercent: number | null, model: string | null, now: number): Record<string, unknown> | null => {
  const entry = (k: string) => {
    const r = rateLimits.find(x => x.kind === k)
    if (!r) return null
    const ms = r.resetsAt ? Date.parse(r.resetsAt) : NaN
    return { used_percentage: r.percentUsed, resets_at: Number.isFinite(ms) ? Math.floor(ms / 1000) : null }
  }
  const five = entry('five_hour')
  const seven = entry('seven_day')
  const spend = entry('spend_limit')
  if (!five && !seven && !spend) return null
  return { written_at: Math.floor(now / 1000), model: model ? { id: model, display_name: model } : null, context_used_percentage: ctxPercent, five_hour: five, seven_day: seven, spend_limit: spend }
}
