// dash: one dashboard for the Revenantworks skills (owner 2026-10-08). A collector counts what
// happens (skill fires, failures, likely misroutes, tokens, meters, command and permission-prompt
// shapes), never text; renderers show it on the status line, in the /dash pane (text where no pane
// draws), in VS Code from feed.json, and as a mobile snapshot. A suggestion queue proposes, never
// builds. Every `$` use lives in this file; pure logic sits in *-logic.ts and lib/.
// Hook work is kept cheap: hooks push counts to memory; a timer writes them.
import type { EngineInterface, Register } from 'claude-code'

import {
  METER_EVERY_MS, commandShape, emptyHealth, emptyMisroute, gatewardenCounts, isRevertCommand, onEdit, onRevertCommand,
  onSkillFire, parseEvents, permissionShape, publishSnapshot, pruneEvents, purgeArgv, rollup, serializeEvents, sessionKey, skillKey,
  type DashEvent, type Feed, type Health, type MisrouteState, type Via,
} from './collector-logic'
import { featuresOf } from './lib/catalog'
import { applySwitchCommand } from './lib/commands'
import { parseShell, writeTargets } from './lib/shell'
import { isFeatureOn, isNetworkOn, isRecordingOn, parseSwitches, serializeSwitches, type Switches } from './lib/switches'
import { fnv1a, formatAge, isWindowsEnv, normPath, repoSlug } from './lib/util'
import { cacheHit, liveFromMeasure, liveFromMeterFile, meterFile, shouldWriteMeterFile, statusText, STALE_MS, type Live, type Usage } from './meters-logic'
import {
  RESEARCH_SKILL, bandLine as godotLine, ciFacts, comfyFrom, countsAsProof, floorDrop, godotRun, gutCounts, isGodotSource,
  judge, junitCounts, leaseLines, leasePath, lmsFrom, ollamaFrom, paletteTokens, parseLease, parseRoster, pinChanges,
  resolveBrand, versionAtLeast, type CiFacts, type Pins, type Proof, type Readings,
} from './panels-logic'
import { actOn, candidates, mergeSuggestions, parseSuggestions, pickNote, serializeSuggestions, type Suggestion } from './suggest-logic'
import {
  addTask, changesPrs, estimateFor, isRunActive, lastLineOf, matchLedgerRow, parseEstWall, parseLedger, parsePrList,
  parseTaskNotification, prChanges, prLine, reconcileFlags, recordDuration, runIdFromPath, sanitizeTaskHistory, settleTask, summariseLedger,
  taskSignature, taskStatusLines, tasksHeadline, visibleTasks,
  type LedgerRow, type PrRow, type TaskHistory, type TaskRecord,
} from './tasks-logic'
import {
  HELP, healthLines, linesText, metersLines, overviewLines, parseDashArgs, skillsLines, suggestLines,
  type Line, type View,
} from './view-logic'

const PLUGIN = 'dash'
const VERSION = '1.0.0'
const MIN_CLAUDE = '2.1.287'
const FLUSH_MS = 5 * 60_000

// ---------- module state (a hot reload starts it over; switches and the files stay) ----------
let dsSw: Switches = parseSwitches(null)
let dsInit: Promise<void> | null = null
let dsHome = ''
let dsCwd = ''
let dsRoot = ''
let dsSession = ''
let dsSKey = ''
let dsIsWin = false
let dsCaught = 0
/** Rows not yet written to events.jsonl. */
let dsBuffer: DashEvent[] = []
/** This session's rows: what the views read before the records yes. */
let dsMem: DashEvent[] = []
let dsMis: MisrouteState = emptyMisroute()
let dsLastSlash: { name: string; at: number } | null = null
const dsSkillLast: Record<string, number> = {}
let dsTurnSkill: string | null = null
let dsLastCost: number | null = null
let dsLastHit: number | null = null
let dsLive: Live | null = null
let dsLastMeterAt = 0
let dsCtxHigh = false
let dsListed = false
let dsFeed: Feed | null = null
let dsHealth: Health = emptyHealth()
let dsSuggest: Suggestion[] = []
let dsNoted = false
let dsNote: Suggestion | null = null
let dsNotes: string[] = []
let dsAskRecords = false
let dsAskedAsText = false
let dsView: View = 'overview'
let dsMeterWrittenAt: number | null = null
// tasks (F3, F3f, F3e)
let dsTasks: TaskRecord[] = []
let dsTaskHist: TaskHistory = {}
let dsLedgerPath: string | null = null
let dsLedgerRows: LedgerRow[] = []
let dsRunActive = false
// PRs (X5)
let dsPrs: PrRow[] = []
let dsPrAt = 0
// research (S4)
let dsResearch = false
let dsResearchIdle = 0
let dsLaunches = 0
let dsBrand: string | null = null
// GPU (L1)
let dsReadings: Readings | null = null
let dsLeaseFile = ''
// Godot (G1)
let dsGodot = false
let dsCi: CiFacts | null = null
let dsProof: Proof | null = null
let dsImported = false
let dsEditedSinceImport = false
let dsImportWarned = false
// pins (C14)
let dsPinsChanged = 0

function dsOn(id: string): boolean {
  return isFeatureOn(dsSw, id)
}

function dsRecording(): boolean {
  return isRecordingOn(dsSw, 'D1')
}

function dsPath(name: string): string {
  return `${dsHome}/.claude/revenantworks/${name}`
}

function dsRel(path: string): string {
  const p = normPath(path)
  const root = normPath(dsRoot || dsCwd).replace(/\/$/, '')
  return p.startsWith(`${root}/`) ? p.slice(root.length + 1) : p
}

async function dsRead($: EngineInterface, path: string): Promise<string | null> {
  try {
    return await $.fs.read(path)
  } catch {
    return null
  }
}

async function dsWrite($: EngineInterface, path: string, text: string): Promise<void> {
  try {
    await $.fs.write(path, text)
  } catch {
    // Observe-only writes never block the person's work.
  }
}

async function dsCanDraw($: EngineInterface): Promise<boolean> {
  const s = await $.session.surfaces()
  return s.includes('terminal') || s.includes('desktop')
}

async function dsSay($: EngineInterface, text: string): Promise<void> {
  if (await dsCanDraw($)) $.ui.toast(text)
  else dsNotes.push(text)
}

