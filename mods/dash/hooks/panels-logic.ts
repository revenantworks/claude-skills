// dash panels: pure logic (no $) for the optional per-pack panels and the health checks.
// D9 research and palette (was S4), D10 GPU lease (was L1), D11 Godot proof (was G1), D8 pins
// (was C14) and the version check behind /dash doctor (was C5). Ported as they were.
import { parseShell } from './lib/shell'
import { normPath } from './lib/util'

// ---------- D9: research band and palette (brandscribe resolve order) ----------

/** The research band starts when researchscribe runs. */
export const RESEARCH_SKILL = /researchscribe/i

export type RosterRow = { slug: string; scope: string }

export const parseRoster = (md: string | null): RosterRow[] =>
  (md ?? '').split('\n').filter(l => /^\|/.test(l) && !/^\|\s*-/.test(l)).map(l => l.split('|').map(c => c.trim()).filter(Boolean)).filter(c => c.length >= 2 && !/^slug$/i.test(c[0]!)).map(c => ({ slug: c[0]!.replace(/`/g, ''), scope: c[1]! }))

/** named → scoped → ask. */
export const resolveBrand = (rows: readonly RosterRow[], named: string | null, repoSlug: string, rel: string): { slug: string | null; how: 'named' | 'scoped' | 'ask' } => {
  if (named && rows.some(r => r.slug === named)) return { slug: named, how: 'named' }
  const tokens = (r: RosterRow) => r.scope.toLowerCase().replace(/`/g, '').split(/[\s,;]+/).filter(Boolean)
  const scoped = rows.filter(r => tokens(r).includes(repoSlug.toLowerCase()) || (rel !== '' && tokens(r).some(s => s.includes('/') && normPath(rel).startsWith(normPath(s)))))
  return scoped.length === 1 ? { slug: scoped[0]!.slug, how: 'scoped' } : { slug: null, how: 'ask' }
}

export const paletteTokens = (md: string): Array<{ token: string; hex: string }> => {
  const out: Array<{ token: string; hex: string }> = []
  for (const line of md.split('\n')) {
    const tok = line.match(/`([a-z][\w-]*)`/)
    const hex = line.match(/#[0-9a-fA-F]{6}\b/)
    if (tok && hex) out.push({ token: tok[1]!, hex: hex[0] })
  }
  return out.slice(0, 24)
}

// ---------- D10: GPU lease and live readings ----------

export type Lease = { holder: string; purpose: string; started: string; expires: string; est_vram_bytes: number | null; est_ram_bytes: number | null; device: string | null; instance_ids: string[] }

export const parseLease = (text: string | null): Lease | 'unreadable' | null => {
  if (text === null) return null
  try {
    const d = JSON.parse(text) as Partial<Lease>
    if (typeof d.holder !== 'string') return 'unreadable'
    return { holder: d.holder, purpose: d.purpose ?? '', started: d.started ?? '', expires: d.expires ?? '', est_vram_bytes: d.est_vram_bytes ?? null, est_ram_bytes: d.est_ram_bytes ?? null, device: d.device ?? null, instance_ids: d.instance_ids ?? [] }
  } catch {
    return 'unreadable'
  }
}

export const leasePath = (isWin: boolean, env: { LOCALAPPDATA?: string; XDG_STATE_HOME?: string; HOME: string }): string =>
  isWin && env.LOCALAPPDATA ? `${env.LOCALAPPDATA.replace(/\\/g, '/')}/localops/gpu-lease.json` : `${(env.XDG_STATE_HOME ?? `${env.HOME}/.local/state`).replace(/\\/g, '/')}/localops/gpu-lease.json`

const gb = (b: number | null | undefined): string => (b === null || b === undefined ? '?' : `${(b / 1024 ** 3).toFixed(1)} GB`)

export type Readings = {
  comfy: { vramFree: number | null; vramTotal: number | null; running: number; pending: number } | null
  lms: string[] | null
  ollama: Array<{ name: string; vram: number | null; expires: string | null }> | null
  at: number
}

export const comfyFrom = (stats: string | null, queue: string | null): Readings['comfy'] => {
  if (stats === null && queue === null) return null
  try {
    const s = stats ? (JSON.parse(stats) as { devices?: Array<{ vram_free?: number; vram_total?: number }> }) : {}
    const q = queue ? (JSON.parse(queue) as { queue_running?: unknown[]; queue_pending?: unknown[] }) : {}
    const d = s.devices?.[0]
    return { vramFree: d?.vram_free ?? null, vramTotal: d?.vram_total ?? null, running: q.queue_running?.length ?? 0, pending: q.queue_pending?.length ?? 0 }
  } catch {
    return null
  }
}

export const lmsFrom = (json: string | null): string[] | null => {
  if (json === null) return null
  try {
    const d = JSON.parse(json) as { data?: Array<{ id?: string; loaded_instances?: Array<{ id?: string }>; state?: string }> }
    return (d.data ?? []).flatMap(m => (m.loaded_instances ?? []).map(i => i.id ?? m.id ?? '?').concat(m.state === 'loaded' && !m.loaded_instances ? [m.id ?? '?'] : []))
  } catch {
    return null
  }
}

export const ollamaFrom = (json: string | null): Readings['ollama'] => {
  if (json === null) return null
  try {
    const d = JSON.parse(json) as { models?: Array<{ name?: string; size_vram?: number; expires_at?: string }> }
    return (d.models ?? []).map(m => ({ name: m.name ?? '?', vram: m.size_vram ?? null, expires: m.expires_at ?? null }))
  } catch {
    return null
  }
}

export const leaseLines = (lease: Lease | 'unreadable' | null, r: Readings | null, now: number): string[] => {
  const lines: string[] = []
  if (lease === null) lines.push('GPU lease: free (no lease file)')
  else if (lease === 'unreadable') lines.push('GPU lease: UNREADABLE; treat as stale and ask the user')
  else {
    const exp = Date.parse(lease.expires)
    const left = Number.isFinite(exp) ? Math.round((exp - now) / 60_000) : null
    lines.push(`GPU lease: ${lease.holder} · ${lease.purpose || 'no purpose'} · ${left === null ? 'no expiry' : left >= 0 ? `${left} min left` : `STALE ${-left} min ago`}`)
    lines.push(`  est VRAM ${gb(lease.est_vram_bytes)} · est RAM ${gb(lease.est_ram_bytes)} · device ${lease.device ?? '?'} · ${lease.instance_ids.length} instance(s)`)
    if (left !== null && left >= 0 && left < 5) lines.push('  renew soon: the holder rewrites expires before it passes')
  }
  if (!r) {
    lines.push('Live readings: none yet')
    return lines
  }
  const age = Math.round((now - r.at) / 1000)
  lines.push(`Live readings (${age}s old):`)
  lines.push(r.comfy ? `  ComfyUI: VRAM free ${gb(r.comfy.vramFree)} of ${gb(r.comfy.vramTotal)} · running ${r.comfy.running} · pending ${r.comfy.pending}${r.comfy.running + r.comfy.pending > 0 ? ' (busy)' : ''}` : '  ComfyUI: not answering')
  lines.push(r.lms ? `  LM Studio: ${r.lms.length} loaded${r.lms.length ? ` (${r.lms.slice(0, 3).join(', ')})` : ''}` : '  LM Studio: not answering')
  lines.push(r.ollama ? `  Ollama: ${r.ollama.length} loaded${r.ollama.length ? ` (${r.ollama.map(m => `${m.name} ${gb(m.vram)}`).slice(0, 3).join(', ')})` : ''}` : '  Ollama: not answering')
  if (lease && lease !== 'unreadable' && r.comfy && r.comfy.running > 0 && lease.holder !== 'comfyrunner') lines.push(`  ComfyUI is rendering while ${lease.holder} holds the lease: two consumers on one card`)
  return lines
}

// ---------- D11: Godot proof ----------

export type CiFacts = { floor: number | null; scripts: number | null; slackMax: number | null; gdir: string | null; commands: string[] }

/** The Godot test steps a workflow runs, with its pinned script count and test floor. */
export const ciFacts = (yaml: string): CiFacts => ({
  floor: Number(yaml.match(/TESTS_FLOOR\s*=\s*(\d+)/)?.[1] ?? NaN) || null,
  scripts: Number(yaml.match(/Scripts(?:\\s\+|\s+)(\d+)/)?.[1] ?? NaN) || null,
  slackMax: Number(yaml.match(/SLACK_MAX\s*=\s*(\d+)/)?.[1] ?? NaN) || null,
  gdir: yaml.match(/-gdir=(\S+)/)?.[1] ?? null,
  commands: [...yaml.matchAll(/^\s*(godot[^\n|]*)/gm)].map(m => m[1]!.trim().replace(/\s*\\$/, '')),
})

export type RunKind = { test: boolean; whole: boolean; import: boolean }

export const godotRun = (command: string, shell: 'sh' | 'ps', ciGdir: string | null = null): RunKind => {
  const p = parseShell(command, shell)
  // Godot ships as godot, godot4, Godot_v4.3-stable_linux.x86_64, Godot_v4.3-stable_win64.exe ...
  const g = p.commands.find(c => /^godot/.test(c.prog))
  if (!g) return { test: false, whole: false, import: false }
  const a = g.argv.join(' ')
  const gut = /gut_cmdln\.gd/.test(a)
  const gdunit = /gdunit|GdUnitCmdTool/i.test(a)
  const imp = /--import\b/.test(a) || (/--editor\b/.test(a) && /--quit\b/.test(a))
  const test = gut || gdunit
  const gdir = a.match(/-gdir=(\S+)/)?.[1] ?? null
  // Only the whole suite backs a claim: a narrower -gdir than CI's, or any filter, is partial.
  const narrower = gdir !== null && gdir.replace(/\/$/, '') !== (ciGdir ?? 'res://tests').replace(/\/$/, '')
  const partial = narrower || /-g(select|test|inner_class|unit_test_name|prefix|suffix)=/.test(a) || (gdunit && /-a\s+\S+\.gd\b/.test(a))
  return { test, whole: test && !partial, import: imp }
}

/** A run counts as proof only as a lone command or a tee with pipefail: no ||, no $(), no other pipe. */
export const countsAsProof = (command: string): boolean => {
  if (/\|\||\$\(|`/.test(command)) return false
  // Anything after the run (`; true`, a second line) can hide its exit; `set -o pipefail;` before it is fine.
  const rest = command.replace(/^\s*set -o pipefail\s*(;|&&|\n)\s*/, '')
  if (/;|\n|&&/.test(rest.replace(/\|\s*tee\b.*$/, ''))) return false
  const pipes = command.split(/(?<!\|)\|(?!\|)/).length - 1
  if (pipes === 0) return true
  return pipes === 1 && /\|\s*tee\b/.test(command) && /set -o pipefail/.test(command)
}

export type GutCounts = { scripts: number | null; tests: number | null; passing: number | null; failing: number | null; errors: number }

const ERR = /SCRIPT ERROR|Parse Error|Failed to load|Cannot open file|Resource file not found/

/** Engine error lines, less the exact lines the project's ci/benign-errors.txt allows (ci-guards.md). */
export const errorLines = (log: string, benign: readonly string[]): number =>
  log.split('\n').filter(l => ERR.test(l) && !benign.includes(l)).length

const count = (log: string, re: RegExp): number | null => {
  const m = log.match(re)
  return m ? Number(m[1]) : null
}

export const gutCounts = (log: string, benign: readonly string[] = []): GutCounts => ({
  scripts: count(log, /^\s*Scripts\s+(\d+)\s*$/m),
  tests: count(log, /^\s*Tests\s+(\d+)\s*$/m),
  passing: count(log, /^\s*Passing(?: Tests)?\s+(\d+)\s*$/m),
  failing: count(log, /^\s*Failing(?: Tests)?\s+(\d+)\s*$/m),
  errors: errorLines(log, benign),
})

export const junitCounts = (xml: string): GutCounts | null => {
  const suites = [...xml.matchAll(/<testsuite\b([^>]*)>/g)].map(m => m[1]!)
  if (suites.length === 0) return null
  const num = (attrs: string, k: string) => Number(attrs.match(new RegExp(`\\b${k}="(\\d+)"`))?.[1] ?? 0)
  const tests = suites.reduce((n, s) => n + num(s, 'tests'), 0)
  const failing = suites.reduce((n, s) => n + num(s, 'failures') + num(s, 'errors'), 0)
  return { scripts: suites.length, tests, passing: tests - failing - suites.reduce((n, s) => n + num(s, 'skipped'), 0), failing, errors: 0 }
}

export type ProofStatus = 'Not run' | 'Running' | 'Passed' | 'Failed' | 'Stale' | 'Unknown'

export type Proof = { status: ProofStatus; at: number; counts: GutCounts | null; why: string }

/** The verdict for one finished run. UNMEASURED is never green. */
export const judge = (exitOk: boolean, whole: boolean, proof: boolean, counts: GutCounts | null, ci: CiFacts | null, at: number): Proof => {
  if (!proof) return { status: 'Unknown', at, counts, why: 'the command used ||, $() or a pipe without pipefail, so its exit proves nothing' }
  if (!whole) return { status: 'Unknown', at, counts, why: 'a partial run (one test or file) does not back a claim about the project' }
  if (!counts || counts.tests === null || counts.tests === 0) return { status: exitOk ? 'Unknown' : 'Failed', at, counts, why: counts?.tests === 0 ? 'zero tests ran: unmeasured' : 'no Tests line: unmeasured' }
  if (counts.errors > 0) return { status: 'Failed', at, counts, why: `${counts.errors} engine error marker(s) in the log` }
  if (!exitOk || (counts.failing ?? 0) > 0) return { status: 'Failed', at, counts, why: `${counts.failing ?? '?'} failing` }
  if (ci?.scripts && counts.scripts !== null && counts.scripts !== ci.scripts) return { status: 'Failed', at, counts, why: `${counts.scripts} scripts ran, CI expects ${ci.scripts}` }
  if (ci?.floor && counts.tests < ci.floor) return { status: 'Failed', at, counts, why: `${counts.tests} tests, below the CI floor of ${ci.floor}` }
  if (ci?.floor && ci.slackMax !== null && counts.tests - ci.floor > ci.slackMax) return { status: 'Failed', at, counts, why: `the floor is ${counts.tests - ci.floor} behind the suite (SLACK_MAX ${ci.slackMax}); raise TESTS_FLOOR to ${counts.tests}, as CI will demand` }
  return { status: 'Passed', at, counts, why: ci?.floor ? `${counts.tests} tests, floor ${ci.floor}, slack ${counts.tests - ci.floor}` : `${counts.tests} tests (no CI floor found)` }
}

export const isGodotSource = (rel: string): boolean => /\.(gd|tscn|tres|gdshader|cfg|import)$/.test(rel) || /(^|\/)project\.godot$/.test(rel)

export const bandLine = (p: Proof | null, now: number): string => {
  if (!p) return 'Godot proof: Not run'
  const c = p.counts
  const age = Math.round((now - p.at) / 60_000)
  return `Godot proof: ${p.status} · ${c?.tests ?? '?'} tests${c?.scripts ? ` · ${c.scripts} scripts` : ''} · ${age} min ago · ${p.why}`
}

/** The floor may only rise: a lower TESTS_FLOOR in a workflow edit. */
export const floorDrop = (before: string, after: string): string | null => {
  const a = Number(before.match(/TESTS_FLOOR\s*=\s*(\d+)/)?.[1] ?? NaN)
  const b = Number(after.match(/TESTS_FLOOR\s*=\s*(\d+)/)?.[1] ?? NaN)
  return Number.isFinite(a) && Number.isFinite(b) && b < a ? `TESTS_FLOOR drops from ${a} to ${b}; the floor only rises (godotsmith ci-guards).` : null
}

// ---------- D8: instruction-file pins ----------

export type Pins = Record<string, string>
export const pinChanges = (before: Pins, now: Pins): { changed: string[]; added: string[] } => ({
  changed: Object.keys(now).filter(k => before[k] !== undefined && before[k] !== now[k]),
  added: Object.keys(now).filter(k => before[k] === undefined),
})

// ---------- /dash doctor ----------

/** Version string a >= b, numeric parts only. */
export const versionAtLeast = (a: string, b: string): boolean => {
  const pa = a.split(/[.-]/).map(Number)
  const pb = b.split(/[.-]/).map(Number)
  for (let i = 0; i < 3; i++) {
    const x = pa[i] ?? 0
    const y = pb[i] ?? 0
    if (x !== y) return x > y
  }
  return true
}
