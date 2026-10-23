// vigil tile builder: pure logic (no $). A tile the user builds is data, never code: it names one
// source, one picture and a rule, and vigil reads the source itself. No script runs, nothing is
// fetched, and a tile shows numbers and dates only, so no text from the source reaches the board.
// Specs live in the user's own folder (~/.claude/revenantworks/vigil/tiles/<id>.json), never in
// the plugin. Claude proposes them from a read-only scan; the user says yes before one is saved.
import type { Picture, Tile } from './board-logic'

export const TILE_SCHEMA = 1
export const TILES_MAX = 12
export const READ_MAX_BYTES = 1_000_000
export const SOURCE_KINDS = ['json', 'lines', 'files', 'age', 'date'] as const
export type SourceKind = (typeof SOURCE_KINDS)[number]
export const PICTURE_KINDS = ['ring', 'count', 'spark', 'dots', 'countdown'] as const
export type PictureKind = (typeof PICTURE_KINDS)[number]

/** Where the builder may scan. Each is a read-only brief for Claude, never a reader of vigil's own. */
export const BUILD_SOURCES = {
  repo: 'this repo: its files, workflows and docs',
  sessions: 'my Claude Code sessions folder (~/.claude/projects), counts and dates only',
  chats: 'chat exports I keep on this machine, if any',
  archive: 'this repo\'s git history: branches, tags and commit dates',
  tasks: 'my scheduled tasks and their run logs',
  project: 'every repo folder beside this one',
} as const
export type BuildSource = keyof typeof BUILD_SOURCES
export const isBuildSource = (v: unknown): v is BuildSource => typeof v === 'string' && Object.hasOwn(BUILD_SOURCES, v)

export type Source =
  | { kind: 'json'; path: string; field: string }
  | { kind: 'lines'; path: string; match?: string }
  | { kind: 'files'; path: string; ext?: string; olderThanDays?: number }
  | { kind: 'age'; path: string }
  | { kind: 'date'; path: string; field?: string }

export type TileSpec = {
  schema: 1
  id: string
  title: string
  source: Source
  picture: PictureKind
  /** ring: the value that fills it (default 100). */
  max?: number
  /** A value at or past warnAt draws as a warning; at or past badAt, as a fault. Lower is better when `lowIsBad`. */
  warnAt?: number
  badAt?: number
  lowIsBad?: boolean
  /** One line the detail shows: what a click on the tile tells you. */
  note?: string
}

export const ID_RE = /^[a-z0-9][a-z0-9-]{0,31}$/
export const tileKey = (id: string): `my:${string}` => `my:${id}`

/** Path segments a tile may never read, whatever the user asks: keys, tokens, secrets and git internals. */
const DENY = [/^\.ssh$/i, /^\.gnupg$/i, /^\.aws$/i, /^\.azure$/i, /^\.kube$/i, /^\.docker$/i, /^\.git$/i, /^\.env(\..*)?$/i, /credential/i, /secret/i, /token/i, /password/i, /\.pem$/i, /\.key$/i, /^id_[a-z0-9]+$/i, /pattern/i, /protected-names/i, /\.dispatch-secrets?/i]

/** A path a tile may read: under the home folder (`~/`) or the repo (`./`), with no `..` and no denied segment. */
export const pathProblem = (path: unknown): string | null => {
  if (typeof path !== 'string' || !path) return 'path is missing'
  if (path.length > 200) return 'path is longer than 200 characters'
  const p = path.replace(/\\/g, '/')
  if (!p.startsWith('~/') && !p.startsWith('./')) return 'path must start with ~/ (home) or ./ (this repo)'
  const segs = p.slice(2).split('/').filter(Boolean)
  if (!segs.length) return 'path names no file'
  if (segs.some(s => s === '..' || s === '.')) return 'path may not climb with ..'
  const bad = segs.find(s => DENY.some(r => r.test(s)))
  return bad ? `path reaches "${bad}", which a tile may never read` : null
}

/**
 * Where a path really landed (every link followed), checked again: it must sit under one of the
 * resolved bases (home, repo) and pass the same deny list, so a link cannot lead a tile to a key.
 */