/** Keep a row: counts only, through the one door. Cheap: memory now, the file on the next flush. */
function dsPush(e: DashEvent): void {
  if (!dsOn('D1') && !dsOn('D3') && !dsOn('D5')) return
  dsMem = [...dsMem, e].slice(-5000)
  if (dsRecording()) dsBuffer = [...dsBuffer, e].slice(-5000)
}

async function dsLoadSwitches($: EngineInterface): Promise<void> {
  dsSw = parseSwitches(await dsRead($, dsPath('switches.json')))
}

async function dsSaveSwitches($: EngineInterface, sw: Switches): Promise<void> {
  dsSw = sw
  await $.fs.write(dsPath('switches.json'), serializeSwitches(sw))
}

async function dsHeartbeat($: EngineInterface): Promise<void> {
  const on = featuresOf('dash').filter(x => dsOn(x.id)).map(x => x.id)
  await dsWrite($, dsPath(`health/${PLUGIN}.json`), JSON.stringify({ plugin: PLUGIN, version: VERSION, session: fnv1a(dsSession), at: await $.clock.now(), on, caught: dsCaught }))
}

/** Writes the buffered rows to events.jsonl (records only), pruned to 30 days. */
async function dsFlush($: EngineInterface): Promise<DashEvent[]> {
  const now = await $.clock.now()
  if (!dsRecording()) {
    dsBuffer = []
    return dsMem
  }
  const file = dsPath('dash/events.jsonl')
  const events = pruneEvents([...parseEvents(await dsRead($, file)), ...dsBuffer], now)
  dsBuffer = []
  await dsWrite($, file, serializeEvents(events))
  return events
}

/** Health: heartbeats, hook drift (when asked), gatewarden's counts, pins. */
async function dsHealthNow($: EngineInterface, full: boolean): Promise<Health> {
  const now = await $.clock.now()
  const plugins: Health['plugins'] = {}
  for (const p of ['dash', 'privacy']) {
    const text = await dsRead($, dsPath(`health/${p}.json`))
    try {
      const b = JSON.parse(text ?? '') as { session?: string; at?: number; version?: string; caught?: number }
      plugins[p] = { loaded: b.session === fnv1a(dsSession) && now - (b.at ?? 0) < 10 * 60_000, at: b.at ?? null, version: b.version ?? null, caught: b.caught ?? 0 }
    } catch {
      plugins[p] = { loaded: false, at: null, version: null, caught: 0 }
    }
  }
  plugins.dash = { loaded: true, at: now, version: VERSION, caught: dsCaught }
  let drift = dsHealth.drift
  if (full) {
    drift = []
    if (dsRoot) {
      try {
        for (const e of (await $.fs.list(`${dsRoot}/.claude/hooks`)).filter(x => x.kind === 'file' && /\.(py|sh|ps1)$/.test(x.name)).slice(0, 40)) {
          const repo = await dsRead($, `${dsRoot}/.claude/hooks/${e.name}`)
          const live = await dsRead($, `${dsHome}/.claude/hooks/${e.name}`)
          drift.push({ hook: e.name, state: live === null ? 'not installed' : repo === live ? 'same' : 'differs' })
        }
      } catch {
        // No .claude/hooks in this repo.
      }
    }
  }
  const gwPath = ((await $.env.get('GATEWARDEN_EVENTS')) ?? `${dsHome}/.claude/gatewarden/events.jsonl`).replace(/\\/g, '/')
  const gatewarden = gatewardenCounts(await dsRead($, gwPath), now)
  dsHealth = { plugins, drift, gatewarden, pinsChanged: dsPinsChanged }
  return dsHealth
}

/** Flush, then fold into feed.json and the suggestion queue. Files only with the records yes. */
async function dsRoll($: EngineInterface, full = false): Promise<Feed> {
  const now = await $.clock.now()
  const events = await dsFlush($)
  const health = await dsHealthNow($, full)
  let feed = rollup(events, { now, recording: dsRecording(), health })
  if (dsOn('D5')) {
    dsSuggest = mergeSuggestions(dsSuggest, candidates(events, feed, now), now)
    feed = { ...feed, suggestionsNew: dsSuggest.filter(r => r.state === 'new').length }
  }
  dsFeed = feed
  if (dsRecording()) {
    await dsWrite($, dsPath('dash/feed.json'), `${JSON.stringify(feed, null, 2)}\n`)
    if (dsOn('D5')) await dsWrite($, dsPath('dash/suggestions.json'), serializeSuggestions(dsSuggest, now))
  }
  return feed
}

async function dsFindLedger($: EngineInterface): Promise<void> {
  dsLedgerPath = null
  dsLedgerRows = []
  const candidatesList: string[] = []
  const env = await $.env.get('CLAUDE_DISPATCH_LEDGER')
  if (env) candidatesList.push(env)
  const pointer = await dsRead($, `${dsCwd}/.dispatch/ledger-path`)
  if (pointer) candidatesList.push(pointer.trim())
  try {
    const runs = await $.fs.list(`${dsCwd}/.dispatch/runs`)
    const newest = [...runs].filter(r => r.kind === 'dir').sort((a, b) => b.mtimeMs - a.mtimeMs)[0]
    if (newest) candidatesList.push(`${dsCwd}/.dispatch/runs/${newest.name}/ledger.md`, `${dsCwd}/.dispatch/runs/${newest.name}/ledger.csv`)
  } catch {
    // No run folder here.
  }
  for (const c of candidatesList) {
    const text = await dsRead($, c)
    if (text) {
      dsLedgerPath = c
      dsLedgerRows = parseLedger(c, text)
      return
    }
  }
}

async function dsRefreshRun($: EngineInterface): Promise<void> {
  await dsFindLedger($)
  const flag = await dsRead($, `${dsHome}/.claude/dispatch-mode.json`)
  dsRunActive = isRunActive(flag ?? undefined, await $.clock.now()) && dsLedgerPath !== null
}

function dsLedgerLine(): string | null {
  return dsLedgerPath ? summariseLedger(runIdFromPath(dsLedgerPath), dsLedgerRows).line : null
}

