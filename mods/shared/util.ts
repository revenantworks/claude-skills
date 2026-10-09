// Small pure helpers shared by every Revenantworks mod.

/** Token shapes masked before anything is stored or shown (keywarden's prefix classes). */
const TOKEN_RE =
  /(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{16,}|(?:AKIA|ASIA)[A-Z0-9]{16}|xox[abposr]-[A-Za-z0-9-]{10,}|glpat-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{30,}|npm_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)/g
const BEARER_RE = /\b(bearer|token)\s+[A-Za-z0-9._~+/=-]{12,}/gi

export const maskTokens = (text: string): string =>
  text.replace(TOKEN_RE, '[REDACTED]').replace(BEARER_RE, '$1 [REDACTED]')

export const clip = (text: string, width: number): string =>
  text.length <= width ? text : `${text.slice(0, Math.max(0, width - 3))}...`

/** "4m", "3h", "2d" for an age in milliseconds; "?" for a negative or missing age. */
export const formatAge = (ms: number | undefined): string => {
  if (ms === undefined || !Number.isFinite(ms) || ms < 0) return '?'
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 48) return `${h}h`
  return `${Math.floor(h / 24)}d`
}

/** A text bar: █ for used, ░ for the rest. Never colour alone: callers print the number too. */
export const bar = (percent: number | undefined, width = 20): string => {
  if (percent === undefined || !Number.isFinite(percent)) return '?'.padEnd(width, '·')
  const p = Math.max(0, Math.min(100, percent))
  const full = Math.round((p / 100) * width)
  return '█'.repeat(full) + '░'.repeat(width - full)
}

/** FNV-1a 32-bit, hex: a stable short id, never a secret fingerprint. */
export const fnv1a = (text: string): string => {
  let h = 0x811c9dc5
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h.toString(16).padStart(8, '0')
}

/** Lower-case, forward slashes: compare paths the same way on Windows and Linux. */
export const normPath = (p: string): string => p.replace(/\\/g, '/').replace(/\/+/g, '/').toLowerCase()

/** True when `path` sits under `root` after normalising both. */
export const isUnder = (path: string, root: string): boolean => {
  const a = normPath(path)
  const b = normPath(root).replace(/\/$/, '')
  return a === b || a.startsWith(`${b}/`)
}

export const repoSlug = (cwd: string): string => {
  const parts = cwd.replace(/\\/g, '/').split('/').filter(Boolean)
  return (parts[parts.length - 1] ?? 'root').toLowerCase().replace(/[^a-z0-9._-]+/g, '-')
}

/** Shell segments of a Bash or PowerShell command: quoted text blanked, split on ; && || | and newlines. */
export const shellSegments = (command: string): string[] =>
  command
    .replace(/"(?:[^"\\]|\\.)*"|'[^']*'/g, '""')
    .split(/&&|\|\||[;\n|]/)
    .map(s => s.trim())
    .filter(s => s.length > 0)

/** The segments that start with the given program words, after env-style prefixes and common launchers. */
export const segmentsRunning = (command: string, words: RegExp): string[] =>
  shellSegments(command).filter(seg => {
    const stripped = seg.replace(/^((\w+=\S*|sudo|env|nohup|time|command|&)\s+)*/, '')
    return words.test(stripped)
  })

/** Commit messages from `git commit -m "..."` (each -m), read from the raw command. */
export const commitMessages = (command: string): string[] => {
  const out: string[] = []
  const re = /\s-[a-z]*m\s+("(?:[^"\\]|\\.)*"|'[^']*')|\s--message[= ]("(?:[^"\\]|\\.)*"|'[^']*')/g
  let m: RegExpExecArray | null
  while ((m = re.exec(command)) !== null) out.push((m[1] ?? m[2] ?? '').slice(1, -1))
  return out
}

export const isWindowsEnv = (os: string | undefined): boolean => (os ?? '').toLowerCase().includes('windows')

/** Walk any JSON value and rewrite every string inside it. */
export const mapStrings = (value: unknown, fn: (s: string, key: string) => string, key = '', depth = 0): unknown => {
  if (depth > 12) return value
  if (typeof value === 'string') return fn(value, key)
  if (Array.isArray(value)) return value.map(x => mapStrings(x, fn, key, depth + 1))
  if (value && typeof value === 'object') {
    const o: Record<string, unknown> = {}
    for (const [k, x] of Object.entries(value)) o[k] = /^(id|tool_use_id|uuid|type|name|media_type)$/.test(k) ? x : mapStrings(x, fn, k, depth + 1)
    return o
  }
  return value
}

/** How long a session's heartbeat counts as alive. Writers beat every minute. */
export const HEARTBEAT_FRESH_MS = 10 * 60_000

/**
 * A mod's heartbeat file, shared by every session on the machine: the newest writer's fields at
 * the top, and `sessions`, every live session's hash and last beat. One file per mod kept a single
 * writer's session only, so a second session's beat turned the first one's mod "not loaded".
 */
export const mergeHeartbeat = (prev: string | null, beat: Record<string, unknown> & { session: string; at: number }): string => {
  let sessions: Record<string, number> = {}
  try {
    const o = JSON.parse(prev ?? '') as { sessions?: unknown }
    if (o.sessions && typeof o.sessions === 'object') {
      for (const [k, v] of Object.entries(o.sessions as Record<string, unknown>)) {
        if (typeof v === 'number' && beat.at - v < HEARTBEAT_FRESH_MS && /^[0-9a-f]{8}$/.test(k)) sessions[k] = v
      }
    }
  } catch {
    sessions = {}
  }
  sessions[beat.session] = beat.at
  const keep = Object.entries(sessions).sort((a, b) => b[1] - a[1]).slice(0, 50)
  return JSON.stringify({ ...beat, sessions: Object.fromEntries(keep) })
}

/** Whether a heartbeat file shows this session alive: its own entry in `sessions`, or the top fields. */
export const heartbeatAlive = (text: string | null, session: string, now: number): { alive: boolean; version: string | null; caught: number; at: number | null } => {
  try {
    const b = JSON.parse(text ?? '') as { session?: string; at?: number; version?: string; caught?: number; sessions?: Record<string, unknown> }
    const mine = typeof b.sessions?.[session] === 'number' ? (b.sessions[session] as number) : b.session === session ? (b.at ?? 0) : null
    const fresh = mine !== null && now - mine < HEARTBEAT_FRESH_MS
    return { alive: fresh, version: b.version ?? null, caught: b.session === session ? (b.caught ?? 0) : 0, at: mine }
  } catch {
    return { alive: false, version: null, caught: 0, at: null }
  }
}