export const realProblem = (real: string | undefined, bases: readonly string[]): string | null => {
  if (!real) return 'the path could not be resolved'
  const r = real.replace(/\\/g, '/')
  const base = bases.filter(Boolean).map(b => b.replace(/\\/g, '/').replace(/\/$/, '')).find(b => r === b || r.startsWith(`${b}/`))
  if (base === undefined) return 'the path leads outside home and the repo'
  const segs = r.slice(base.length).split('/').filter(Boolean)
  const bad = segs.find(x => DENY.some(d => d.test(x)))
  return bad ? `the path leads to "${bad}", which a tile may never read` : null
}

/** Absolute form of a tile path, or null when vigil has no repo for a ./ path. */
export const resolvePath = (path: string, home: string, root: string): string | null => {
  const p = path.replace(/\\/g, '/')
  if (p.startsWith('~/')) return home ? `${home}/${p.slice(2)}` : null
  return root ? `${root}/${p.slice(2)}` : null
}

const clean = (s: unknown, max: number): string | null =>
  typeof s === 'string' && s.trim() ? s.replace(/[\u0000-\u001f\u007f<>]/g, '').trim().slice(0, max) : null
const num = (v: unknown): number | undefined => (typeof v === 'number' && Number.isFinite(v) ? v : undefined)

/** Which pictures each source can feed. */
const FEEDS: Record<SourceKind, readonly PictureKind[]> = {
  json: ['ring', 'count', 'spark', 'dots', 'countdown'],
  lines: ['ring', 'count'],
  files: ['ring', 'count', 'spark'],
  age: ['count', 'countdown'],
  date: ['countdown'],
}

/** A spec file, checked: the spec, or every reason it is refused. Unknown keys are refused, so a typo never passes silently. */
export const parseSpec = (text: string, fileId?: string): { spec: TileSpec } | { errors: string[] } => {
  let o: Record<string, unknown>
  try {
    const v: unknown = JSON.parse(text)
    if (!v || typeof v !== 'object' || Array.isArray(v)) return { errors: ['not a JSON object'] }
    o = v as Record<string, unknown>
  } catch {
    return { errors: ['not valid JSON'] }
  }
  const errors: string[] = []
  const KEYS = ['schema', 'id', 'title', 'source', 'picture', 'max', 'warnAt', 'badAt', 'lowIsBad', 'note']
  for (const key of Object.keys(o)) if (!KEYS.includes(key)) errors.push(`unknown key "${key.slice(0, 20)}"`)
  if (o.schema !== TILE_SCHEMA) errors.push(`schema must be ${TILE_SCHEMA}`)
  const id = typeof o.id === 'string' && ID_RE.test(o.id) ? o.id : null
  if (!id) errors.push('id must be lowercase letters, digits and dashes, at most 32')
  else if (fileId !== undefined && fileId !== id) errors.push(`id "${id}" does not match the file name "${fileId}.json"`)
  const title = clean(o.title, 24)
  if (!title) errors.push('title is missing')
  const picture = (PICTURE_KINDS as readonly unknown[]).includes(o.picture) ? (o.picture as PictureKind) : null
  if (!picture) errors.push(`picture must be one of ${PICTURE_KINDS.join(', ')}`)
  const s = o.source && typeof o.source === 'object' && !Array.isArray(o.source) ? (o.source as Record<string, unknown>) : null
  let source: Source | null = null
  if (!s) errors.push('source is missing')
  else {
    const kind = (SOURCE_KINDS as readonly unknown[]).includes(s.kind) ? (s.kind as SourceKind) : null
    const pp = pathProblem(s.path)
    if (!kind) errors.push(`source.kind must be one of ${SOURCE_KINDS.join(', ')}`)
    if (pp) errors.push(`source.${pp}`)
    const allowed: Record<SourceKind, string[]> = { json: ['field'], lines: ['match'], files: ['ext', 'olderThanDays'], age: [], date: ['field'] }
    if (kind) for (const key of Object.keys(s)) if (key !== 'kind' && key !== 'path' && !allowed[kind].includes(key)) errors.push(`source.${key.slice(0, 20)} does not apply to a ${kind} source`)
    if (kind && !pp) {
      const path = (s.path as string).replace(/\\/g, '/')
      const field = clean(s.field, 80)
      if (kind === 'json') {
        if (!field || !/^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$/.test(field)) errors.push('source.field must be a dotted path such as "runs.0.ok"')
        else source = { kind, path, field }
      } else if (kind === 'lines') {
        const match = clean(s.match, 40)
        source = match ? { kind, path, match } : { kind, path }
      } else if (kind === 'files') {
        const ext = clean(s.ext, 12)
        const older = num(s.olderThanDays)
        if (ext !== null && !/^\.?[A-Za-z0-9]+$/.test(ext)) errors.push('source.ext must look like ".md"')
        source = { kind, path, ...(ext ? { ext: ext.startsWith('.') ? ext : `.${ext}` } : {}), ...(older !== undefined && older > 0 ? { olderThanDays: older } : {}) }
      } else if (kind === 'date') {
        if (s.field !== undefined && (!field || !/^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$/.test(field))) errors.push('source.field must be a dotted path')
        source = field ? { kind, path, field } : { kind, path }
      } else source = { kind, path }
    }
    if (kind && picture && !FEEDS[kind].includes(picture)) errors.push(`a ${kind} source cannot draw a ${picture}; it draws ${FEEDS[kind].join(', ')}`)
  }
  for (const key of ['max', 'warnAt', 'badAt'] as const) if (o[key] !== undefined && num(o[key]) === undefined) errors.push(`${key} must be a number`)
  if (o.max !== undefined && (num(o.max) ?? 0) <= 0) errors.push('max must be above 0')
  if (o.lowIsBad !== undefined && typeof o.lowIsBad !== 'boolean') errors.push('lowIsBad must be true or false')
  if (o.note !== undefined && !clean(o.note, 120)) errors.push('note must be text')
  if (errors.length || !id || !title || !picture || !source) return { errors }
  const spec: TileSpec = { schema: 1, id, title, source, picture }
  if (num(o.max) !== undefined) spec.max = num(o.max)!
  if (num(o.warnAt) !== undefined) spec.warnAt = num(o.warnAt)!
  if (num(o.badAt) !== undefined) spec.badAt = num(o.badAt)!
  if (o.lowIsBad === true) spec.lowIsBad = true
  const note = clean(o.note, 120)
  if (note) spec.note = note
  return { spec }
}