/** F3f: every background task: what it is, who started it, how long, an estimate and its last output. */
async function dsTaskText($: EngineInterface): Promise<string> {
  const now = await $.clock.now()
  try {
    for (const a of await $.agent.list()) {
      const state = a.status === 'completed' ? 'completed' : a.status === 'failed' ? 'failed' : a.status === 'killed' ? 'killed' : 'running'
      const known = dsTasks.find(t => t.id === a.id)
      if (known) {
        if (known.state === 'running' && state !== 'running') dsTasks = settleTask(dsTasks, a.id, state, now)
        continue
      }
      dsTasks = addTask(dsTasks, { id: a.id, kind: 'agent', label: a.description.slice(0, 60), group: a.parentId ? 'subagent' : 'main', startedAt: now, state, detail: `${a.type}: ${a.description}`, sig: taskSignature('agent', a.description) })
    }
  } catch {
    // No agent list on this host: tasks seen through tool calls still show.
  }
  const head = tasksHeadline(dsTasks, dsLedgerLine() ?? 'no dispatch ledger here')
  const shown = dsTasks.filter(t => t.state === 'running' || now - (t.endedAt ?? now) < 10 * 60_000)
  const blocks: string[] = []
  for (const t of shown) {
    const row = matchLedgerRow(dsLedgerRows, [t.label, t.detail ?? ''])
    let progress = null
    if (t.outputFile) {
      try {
        const st = await $.fs.stat(t.outputFile)
        const text = st.size < 1_000_000 ? await dsRead($, t.outputFile) : null
        progress = { lastLine: text ? lastLineOf(text) : null, idleMs: now - st.mtimeMs, bytes: st.size }
      } catch {
        progress = null
      }
    }
    blocks.push(taskStatusLines(t, now, estimateFor(t.sig, dsTaskHist, parseEstWall(row?.estWall), t.timeoutMs), progress).join('\n'))
  }
  return [head, ...(blocks.length ? blocks : ['No background tasks are running, and none finished in the last 10 minutes.'])].join('\n\n')
}

async function dsRefreshPrs($: EngineInterface): Promise<void> {
  if (!isNetworkOn(dsSw, 'D12')) return
  dsPrAt = await $.clock.now()
  try {
    const r = await $.process.run(['gh', 'pr', 'list', '--author', '@me', '--json', 'number,title,state,mergeStateStatus,reviewDecision,statusCheckRollup', '--limit', '10'], { cwd: dsCwd, timeoutMs: 15000 })
    if (r.exitCode !== 0) return
    const rows = parsePrList(r.stdout)
    const changes = prChanges(dsPrs, rows)
    dsPrs = rows
    if (changes.length > 0) await dsSay($, `PRs: ${changes.join(' · ')}`)
  } catch {
    // gh missing or offline: the PR line shows its age instead.
  }
}

async function dsFetch($: EngineInterface, url: string): Promise<string | null> {
  try {
    // A filtered port can hang; a reading that does not come back in 2 s counts as no answer.
    const timeout = $.clock.sleep(2000).then(() => null)
    const r = await Promise.race([$.http.fetch(url), timeout])
    return r && r.ok ? r.text : null
  } catch {
    return null
  }
}

/** D10: reads 127.0.0.1 only, and only when the person asks (/dash gpu). */
async function dsPollGpu($: EngineInterface): Promise<void> {
  const stats = await dsFetch($, 'http://127.0.0.1:8188/system_stats')
  const queue = await dsFetch($, 'http://127.0.0.1:8188/queue')
  const lms = await dsFetch($, 'http://127.0.0.1:1234/api/v1/models')
  const ollama = await dsFetch($, 'http://127.0.0.1:11434/api/ps')
  dsReadings = { comfy: comfyFrom(stats, queue), lms: lmsFrom(lms), ollama: ollamaFrom(ollama), at: await $.clock.now() }
}

async function dsPaletteLines($: EngineInterface): Promise<string[]> {
  const roster = dsRoot ? await dsRead($, `${dsRoot}/brands/roster.md`) : null
  if (!roster) return ['No brands/roster.md here; brandscribe asks which brand before any work.']
  const r = resolveBrand(parseRoster(roster), dsBrand, repoSlug(dsRoot || dsCwd), dsRel(dsCwd))
  if (!r.slug) return ['Brand: not resolved here (named, then scoped, then ask). brandscribe asks which one.']
  const md = await dsRead($, `${dsRoot}/brands/${r.slug}/brand.md`)
  const toks = md ? paletteTokens(md) : []
  return [`Brand ${r.slug} (${r.how}): ${toks.length} palette token(s)`, ...toks.map(t => `  ${t.token.padEnd(22)} ${t.hex}`)]
}

function dsGodotLines(now: number): string[] {
  return [
    godotLine(dsProof, now),
    `CI: ${dsCi ? `${dsCi.commands.length} godot step(s)${dsCi.floor ? `, floor ${dsCi.floor}` : ''}${dsCi.scripts ? `, ${dsCi.scripts} scripts expected` : ''}` : 'no Godot workflow found'}`,
    ...(dsCi?.commands ?? []).map(c => `  step: ${c.slice(0, 100)}`),
    `Import: ${dsImported ? (dsEditedSinceImport ? 'assets or scripts changed since the last import' : 'current') : 'not run this session and no .godot/imported'}`,
  ]
}

async function dsLoadCi($: EngineInterface): Promise<void> {
  dsCi = null
  try {
    for (const f of (await $.fs.list(`${dsRoot}/.github/workflows`)).filter(x => /\.ya?ml$/.test(x.name))) {
      const text = await dsRead($, `${dsRoot}/.github/workflows/${f.name}`)
      if (text && /\bgodot\b/.test(text)) {
        dsCi = ciFacts(text)
        return
      }
    }
  } catch {
    // No workflows: the panel shows "no CI floor found".
  }
}

/** The optional panels' one-liners for the overview, each only where it applies. */
async function dsPanelLines($: EngineInterface): Promise<string[]> {
  const now = await $.clock.now()
  const out: string[] = []
  if (dsOn('D9') && dsResearch) out.push(`research: ${dsLaunches} agent(s) launched · 5h ${dsLive?.five === null || dsLive?.five === undefined ? '?' : `${Math.round(dsLive.five)}%`}`)
  if (dsOn('D11') && dsGodot) out.push(godotLine(dsProof, now))
  if (dsOn('D10') && dsLeaseFile) {
    const lease = parseLease(await dsRead($, dsLeaseFile))
    if (lease) out.push(leaseLines(lease, null, now)[0] ?? '')
  }
  if (isNetworkOn(dsSw, 'D12') && dsPrs.length > 0) out.push(`PRs (${formatAge(now - dsPrAt)} ago): ${prLine(dsPrs)}`)
  return out
}

async function dsLines($: EngineInterface, view: View): Promise<Line[]> {
  const now = await $.clock.now()
  const feed = dsFeed ?? (await dsRoll($))
  const live = dsLive && now - dsLive.at <= STALE_MS ? dsLive : liveFromMeterFile(await dsRead($, ((await $.env.get('CLAUDE_USAGE_WINDOWS')) ?? `${dsHome}/.claude/usage-windows.json`).replace(/\\/g, '/'))) ?? dsLive
  const text = (xs: string[]): Line[] => xs.map(t => ({ text: t }))
  switch (view) {
    case 'skills': return skillsLines(feed)
    case 'meters': return metersLines(live, feed, now)
    case 'health': return healthLines(feed.health)
    case 'tasks': return text((await dsTaskText($)).split('\n'))
    case 'suggest': return suggestLines(dsSuggest)
    case 'gpu': return text(leaseLines(parseLease(await dsRead($, dsLeaseFile)), dsReadings, now))
    case 'palette': return text(await dsPaletteLines($))
    case 'godot': return text(dsGodot ? dsGodotLines(now) : ['No project.godot here; the Godot panel is for Godot projects.'])
    case 'prs': return text([isNetworkOn(dsSw, 'D12') ? prLine(dsPrs) : 'PR state is off, so nothing was read from GitHub. /dash network on turns it on.'])
    case 'context': {
      try {
        const u = await $.session.usage({ breakdown: 'summary' })
        const b = u.context.breakdown
        if (!b) return text(['No breakdown yet: it is taken after the first answer.'])
        return text([
          `Context ${Math.round(b.totalTokens / 1000)}k of ${Math.round((b.rawMaxTokens || b.maxTokens) / 1000)}k (${Math.round(b.percentage)}%)`,
          ...[...b.categories].sort((x, y) => y.tokens - x.tokens).slice(0, 12).map(c => `  ${c.name.padEnd(24).slice(0, 24)} ${Math.round(c.tokens / 100) / 10}k`),
        ])
      } catch {
        return text(['No context breakdown on this host.'])
      }
    }
    default: {
      const tl = visibleTasks(dsTasks, now).length || dsLedgerPath ? tasksHeadline(dsTasks, dsLedgerLine()) : null
      return overviewLines({ live, feed, now, tasksLine: tl, panels: await dsPanelLines($) })
    }
  }
}

async function dsDoctor($: EngineInterface): Promise<string> {
  const v = await $.session.version()
  const lines = ['/dash doctor', `  Claude Code ${v.version}: ${versionAtLeast(v.version, MIN_CLAUDE) ? 'OK' : `needs ${MIN_CLAUDE} or newer for mods`}`]
  const surfaces = await $.session.surfaces()
  lines.push(`  Surface: ${surfaces.join(', ') || 'none reported'}. ${surfaces.includes('terminal') || surfaces.includes('desktop') ? 'The /dash pane draws here.' : 'Text only here; in VS Code the dash extension (mods/vscode) shows the status bar item and the panel.'}`)
  lines.push(`  Switch file: ${(await $.fs.exists(dsPath('switches.json'))) ? 'present' : 'not written yet (shipped defaults)'}; kill switch ${dsSw.off ? 'ON' : 'off'}`)
  lines.push(`  Collector: ${dsRecording() ? 'writing counts to ~/.claude/revenantworks/dash/' : 'this session only (/dash records on keeps counts)'}`)
  const now = await $.clock.now()
  for (const [label, path] of [['meter file', `${dsHome}/.claude/usage-windows.json`], ['feed', dsPath('dash/feed.json')]] as const) {
    try {
      lines.push(`  ${label}: ${formatAge(now - (await $.fs.stat(path)).mtimeMs)} old`)
    } catch {
      lines.push(`  ${label}: absent`)
    }
  }
  lines.push(...healthLines(await dsHealthNow($, true)).map(l => `  ${l.text}`))
  return lines.join('\n')
}

async function dsPurge($: EngineInterface): Promise<string> {
  for (const key of await $.store.keys()) await $.store.delete(key)
  const dir = dsPath('dash')
  const argv = purgeArgv(dsIsWin, dir)
  if (!argv) return `Refused to run a remove command on ${dir}: the path is not the dash folder or holds a shell character. Delete it by hand.`
  try {
    const r = await $.process.run(argv, { timeoutMs: 10000 })
    dsMem = []
    dsBuffer = []
    dsSuggest = []
    dsFeed = null
    return r.exitCode === 0 ? `Removed ${dir}. The switch file stays; /dash records off stops new counts.` : `Could not remove ${dir} (exit ${r.exitCode}). Delete it by hand.`
  } catch {
    return `Could not run the remove command. Delete ${dir} by hand.`
  }
}

async function dsEnsure($: EngineInterface): Promise<void> {
  // A failed setup is retried by the next hook instead of being cached for the whole session.
  if (!dsInit) dsInit = dsSetup($).catch(err => { dsInit = null; throw err })
  await dsInit
}