// ---------- reading a source ----------

/** What vigil read for a tile: the raw material, gathered by the caller's $.fs, decided on here. */
export type Reading =
  | { kind: 'text'; text: string; mtimeMs: number }
  | { kind: 'files'; entries: ReadonlyArray<{ name: string; kind: string; mtimeMs: number }> }
  | { kind: 'missing'; why: string }

/** A tile's value: a number, a list of numbers, a list of flags, a moment, or nothing with a reason. */
export type Value =
  | { kind: 'n'; n: number }
  | { kind: 'ns'; ns: number[] }
  | { kind: 'flags'; flags: Array<boolean | null> }
  | { kind: 'at'; at: number }
  | { kind: 'none'; why: string }

const DAY = 86_400_000
const ISO = /\b(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)(Z|[+-]\d{2}:?\d{2})?)?\b/

const dateOf = (v: unknown): number | null => {
  if (typeof v === 'number' && Number.isFinite(v)) return v > 1e12 ? v : v * 1000
  if (typeof v !== 'string') return null
  const m = ISO.exec(v)
  if (!m) return null
  const t = Date.parse(m[2] ? `${m[1]}T${m[2]}${m[3] ?? 'Z'}` : `${m[1]}T00:00:00Z`)
  return Number.isFinite(t) ? t : null
}

const dig = (v: unknown, field: string): unknown => {
  let cur = v
  for (const part of field.split('.')) {
    if (Array.isArray(cur) && /^\d+$/.test(part)) cur = cur[Number(part)]
    else if (cur && typeof cur === 'object' && !Array.isArray(cur) && Object.hasOwn(cur, part)) cur = (cur as Record<string, unknown>)[part]
    else return undefined
  }
  return cur
}

const flagOf = (v: unknown): boolean | null => {
  if (typeof v === 'boolean') return v
  if (typeof v === 'number') return v > 0
  if (typeof v === 'string') return /^(ok|pass|passed|success|green|true|yes|done)$/i.test(v) ? true : /^(fail|failed|failure|error|red|false|no|missed)$/i.test(v) ? false : null
  if (v && typeof v === 'object' && !Array.isArray(v)) {
    const o = v as Record<string, unknown>
    for (const key of ['ok', 'conclusion', 'status', 'result', 'pass']) if (key in o) return flagOf(o[key])
  }
  return null
}