async function dsSetup($: EngineInterface): Promise<void> {
  dsIsWin = isWindowsEnv(await $.env.get('OS'))
  dsHome = ((dsIsWin ? (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) : (await $.env.get('HOME')) ?? (await $.env.get('USERPROFILE'))) ?? '').replace(/\\/g, '/')
  dsSession = await $.session.id()
  dsSKey = sessionKey(dsSession)
  dsCwd = (await $.session.cwd()).replace(/\\/g, '/')
  dsRoot = ((await $.session.repo())?.root ?? '').replace(/\\/g, '/')
  dsLeaseFile = leasePath(dsIsWin, { LOCALAPPDATA: await $.env.get('LOCALAPPDATA'), XDG_STATE_HOME: await $.env.get('XDG_STATE_HOME'), HOME: dsHome })
  await dsLoadSwitches($)
  dsSuggest = parseSuggestions(await dsRead($, dsPath('dash/suggestions.json')))
  // Hash keys only: text keys left by an older build are dropped on read and never written back.
  dsTaskHist = sanitizeTaskHistory(await $.store.get('taskHistory'))
  try {
    await $.command.register({ name: 'dash', description: 'dash: skills, meters, health and suggestions in one view', argumentHint: 'skills · meters · health · tasks · suggest · publish · switches · help' })
  } catch {
    // A name the host refuses is skipped; setup goes on.
  }
  if (dsOn('D4')) {
    try {
      await $.tool.register({
        name: 'dash_read',
        description: 'Read the dash feed on demand: skills fired (slash or automatic), failures, likely misroutes, tokens by skill, the 5-hour and weekly meters, context, cache, background tasks, health and the suggestion queue. Read-only; counts only, never text.',
        inputSchema: { type: 'object', properties: { view: { type: 'string', enum: ['overview', 'skills', 'meters', 'health', 'tasks', 'suggest'] } } },
      })
    } catch {
      // A name the host refuses is skipped; setup goes on.
    }
  }
  const root = dsRoot || dsCwd
  dsGodot = await $.fs.exists(`${root}/project.godot`).catch(() => false)
  if (dsGodot && dsOn('D11')) {
    await dsLoadCi($)
    dsImported = await $.fs.exists(`${root}/.godot/imported`).catch(() => false)
  }
  dsAskRecords = !dsSw.off && (await $.store.get('recordsAnswered')) !== true && dsSw.features.D1 === undefined
  dsPush({ t: await $.clock.now(), s: dsSKey, k: 'session' })
  await dsRefreshRun($)
  await dsHeartbeat($)
  $.clock.every(60_000, async () => {
    await dsLoadSwitches($)
    await dsHeartbeat($)
  })
  $.clock.every(FLUSH_MS, async () => {
    await dsRoll($)
  })
}

function dsShell(e: { tool: string }): { command: string; shell: 'sh' | 'ps' } | null {
  const command = (e as { command?: unknown }).command
  if (typeof command !== 'string') return null
  if (e.tool === 'Bash') return { command, shell: 'sh' }
  if ((e.tool as string) === 'PowerShell') return { command, shell: 'ps' }
  return null
}

/** The switch file changes only through /dash, which the person types (C2). */
function dsWritesSwitchFile(command: string, shell: 'sh' | 'ps'): boolean {
  const parsed = parseShell(command, shell)
  if (parsed.commands.some(c => writeTargets(c).some(t => /revenantworks[\\/]switches\.json$/i.test(t)))) return true
  return /revenantworks[\\/]switches\.json/i.test(command) && parsed.commands.some(c => c.prog && !/^(cat|type|get-content|gc|less|more|head|tail|grep|rg|jq|ls|dir|stat|test-path|wc|diff)$/.test(c.prog))
}