/** The value a tile shows, from what was read. Text from the source is never kept: only counts, numbers and dates. */
export const valueOf = (spec: TileSpec, r: Reading, now: number): Value => {
  if (r.kind === 'missing') return { kind: 'none', why: r.why }
  const s = spec.source
  if (s.kind === 'files') {
    if (r.kind !== 'files') return { kind: 'none', why: 'not a folder' }
    const files = r.entries.filter(e => e.kind === 'file' && (!s.ext || e.name.toLowerCase().endsWith(s.ext.toLowerCase())))
    const kept = s.olderThanDays ? files.filter(e => now - e.mtimeMs > s.olderThanDays! * DAY) : files
    if (spec.picture === 'spark') return { kind: 'ns', ns: Array.from({ length: 14 }, (_, i) => kept.filter(e => Math.floor((now - e.mtimeMs) / DAY) === 13 - i).length) }
    return { kind: 'n', n: kept.length }
  }
  if (r.kind !== 'text') return { kind: 'none', why: 'a folder, not a file' }
  if (s.kind === 'age') return spec.picture === 'countdown' ? { kind: 'at', at: r.mtimeMs } : { kind: 'n', n: Math.floor((now - r.mtimeMs) / DAY) }
  if (s.kind === 'lines') {
    const lines = r.text.split(/\r?\n/).filter(l => l.trim())
    return { kind: 'n', n: s.match ? lines.filter(l => l.includes(s.match!)).length : lines.length }
  }
  if (s.kind === 'date' && !s.field) {
    const at = dateOf(r.text)
    return at === null ? { kind: 'none', why: 'no date in the file' } : { kind: 'at', at }
  }
  let doc: unknown
  try {
    doc = JSON.parse(r.text)
  } catch {
    return { kind: 'none', why: 'the file is not JSON' }
  }
  const v = dig(doc, s.field!)
  if (v === undefined) return { kind: 'none', why: `no field ${s.field}` }
  if (spec.picture === 'countdown') {
    const at = dateOf(v)
    return at === null ? { kind: 'none', why: `${s.field} is not a date` } : { kind: 'at', at }
  }
  if (spec.picture === 'dots') return Array.isArray(v) ? { kind: 'flags', flags: v.slice(-12).map(flagOf) } : { kind: 'flags', flags: [flagOf(v)] }
  if (spec.picture === 'spark') return Array.isArray(v) ? { kind: 'ns', ns: v.slice(-14).map(x => (typeof x === 'number' && Number.isFinite(x) ? x : 0)) } : { kind: 'none', why: `${s.field} is not a list` }
  if (typeof v === 'number' && Number.isFinite(v)) return { kind: 'n', n: v }
  if (Array.isArray(v)) return { kind: 'n', n: v.length }
  if (v && typeof v === 'object') return { kind: 'n', n: Object.keys(v).length }
  return { kind: 'none', why: `${s.field} is not a number` }
}

// ---------- drawing a user's tile ----------

/** 'bad', 'warn' or 'ok' by the spec's rule; null when it has none. */
export const levelOf = (spec: TileSpec, n: number): 'ok' | 'warn' | 'bad' | null => {
  if (spec.warnAt === undefined && spec.badAt === undefined) return null
  const past = (t: number | undefined) => t !== undefined && (spec.lowIsBad ? n <= t : n >= t)
  return past(spec.badAt) ? 'bad' : past(spec.warnAt) ? 'warn' : 'ok'
}

const short = (n: number): string => (Math.abs(n) >= 10_000 ? `${Math.round(n / 1000)}k` : Number.isInteger(n) ? String(n) : n.toFixed(1))

const until = (at: number, now: number): { big: string; sub: string; days: number } => {
  const d = (at - now) / DAY
  const abs = Math.abs(d)
  const big = abs >= 2 ? `${Math.round(abs)}d` : `${Math.max(0, Math.round(abs * 24))}h`
  return { big, sub: d >= 0 ? 'to go' : 'ago', days: d }
}