async function dsSkillFired($: EngineInterface, skill: string, via: Via): Promise<void> {
  const now = await $.clock.now()
  const name = skillKey(skill)
  if (dsSkillLast[name] !== undefined && now - dsSkillLast[name]! < 5000) return
  dsSkillLast[name] = now
  dsPush({ t: now, s: dsSKey, k: 'skill', skill: name, via })
  const r = onSkillFire(dsMis, name, via, now)
  dsMis = r.st
  if (r.misroute) dsPush({ t: now, s: dsSKey, k: 'misroute', skill: r.misroute, why: 'switch' })
  dsTurnSkill = name
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await dsEnsure($)
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await dsEnsure($)
    const now = await $.clock.now()
    dsLive = liveFromMeasure(e.rateLimits, e.context.percent, e.cost?.usd ?? null, dsLastHit, now)
    if (dsOn('D2') && (await dsCanDraw($))) $.ui.status(statusText(dsLive, now))
    const ctx = e.context.percent ?? null
    if (ctx !== null) {
      if (ctx >= 80 && !dsCtxHigh) dsPush({ t: now, s: dsSKey, k: 'ctx80' })
      dsCtxHigh = ctx >= 80
    }
    if (now - dsLastMeterAt >= METER_EVERY_MS && (dsLive.five !== null || dsLive.week !== null || ctx !== null)) {
      dsLastMeterAt = now
      dsPush({ t: now, s: dsSKey, k: 'meter', five: dsLive.five, week: dsLive.week, weekReset: dsLive.weekResetMs, ctx })
    }
    // D6: pacewright's meter file, only when no other writer keeps it fresh.
    if (isRecordingOn(dsSw, 'D6') && e.rateLimits.length > 0) {
      const meterPath = ((await $.env.get('CLAUDE_USAGE_WINDOWS')) ?? `${dsHome}/.claude/usage-windows.json`).replace(/\\/g, '/')
      let mtime: number | null = null
      try {
        mtime = (await $.fs.stat(meterPath)).mtimeMs
      } catch {
        mtime = null
      }
      if (shouldWriteMeterFile(mtime, dsMeterWrittenAt, now)) {
        const file = meterFile(e.rateLimits, ctx, (await $.session.model()) ?? null, now)
        if (file) {
          await dsWrite($, meterPath, JSON.stringify(file))
          dsMeterWrittenAt = now
        }
      }
    }
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    await dsEnsure($)
    const kind = e.origin?.kind
    const now = await $.clock.now()
    if (kind === 'task-notification') {
      const n = parseTaskNotification(e.text)
      if (n) {
        const t = dsTasks.find(x => x.id === n.id)
        dsTasks = settleTask(dsTasks, n.id, n.status, now)
        if (t?.sig && n.status === 'completed') {
          dsTaskHist = recordDuration(dsTaskHist, t.sig, now - t.startedAt)
          if (dsRecording()) await $.store.set('taskHistory', dsTaskHist)
        }
      }
    }
    if (kind === 'composer' || kind === 'bridge') {
      // Only the name a typed /name carries is kept, to tell a slash fire from an automatic one.
      const m = /^\/([A-Za-z0-9][\w:.-]*)/.exec(e.text.trimStart())
      dsLastSlash = m ? { name: m[1]!, at: now } : null
      dsTurnSkill = null
      if (dsResearch) {
        dsResearchIdle = /\b(research|source|route|agents?|size|fan.?out|run|workflow)\b/i.test(e.text) ? 0 : dsResearchIdle + 1
        if (dsResearchIdle >= 2) dsResearch = false
      }
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('skill.prompt', async ($, e, next) => {
    await dsEnsure($)
    const now = await $.clock.now()
    const slash = dsLastSlash && now - dsLastSlash.at < 30_000 && (dsLastSlash.name === e.skill || e.skill.endsWith(`:${dsLastSlash.name}`) || e.skill.endsWith(`-${dsLastSlash.name}`))
    await dsSkillFired($, e.skill, slash ? 'slash' : 'auto')
    if (dsOn('D9') && RESEARCH_SKILL.test(e.skill)) {
      dsResearch = true
      dsLaunches = 0
      dsResearchIdle = 0
    }
    return next(e)
  }).catch(($, e, next) => {
    dsCaught += 1
    return next(e)
  })

  on('agent.spawn', async ($, e, next) => {
    await dsEnsure($)
    if (dsResearch && e.subagentType !== 'fork') dsLaunches += 1
    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.check', async ($, e, next) => {
    const res = await next(e)
    if (res.decision === 'ask') {
      await dsEnsure($)
      const shape = permissionShape(e.tool, e.input as Record<string, unknown> | undefined)
      if (shape) dsPush({ t: await $.clock.now(), s: dsSKey, k: 'perm', shape })
    }
    return res
  }).catch(($, e, next) => next(e))

  on('tool.call', async ($, e, next) => {
    await dsEnsure($)
    if (e.tool === 'mcp__dash__dash_read') {
      if (!dsOn('D4')) return { deny: 'dash_read is switched off (/dash on read-tool).' }
      const view = String((e as { view?: unknown }).view ?? 'overview') as View
      await dsRoll($)
      // An MCP tool result is a string or content blocks; a { text } object fails the host's output check.
      return { result: linesText(await dsLines($, ['overview', 'skills', 'meters', 'health', 'tasks', 'suggest'].includes(view) ? view : 'overview')) }
    }
    const shell = dsShell(e)
    const filePath = typeof (e as { file_path?: unknown }).file_path === 'string' ? (e as { file_path: string }).file_path : null
    // C2: the switch file holds the person's choices; it changes only through /dash, which they type.
    if ((e.tool === 'Edit' || e.tool === 'Write') && filePath && /revenantworks[\\/]switches\.json$/i.test(filePath)) {
      return { deny: 'dash: the mods switch file changes only through /dash, which you type.' }
    }
    if (shell && dsWritesSwitchFile(shell.command, shell.shell)) {
      return { deny: 'dash: this would write the mods switch file; it changes only through /dash, which you type.' }
    }
    const now = await $.clock.now()
    const kind = shell && dsOn('D11') && dsGodot ? godotRun(shell.command, shell.shell, dsCi?.gdir ?? null) : null
    if (kind?.test) {
      dsProof = { status: 'Running', at: now, counts: dsProof?.counts ?? null, why: 'running' }
      if ((!dsImported || dsEditedSinceImport) && !dsImportWarned) {
        dsImportWarned = true
        dsNotes.push('Run godot --headless --import before the tests: new or changed assets are not imported yet, and the run can fail for that alone.')
      }
    }
    const workflowBefore = filePath && dsGodot && /(^|\/)\.github\/workflows\/[^/]+\.ya?ml$/.test(dsRel(filePath)) && (e.tool === 'Edit' || e.tool === 'Write') ? await dsRead($, filePath) : null

    const ran = await next(e)
    const ok = ran.deny === undefined && ran.isError !== true

    // Collector: shapes and hashes only.
    if (e.tool === 'Skill') {
      const skill = (e as { skill?: unknown }).skill
      if (typeof skill === 'string' && !ok) dsPush({ t: now, s: dsSKey, k: 'skill_fail', skill })
    }
    if (shell) {
      const shape = commandShape(shell.command, shell.shell)
      if (shape) dsPush({ t: now, s: dsSKey, k: 'cmd', shape })
      if (ok && isRevertCommand(shell.command)) {
        const r = onRevertCommand(dsMis, now)
        dsMis = r.st
        if (r.misroute) dsPush({ t: now, s: dsSKey, k: 'misroute', skill: r.misroute, why: 'revert' })
      }
      if (ok && isNetworkOn(dsSw, 'D12') && changesPrs(shell.command)) await dsRefreshPrs($)
    }
    if (e.tool === 'Edit' && filePath && ok) {
      const r = onEdit(dsMis, fnv1a(normPath(filePath)), fnv1a(e.old_string), fnv1a(e.new_string), now)
      dsMis = r.st
      if (r.misroute) dsPush({ t: now, s: dsSKey, k: 'misroute', skill: r.misroute, why: 'revert' })
    }
    // F3, F3f: background tasks and agents.
    if (ok) {
      const result = (ran.result ?? {}) as Record<string, unknown>
      const id = (result.backgroundTaskId ?? result.taskId ?? (result.status === 'async_launched' ? result.agentId : undefined)) as string | undefined
      if (id) {
        const tk = e.tool === 'Agent' ? 'agent' : e.tool === 'Monitor' ? 'monitor' : 'bash'
        const label = String((e as { description?: unknown }).description ?? shell?.command ?? e.tool).slice(0, 60)
        const detail = shell?.command ?? `${String((e as { subagent_type?: unknown }).subagent_type ?? 'agent')}: ${String((e as { prompt?: unknown }).prompt ?? label).slice(0, 200)}`
        const timeout = (e as { timeout?: unknown }).timeout
        dsTasks = addTask(dsTasks, {
          id, kind: tk, label, group: e.agentId ? 'subagent' : 'main', startedAt: now, state: 'running', detail, sig: taskSignature(tk, shell?.command ?? label),
          ...(typeof timeout === 'number' ? { timeoutMs: timeout } : {}),
          ...(typeof result.outputFile === 'string' ? { outputFile: result.outputFile } : {}),
        })
      }
      if (e.tool === 'TaskStop') {
        const stopId = (e as { task_id?: unknown }).task_id
        if (typeof stopId === 'string') dsTasks = settleTask(dsTasks, stopId, 'killed', now)
      }
    }
    // D11: the Godot proof, stale on any later change to Godot source.
    if (dsGodot && dsOn('D11')) {
      if (kind?.import && ran.deny === undefined) {
        dsImported = true
        dsEditedSinceImport = false
      }
      if (kind?.test && shell) {
        const out = JSON.stringify(ran.result ?? '').replace(/\\n/g, '\n')
        const benign = ((await dsRead($, `${dsRoot || dsCwd}/ci/benign-errors.txt`)) ?? '').split('\n').filter(Boolean)
        let counts = gutCounts(out, benign)
        if (counts.tests === null) {
          const xmlPath = shell.command.match(/-gjunit_xml_file=(\S+)/)?.[1]
          const xml = xmlPath ? await dsRead($, xmlPath.startsWith('res://') ? `${dsRoot || dsCwd}/${xmlPath.slice(6)}` : xmlPath) : null
          counts = (xml && junitCounts(xml)) || counts
        }
        const exitOk = ok && !/"exit_?code"\s*:\s*[1-9]/.test(out)
        dsProof = judge(exitOk, kind.whole, countsAsProof(shell.command), counts, dsCi, await $.clock.now())
      }
      if (shell && ran.deny === undefined && dsProof && (dsProof.status === 'Passed' || dsProof.status === 'Failed')) {
        const parsed = parseShell(shell.command, shell.shell)
        const touched = parsed.commands.flatMap(c => [...writeTargets(c), ...(c.prog === 'git' && /^(checkout|restore|reset|stash|merge|pull|rebase|apply)$/.test(c.argv[1] ?? '') ? ['*.gd'] : [])])
        const hit = touched.find(t => t === '*.gd' || isGodotSource(dsRel(t)))
        if (hit) dsProof = { ...dsProof, status: 'Stale', why: `${hit === '*.gd' ? 'a git command' : dsRel(hit)} changed source after the run` }
      }
      if (filePath && (e.tool === 'Edit' || e.tool === 'Write') && ran.deny === undefined) {
        const rel = dsRel(filePath)
        if (isGodotSource(rel)) {
          dsEditedSinceImport = true
          if (dsProof && (dsProof.status === 'Passed' || dsProof.status === 'Failed')) dsProof = { ...dsProof, status: 'Stale', why: `${rel} changed after the run` }
        }
        if (workflowBefore !== null) {
          const after = await dsRead($, filePath)
          const drop = after ? floorDrop(workflowBefore, after) : null
          if (drop) dsNotes.push(drop)
          await dsLoadCi($)
        }
      }
    }
    return ran
  }).catch(($, e, next) => {
    dsCaught += 1
    return next(e)
  })

  // D8: instruction files that changed since they last loaded (hashes only, after its own yes).
  on('prompt.context', async ($, e, next) => {
    await dsEnsure($)
    if (isRecordingOn(dsSw, 'D8') && e.instructionFiles) {
      const now: Pins = {}
      for (const f of e.instructionFiles) now[fnv1a(normPath(f.path))] = fnv1a(f.content)
      const before = ((await $.store.get('pins')) as Pins | undefined) ?? {}
      dsPinsChanged = pinChanges(before, now).changed.length
      await $.store.set('pins', { ...before, ...now })
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    await dsEnsure($)
    const now = await $.clock.now()
    if (e.usage) {
      const u = e.usage as unknown as Usage
      if (!e.agentId) {
        dsLastHit = cacheHit(u)
        if (dsLive) dsLive = { ...dsLive, cacheHit: dsLastHit }
      }
      const cost = dsLive?.costUsd ?? null
      const delta = !e.agentId && cost !== null && dsLastCost !== null ? cost - dsLastCost : null
      if (!e.agentId) dsLastCost = cost
      dsPush({ t: now, s: dsSKey, k: 'turn', skill: e.agentId ? null : dsTurnSkill, input: u.input_tokens, output: u.output_tokens, cacheRead: u.cache_read_input_tokens, cacheWrite: u.cache_creation_input_tokens, cost: delta })
      // D7: the ledger's cost sidecar during an active dispatch run (after its own yes).
      if (!e.agentId && isRecordingOn(dsSw, 'D7') && dsRunActive && dsLedgerPath) {
        const dir = dsLedgerPath.replace(/[^/]+$/, '')
        const before = (await dsRead($, `${dir}actuals.jsonl`)) ?? ''
        const line = JSON.stringify({ ts: new Date(now).toISOString(), turn: e.turnId, tokens: u.input_tokens + u.output_tokens, five_hour_pct: dsLive?.five ?? null })
        await dsWrite($, `${dir}actuals.jsonl`, `${`${before}${line}\n`.split('\n').filter(Boolean).slice(-2000).join('\n')}\n`)
        const unverified = reconcileFlags(dsLedgerRows, () => true)
        if (unverified.length > 0) dsNotes.push(`Ledger rows marked done without a sha on origin: ${unverified.join(', ')}. Reconcile them (dispatchwright).`)
      }
    }
    if (!e.agentId && !dsListed) {
      // Skills enabled: the listing's names, once a session.
      dsListed = true
      try {
        const b = (await $.session.usage({ breakdown: 'summary' })).context.breakdown
        const names = b?.skills?.skillFrontmatter.map(s => s.name) ?? []
        if (names.length) dsPush({ t: now, s: dsSKey, k: 'listed', skills: names })
      } catch {
        // No listing on this host: skills show once they fire.
      }
    }
    const res = await next(e)
    if (e.agentId) return res
    dsTurnSkill = null
    // At most one suggestion note a session.
    if (dsOn('D5') && !dsNoted) {
      if (!dsFeed) await dsRoll($)
      const p = pickNote(dsSuggest, dsNoted, now)
      if (p.note) {
        dsSuggest = p.rows
        dsNoted = true
        dsNote = p.note
        if (dsRecording()) await dsWrite($, dsPath('dash/suggestions.json'), serializeSuggestions(dsSuggest, now))
        if (!(await dsCanDraw($))) dsNotes.push(`dash suggests: ${p.note.title} (${p.note.evidence}). /dash suggest to accept, dismiss or snooze.`)
      }
    }
    if (dsAskRecords && !dsAskedAsText && !(await dsCanDraw($))) {
      dsAskedAsText = true
      dsNotes.push('dash keeps counts for this session only until you say yes: /dash records on keeps them across sessions (counts, never text); /dash records off stops asking.')
    }
    if (dsNotes.length > 0) {
      const notes = [...new Set(dsNotes.splice(0))]
      if (await dsCanDraw($)) {
        for (const n of notes.slice(0, 2)) $.ui.toast(n)
        return res
      }
      return { ...res, text: [res.text, ...notes].filter(Boolean).join('\n') }
    }
    return res
  }).catch(($, e, next) => {
    dsCaught += 1
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    await dsEnsure($)
    await dsRoll($).catch(() => undefined)
    return next(e)
  })

  on('command.run', { command: 'dash' }, async ($, e) => {
    await dsEnsure($)
    const isOwner = e.origin?.kind === 'composer' || e.origin?.kind === 'bridge'
    const { verb, rest } = parseDashArgs(e.args ?? '')
    const now = await $.clock.now()
    const nowIso = new Date(now).toISOString()
    const show = async (view: View): Promise<{ text: string }> => {
      dsView = view
      const lines = await dsLines($, view)
      if (dsOn('D3') && (await dsCanDraw($))) await $.ui.open({ id: 'dash', title: 'dash' })
      return { text: linesText(lines) }
    }
    switch (verb) {
      case '':
      case 'overview':
        await dsRoll($)
        return show('overview')
      case 'skills':
      case 'meters':
      case 'tasks':
      case 'context':
        await dsRoll($)
        return show(verb)
      case 'health':
        await dsRoll($, true)
        return show('health')
      case 'gpu':
        if (dsOn('D10')) await dsPollGpu($)
        return show('gpu')
      case 'palette':
        dsBrand = rest || null
        return show('palette')
      case 'godot':
        return show('godot')
      case 'prs':
        await dsRefreshPrs($)
        return show('prs')
      case 'suggest': {
        await dsRoll($)
        const [act, ref] = rest.split(/\s+/)
        if (act === 'accept' || act === 'dismiss' || act === 'snooze') {
          if (!isOwner) return { text: 'Only you can act on a suggestion, by typing /dash suggest yourself.' }
          const r = actOn(dsSuggest, act, ref ?? '', now)
          dsSuggest = r.rows
          if (dsRecording()) await dsWrite($, dsPath('dash/suggestions.json'), serializeSuggestions(dsSuggest, now))
          if (dsNote && !dsSuggest.some(x => x.id === dsNote?.id && x.state === 'shown')) dsNote = null
          return { text: r.text }
        }
        return show('suggest')
      }
      case 'publish': {
        if (!dsOn('D13')) return { text: 'Publishing is off. /dash on publish turns it on.' }
        const feed = await dsRoll($, true)
        const path = dsPath('dash/snapshot.json')
        await dsWrite($, path, `${JSON.stringify(publishSnapshot(feed), null, 2)}\n`)
        return { text: `Wrote a rolled-up snapshot (counts only: no prompts, commands, paths or secrets) to ${path}.\nTo see it on your phone, ask Claude: "publish ~/.claude/revenantworks/dash/snapshot.json as a private Artifact page". The page is a snapshot, never live; run /dash publish again to refresh it.` }
      }
      case 'doctor':
        return { text: await dsDoctor($) }
      case 'purge':
        if (!isOwner) return { text: 'Only you can purge, by typing /dash purge yourself.' }
        return { text: await dsPurge($) }
      case 'help':
        return { text: HELP.join('\n') }
      case 'switches':
      case 'list':
      case 'on':
      case 'off':
      case 'records':
      case 'network': {
        await dsLoadSwitches($)
        const r = applySwitchCommand(dsSw, `${verb} ${rest}`, isOwner, nowIso)
        if (r.changed) {
          await dsSaveSwitches($, r.sw)
          if (verb === 'records') {
            await $.store.set('recordsAnswered', true)
            dsAskRecords = false
            // Rows this session already counted go to the file with the yes.
            if (dsRecording()) dsBuffer = [...dsMem]
          }
          await dsHeartbeat($)
        }
        return { text: r.text }
      }
      default:
        return { text: `Unknown: /dash ${verb}.\n${HELP.join('\n')}` }
    }
  })

  on('ui.render', async ($, e, next) => {
    await dsEnsure($)
    if (e.component === 'Pane' && e.requestId === 'dash') {
      const { Box, Text } = $.ui.resolve(e)
      const lines = await dsLines($, dsView)
      const tone = (t?: string) => (t === 'error' ? 'error' : t === 'warning' ? 'warning' : undefined)
      return (
        <Box flexDirection="column">
          {lines.map((l, i) => <Text key={`d${i}`} color={tone(l.tone)} dimColor={l.tone === 'dim'} bold={l.tone === 'bold'}>{l.text || ' '}</Text>)}
        </Box>
      )
    }
    if (e.component !== 'AbovePrompt' || e.props.hasSurvey) return next(e)
    const { Box, Button, Text } = $.ui.resolve(e)
    const now = await $.clock.now()
    const rows: JSX.Element[] = []
    if (dsAskRecords) {
      rows.push(
        <Box key="ask" columnGap={1}>
          <Text bold>dash</Text>
          <Text dimColor wrap="truncate-end">keep counts across sessions? Counts, hashes and shapes only, never text; on this machine.</Text>
          <Button key="ask-on" label="Turn on" onPress={async () => {
            dsAskRecords = false
            await $.store.set('recordsAnswered', true)
            await dsSaveSwitches($, applySwitchCommand(dsSw, 'records on', true, new Date(await $.clock.now()).toISOString()).sw)
            dsBuffer = [...dsMem]
          }} />
          <Button key="ask-off" label="Keep off" onPress={async () => {
            dsAskRecords = false
            await $.store.set('recordsAnswered', true)
            await dsSaveSwitches($, applySwitchCommand(dsSw, 'records off', true, new Date(await $.clock.now()).toISOString()).sw)
          }} />
          <Button key="ask-later" label="Ask me later" onPress={() => { dsAskRecords = false }} />
        </Box>,
      )
    }
    if (dsOn('D5') && dsNote) {
      const note = dsNote
      rows.push(
        <Box key="note" columnGap={1}>
          <Text bold>dash suggests</Text>
          <Text wrap="truncate-end">{`${note.title} (${note.evidence})`}</Text>
          <Button key="note-show" label="Show" onPress={async () => { dsNote = null; dsView = 'suggest'; await $.ui.open({ id: 'dash', title: 'dash' }) }} />
          <Button key="note-later" label="Later" onPress={() => { dsNote = null }} />
        </Box>,
      )
    }
    if (dsOn('D3')) {
      const running = visibleTasks(dsTasks, now)
      if (running.length > 0) rows.push(<Text key="tasks" dimColor wrap="truncate-end">{`${tasksHeadline(dsTasks, dsLedgerLine())} · /dash tasks`}</Text>)
    }
    for (const p of await dsPanelLines($)) rows.push(<Text key={`p-${p.slice(0, 20)}`} dimColor wrap="truncate-end">{p}</Text>)
    if (rows.length === 0) return next(e)
    return <Box flexDirection="column">{rows}{await next(e)}</Box>
  })
}