/** A user's tile as the board draws it, and its detail lines. */
export const userTileOf = (spec: TileSpec, v: Value, now: number): { tile: Tile; lines: string[] } => {
  const id = tileKey(spec.id)
  const reads = `Reads ${spec.source.path}${'field' in spec.source && spec.source.field ? `, field ${spec.source.field}` : ''}${spec.source.kind === 'lines' && spec.source.match ? `, lines with "${spec.source.match}"` : ''}.`
  const tail = [reads, ...(spec.note ? [spec.note] : [])]
  const done = (picture: Picture, big: string, sub: string, first: string) => ({ tile: { id, title: spec.title, picture, big, sub }, lines: [first, ...tail].slice(0, 3) })
  if (v.kind === 'none') return done({ kind: 'word', text: '–' }, '–', v.why, `Nothing to show: ${v.why}.`)
  const rule = (n: number): string => {
    const l = levelOf(spec, n)
    return l === 'bad' ? 'past the limit' : l === 'warn' ? 'near the limit' : ''
  }
  switch (spec.picture) {
    case 'ring': {
      const n = v.kind === 'n' ? v.n : 0
      const max = spec.max ?? 100
      const p = Math.max(0, Math.min(100, (n / max) * 100))
      const warnAt = spec.warnAt === undefined ? undefined : Math.max(0, Math.min(100, (spec.warnAt / max) * 100))
      return done({ kind: 'rings', rings: [{ label: spec.title.slice(0, 6).toLowerCase(), pct: p, tick: null, ...(warnAt === undefined ? {} : { warnAt }) }] }, `${Math.round(p)}%`, rule(n) || `${short(n)} of ${short(max)}`, `${short(n)} of ${short(max)}.`)
    }
    case 'count': {
      const n = v.kind === 'n' ? v.n : 0
      return done({ kind: 'badge', n: Math.round(n) }, short(n), rule(n) || (spec.source.kind === 'age' ? 'days since it changed' : 'now'), `${short(n)} now.`)
    }
    case 'spark': {
      const ns = v.kind === 'ns' ? v.ns : []
      const last = ns.at(-1) ?? 0
      return done({ kind: 'spark', values: ns, label: spec.title }, short(last), rule(last) || `last of ${ns.length}`, `Last ${ns.length}: ${ns.map(short).join(', ')}.`)
    }
    case 'dots': {
      const flags = v.kind === 'flags' ? v.flags : []
      const bad = flags.filter(f => f === false).length
      return done({ kind: 'dots', dots: flags.map((ok, i) => ({ ok, label: `${i + 1}` })) }, bad ? `${bad} failing` : 'ok', `${flags.length} shown`, `${flags.filter(f => f === true).length} pass, ${bad} fail, ${flags.filter(f => f === null).length} unknown.`)
    }
    case 'countdown': {
      const at = v.kind === 'at' ? v.at : now
      const u = until(at, now)
      return done({ kind: 'word', text: u.big }, u.big, rule(u.days) || u.sub, `${new Date(at).toISOString().slice(0, 10)}: ${u.big} ${u.sub}.`)
    }
  }
}

// ---------- the builder's brief ----------

/** The prompt the Build a tile pane hands to Claude: scan read-only, propose, save only on a yes. */
export const buildPrompt = (src: BuildSource, folder: string): string =>
  [
    `Propose up to four vigil tiles from ${BUILD_SOURCES[src]}. Read only: run nothing that writes, fetch nothing.`,
    'A vigil tile is data, never code: one JSON file that names one source, one picture and a rule. vigil reads the source itself and shows numbers and dates only.',
    `Schema: {"schema":1,"id":"<kebab id>","title":"<at most 24 characters>","source":{...},"picture":"ring|count|spark|dots|countdown","max":<ring fill>,"warnAt":<n>,"badAt":<n>,"lowIsBad":<bool>,"note":"<one line a click shows>"}.`,
    'Sources: {"kind":"json","path":P,"field":"a.b.0"} (any picture) · {"kind":"lines","path":P,"match":"TODO"} (ring, count) · {"kind":"files","path":DIR,"ext":".md","olderThanDays":30} (ring, count, spark of files by day) · {"kind":"age","path":P} (count of days, countdown) · {"kind":"date","path":P,"field":"optional"} (countdown to the first date in the file).',
    'P starts with ~/ (home) or ./ (this repo). A tile never reads keys, tokens, secrets, .env files or .git. Propose only tiles that a source above can feed from a file that already exists; say which file each one reads.',
    'For each tile show its picture, what it reads, what a click gives, and the JSON. Write nothing until I say yes.',
    `On my yes, save each one I accept to ${folder}/<id>.json, then tell me to run /rw-vigil tiles to check them.`,
  ].join('\n')
