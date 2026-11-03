// vigil: one dashboard for the Revenantworks skills (owner 2026-10-08). A collector counts what
// happens (skill fires, failures, likely misroutes, tokens, meters, command and permission-prompt
// shapes), never text; renderers show it on the status line, in the /rw-vigil pane (text where no pane
// draws) and in VS Code from feed.json. A short suggestion list proposes, never builds. Every `$` use lives in this file; pure logic sits in *-logic.ts and lib/.
// Hook work is kept cheap: hooks push counts to memory; a timer writes them.
import { atom, read, update } from 'claude-code'
import type { CommandRunInput, CommandRunResult, EngineInterface, Register } from 'claude-code'

import {
  METER_EVERY_MS, commandShape, emptyHealth, emptyMisroute, gatewardenCounts, isRevertCommand, onEdit, onRevertCommand,
  onSkillFire, parseEvents, permissionShape, pruneEvents, purgeArgv, rollup, serializeEvents, sessionKey, skillKey,
  type DashEvent, type Feed, type Health, type MisrouteState, type Via,
} from './collector-logic'
import { HANDOFF_MS, RW, RW_PREFIX, bySkill, isLongName, parseRw, resolveTarget, rwDescription, rwListLines } from './launcher-logic'
import { featuresOf } from './lib/catalog'
import { applySwitchCommand } from './lib/commands'
import { parseShell, writeTargets } from './lib/shell'
import { isFeatureOn, isRecordingOn, parseSwitches, serializeSwitches, type Switches } from './lib/switches'
import { fnv1a, formatAge, heartbeatAlive, isWindowsEnv, mergeHeartbeat, normPath } from './lib/util'
import { cacheHit, liveFromMeasure, liveFromMeterFile, meterFile, shouldWriteMeterFile, statusText, versionAtLeast, STALE_MS, type Live, type Usage } from './meters-logic'
import { actOn, candidates, mergeSuggestions, neverAgain, parseSuggestions, pickNote, serializeSuggestions, type Suggestion } from './suggest-logic'
import {
  addTask, endAgent, estimateFor, isRunActive, runOwnedBy, lastLineOf, matchLedgerRow, newestLedger, parseEstWall, parseLedger,
  parseTaskNotifications, reconcileAgents, reopenTask, reconcileFlags, recordDuration, runIdFromPath, sanitizeTaskHistory, settleTask, summariseLedger,
  taskSignature, taskStatusLines, tasksHeadline, visibleTasks,
  type LedgerRow, type TaskHistory, type TaskRecord,
} from './tasks-logic'
import {
  NEUTRAL, consoleBackground, discoverThemes, headerText, parseActive, parseBackground, pickTheme, resolveVariant, wantsContrast,
  toneStyle, type ConsoleBg, type ConsoleInfo, type Theme, type ThemeEntry,
} from './theme-logic'
import {
  HELP, head, healthLines, linesText, metersLines, navTabs, overviewLines, panelLines, parseDashArgs, skillsLines, themeApplied, themeLines, dupesLines, findDupes,
  type Line, type Press, type View,
} from './view-logic'
import { RW_SKILLS } from './rw-skills'
import {
  SWITCHES, arranged, boardText, cardsOf, crossed, dailyTokens, detailOf, doItOf, evidenceDots, glanceMeters, glanceOf, glanceText, gridColumns, gridRows, isAutoMode, isTile, moveTile,
  notNow, openCount, parseAutoModes, parseBudget, parseLayout, pictureAlt, pictureGlyph, pictureSvg, serializeAutoModes, tileOf, tilePicture, tileWidth, toggleCollapsed,
  togglePinned, undoRow, AUTO_MODES, type AutoModes, type BoardData, type Budget, type Layout, type MineTile, type Picture, type TileId, parseShroudBeat, shieldText,
} from './board-logic'
import { ASCII_BLOCKS, BLOCKS, inkOf } from './draw-logic'
import {
  BUILD_SOURCES, READ_MAX_BYTES, TILES_MAX, buildPrompt, isBuildSource, parseLink, parseSpec, realProblem, resolvePath, tileKey, userTileOf, valueOf,
  type BuildSource, type Link, type Reading, type TileSpec,
} from './tiles-logic'

const PLUGIN = 'vigil'
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
/** The pane's revision in $.state (types/index.d.ts): the pane reads it, a press bumps it. */
const dsPaneRev = atom({ plugin: 'vigil', key: 'paneRev' } as const, 0)
/** The band's revision, the same way: the band above the prompt reads it, a band press bumps it. */
const dsBandRev = atom({ plugin: 'vigil', key: 'bandRev' } as const, 0)
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
let dsView: View = 'board'
// the board (phase 4): its layout (saved per machine in $.store), the open detail, the last Not now
let dsLayout: Layout = parseLayout(null)
let dsDetail: TileId = 'usage'
let dsArranging = false
let dsBandHidden = false
let dsUndo: Suggestion | null = null
let dsAuto: AutoModes = parseAutoModes(null)
let dsBudget: Budget | null = null
// the tile builder (phase 5): the user's own tile specs, the files refused and why, the picked source
let dsMine: TileSpec[] = []
let dsMineErrors: Array<{ file: string; errors: string[] }> = []
let dsMineDrawn: { at: number; map: Map<string, MineTile> } | null = null
let dsBuildSrc: BuildSource = 'repo'
/** Your private folder of tiles and themes, and the clones `@/` means (/rw-vigil link). */
let dsLink: Link | null = null
/** The highest level (80, 90) each meter already toasted at; it clears when the meter drops under 80. */
const dsAlerted: Record<'five' | 'week' | 'ctx', number> = { five: 0, week: 0, ctx: 0 }
let dsMeterWrittenAt: number | null = null
// tasks (F3, F3f, F3e)
let dsTasks: TaskRecord[] = []
let dsTaskHist: TaskHistory = {}
let dsLedgerPath: string | null = null
let dsLedgerRows: LedgerRow[] = []
let dsRunActive = false
let dsRunOwned = false   // the active run is this session's own (D7 writes only then)
// themes: bundled plus the person's files in ~/.claude/revenantworks/themes/
let dsTheme: Theme = NEUTRAL
let dsThemes: Record<string, ThemeEntry> = discoverThemes([]).themes
let dsThemeErrors: string[] = []
let dsThemeNoticed = ''
// The console's background (VIGIL_THEME_BACKGROUND, the Claude Code theme, COLORFGBG) and the picked theme before its variant.
let dsConsole: ConsoleInfo = consoleBackground(null, null, null)
let dsThemeBase: Theme = NEUTRAL
// Each listed skill's source by the engine's word (userSettings, plugin, syncedSkills, built-in), this session only.
let dsSkillSources: Record<string, string> = {}

function dsOn(id: string): boolean {
  return isFeatureOn(dsSw, id)
}

/** The meter cells the theme's glyph set allows: blocks, or plain ASCII. */
function dsGlyphs() {
  return dsTheme.glyphs.full === '#' ? ASCII_BLOCKS : BLOCKS
}

/** Redraws the band: every change to what it shows (dsAskRecords, dsNote, a switch) calls this,
 *  wherever it happens, since a module variable alone redraws nothing (the dead Later, AD). */
async function dsBandBump($: EngineInterface): Promise<void> {
  await update($, dsBandRev, n => (n ?? 0) + 1)
}

/** Redraws the pane and the band: for a change both show, such as the theme. */
async function dsRedraw($: EngineInterface): Promise<void> {
  await update($, dsPaneRev, n => (n ?? 0) + 1)
  await dsBandBump($)
}

async function dsEnv($: EngineInterface, name: 'THEME' | 'THEME_BACKGROUND' | 'THEME_CONTRAST'): Promise<string | undefined> {
  if (name === 'THEME') return $.env.get('VIGIL_THEME')
  return name === 'THEME_CONTRAST' ? $.env.get('VIGIL_THEME_CONTRAST') : $.env.get('VIGIL_THEME_BACKGROUND')
}

function dsRecording(): boolean {
  return isRecordingOn(dsSw, 'D1')
}

function dsPath(name: string): string {
  return `${dsHome}/.claude/revenantworks/${name}`
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
  const on = featuresOf('vigil').filter(x => dsOn(x.id)).map(x => x.id)
  const file = dsPath(`health/${PLUGIN}.json`)
  await dsWrite($, file, mergeHeartbeat(await dsRead($, file), { plugin: PLUGIN, version: VERSION, session: fnv1a(dsSession), at: await $.clock.now(), on, caught: dsCaught }))
}

/** Writes the buffered rows to events.jsonl (records only), pruned to 30 days. */
async function dsFlush($: EngineInterface): Promise<DashEvent[]> {
  const now = await $.clock.now()
  if (!dsRecording()) {
    dsBuffer = []
    return dsMem
  }
  const file = dsPath('vigil/events.jsonl')
  const events = pruneEvents([...parseEvents(await dsRead($, file)), ...dsBuffer], now)
  dsBuffer = []
  await dsWrite($, file, serializeEvents(events))
  return events
}

/** Health: heartbeats, hook drift (when asked), gatewarden's counts, pins. */
async function dsHealthNow($: EngineInterface, full: boolean): Promise<Health> {
  const now = await $.clock.now()
  const plugins: Health['plugins'] = {}
  for (const p of ['vigil', 'shroud']) {
    // Every session on the machine beats into one file; this session reads its own entry.
    const b = heartbeatAlive(await dsRead($, dsPath(`health/${p}.json`)), fnv1a(dsSession), now)
    plugins[p] = { loaded: b.alive, at: b.at, version: b.version, caught: b.caught }
  }
  plugins.vigil = { loaded: true, at: now, version: VERSION, caught: dsCaught }
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
  dsHealth = { plugins, drift, gatewarden }
  return dsHealth
}

/**
 * The file is the queue. Every session rolls on a timer, so a copy held in memory would write back a
 * row another session just dismissed (the queue that "filled up again"). Each change starts here.
 */
async function dsReloadSuggest($: EngineInterface): Promise<void> {
  if (!dsRecording()) return
  dsSuggest = parseSuggestions(await dsRead($, dsPath('vigil/suggestions.json')))
  if (dsNote && !dsSuggest.some(x => x.id === dsNote?.id && x.state === 'shown')) {
    dsNote = null
    await dsBandBump($)
  }
}

/** Flush, then fold into feed.json and the suggestion queue. Files only with the records yes. */
async function dsRoll($: EngineInterface, full = false): Promise<Feed> {
  const now = await $.clock.now()
  const events = await dsFlush($)
  const health = await dsHealthNow($, full)
  let feed = rollup(events, { now, recording: dsRecording(), health })
  if (dsOn('D5')) {
    await dsReloadSuggest($)
    dsSuggest = mergeSuggestions(dsSuggest, candidates(events, feed, now), now)
    feed = { ...feed, suggestionsNew: dsSuggest.filter(r => r.state === 'new').length }
  }
  dsFeed = feed
  if (dsRecording()) {
    await dsWrite($, dsPath('vigil/feed.json'), `${JSON.stringify(feed, null, 2)}\n`)
    if (dsOn('D5')) await dsWrite($, dsPath('vigil/suggestions.json'), serializeSuggestions(dsSuggest, now))
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
  // A listing gives a folder (and a junction) no time, so each run is judged by its ledger file.
  const found: Array<{ path: string; mtimeMs: number }> = []
  for (const base of [...new Set([`${dsRoot || dsCwd}/.dispatch/runs`, `${dsCwd}/.dispatch/runs`, `${dsHome}/.dispatch/runs`])]) {
    let runs: Awaited<ReturnType<typeof $.fs.list>> = []
    try {
      runs = await $.fs.list(base)
    } catch {
      continue
    }
    for (const r of runs.filter(x => x.kind === 'dir' || x.isLink).slice(0, 200)) {
      for (const f of ['ledger.md', 'ledger.csv']) {
        try {
          const st = await $.fs.stat(`${base}/${r.name}/${f}`)
          if (st.kind === 'file') found.push({ path: `${base}/${r.name}/${f}`, mtimeMs: st.mtimeMs })
        } catch {
          // No ledger in this run folder.
        }
      }
    }
  }
  const newest = newestLedger(found)
  if (newest) candidatesList.push(newest)
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
  const now = await $.clock.now()
  dsRunActive = isRunActive(flag ?? undefined, now) && dsLedgerPath !== null
  // Writes (D7) need ownership: an explicit ledger for this process, or the flag naming this session.
  dsRunOwned = dsRunActive && (Boolean(await $.env.get('CLAUDE_DISPATCH_LEDGER'))
    || runOwnedBy(flag ?? undefined, dsSession, now))
}

function dsLedgerLine(): string | null {
  return dsLedgerPath ? summariseLedger(runIdFromPath(dsLedgerPath), dsLedgerRows).line : null
}

/** F3f: every background task: what it is, who started it, how long, an estimate and its last output. */
async function dsTaskLines($: EngineInterface): Promise<Line[]> {
  const now = await $.clock.now()
  try {
    dsTasks = reconcileAgents(dsTasks, await $.agent.list(), now, d => taskSignature('agent', d))
  } catch {
    // No agent list on this host: tasks seen through tool calls still show.
  }
  const t0 = dsTheme
  const out: Line[] = [head(t0, 'Tasks'), { text: `  ${tasksHeadline(dsTasks, null).replace(/^Tasks: /, '')}`, tone: 'bold' }]
  out.push({ text: `  ${dsLedgerLine() ?? 'no dispatch ledger here'}`, tone: 'dim' })
  const shown = dsTasks.filter(t => t.state === 'running' || now - (t.endedAt ?? now) < 10 * 60_000)
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
    const lines = taskStatusLines(t, now, estimateFor(t.sig, dsTaskHist, parseEstWall(row?.estWall), t.timeoutMs), progress)
    const glyph = t.state === 'running' ? t0.glyphs.on : t.state === 'completed' ? t0.glyphs.ok : t.state === 'failed' ? t0.glyphs.bad : t0.glyphs.warn
    const tone = t.state === 'running' ? 'accent' : t.state === 'completed' ? 'ok' : t.state === 'failed' ? 'error' : 'warning'
    out.push({ text: '' }, { text: `  ${glyph} ${lines[0]}`, tone }, ...lines.slice(1).map(text => ({ text: `  ${text}`, tone: 'dim' as const })))
  }
  if (shown.length === 0) out.push({ text: '' }, { text: '  No background task is running, and none finished in the last 10 minutes.', tone: 'dim' })
  return out
}

type Table = ReturnType<EngineInterface['ui']['resolve']>
type OnPress = (p: Press) => () => Promise<void>

/** A picture on this surface: the SVG where the surface draws one, else its glyph line. */
function dsPicture(table: Table, p: Picture, size = 56): JSX.Element {
  const t = table as Record<string, unknown>
  const { Text } = table
  const Svg = t.Svg as ((props: { source: string; alt: string; height?: number }) => JSX.Element) | undefined
  if (Svg) return <Svg source={pictureSvg(p, inkOf(dsTheme, dsConsole.bg), size)} alt={pictureAlt(p)} />
  return <Text color={dsTheme.colors.accent}>{pictureGlyph(p, dsGlyphs(), dsTheme.glyphs.on, dsTheme.glyphs.off, dsTheme.glyphs.bad)}</Text>
}

/** The board, one tile's detail, the inbox cards or the three switches, as the pane draws them. */
async function dsBoardTree($: EngineInterface, table: Table, onPress: OnPress, columns: number): Promise<JSX.Element> {
  const { Box, Button, Text } = table
  const accent = dsTheme.colors.accent
  const now = await $.clock.now()
  if (dsView === 'detail') {
    const d = detailOf(dsDetail, await dsBoardData($))
    return (
      <Box flexDirection="column" rowGap={1}>
        <Box columnGap={1}>
          <Button key="back" label="< Board" plain dimColor onPress={onPress({ kind: 'view', view: 'board' })} />
          <Text bold color={accent}>{d.title}</Text>
        </Box>
        {dsPicture(table, d.picture, 96)}
        <Box flexDirection="column">{d.lines.map((l, i) => <Text key={`dl${i}`} wrap="wrap">{l}</Text>)}</Box>
        {dsMine.find(s => tileKey(s.id) === dsDetail)?.act ? <Button key="tile-act" label={dsMine.find(s => tileKey(s.id) === dsDetail)!.act!.label} variant="secondary" onPress={onPress({ kind: 'tile-act', id: dsDetail })} /> : null}
        {dsDetail === 'privacy' ? <Button key="rotate" label="Rotate it" variant="secondary" onPress={onPress({ kind: 'rotate' })} /> : null}
        {dsDetail === 'mode' ? (
          <Box flexDirection="column">
            {AUTO_MODES.map(m => (
              <Box key={`auto-${m}`} columnGap={1}>
                <Text>{`${m}: ${dsAuto[m] ? 'pacewright may enter it by itself' : 'only on your word'}`}</Text>
                <Button key={`auto:${m}`} label={dsAuto[m] ? 'Switch off' : 'Switch on'} plain dimColor onPress={onPress({ kind: 'auto', mode: m, on: !dsAuto[m] })} />
              </Box>
            ))}
          </Box>
        ) : null}
      </Box>
    )
  }
  if (dsView === 'cards') {
    const { cards, waiting } = cardsOf(dsSuggest, now)
    return (
      <Box flexDirection="column" rowGap={1}>
        <Text bold color={accent}>Inbox</Text>
        {cards.length === 0 ? <Text dimColor>Nothing waits.</Text> : null}
        {cards.map(c => (
          <Box key={`card-${c.id}`} flexDirection="column" borderStyle="round" borderColor={dsTheme.colors.rule} paddingX={1}>
            <Text wrap="wrap">{c.title}</Text>
            {dsPicture(table, { kind: 'dots', dots: evidenceDots(c) }, 10)}
            <Text color={dsTheme.colors.dim} wrap="truncate-end">{c.evidence}</Text>
            <Box columnGap={1}>
              <Button key={`do:${c.id}`} label="Do it" variant="primary" onPress={onPress({ kind: 'card', op: 'do', id: c.id })} />
              <Button key={`notnow:${c.id}`} label="Not now" variant="secondary" onPress={onPress({ kind: 'card', op: 'notnow', id: c.id })} />
              <Button key={`never:${c.id}`} label="Never" plain dimColor onPress={onPress({ kind: 'card', op: 'never', id: c.id })} />
            </Box>
          </Box>
        ))}
        {waiting ? <Text dimColor>{`${waiting} more wait. They show as these clear.`}</Text> : null}
        {dsUndo ? <Box columnGap={1}><Text dimColor wrap="truncate-end">{`Hidden: ${dsUndo.title}`}</Text><Button key="undo" label="Undo" plain dimColor onPress={onPress({ kind: 'card', op: 'undo', id: dsUndo.id })} /></Box> : null}
      </Box>
    )
  }
  if (dsView === 'tiles') {
    return (
      <Box flexDirection="column" rowGap={1}>
        <Text bold color={accent}>Build a tile</Text>
        <Text wrap="wrap">Pick a source. Claude reads it, proposes tiles in chat, and saves one only when you say yes. A tile is data: it reads one file and shows numbers and dates, and no script runs.</Text>
        <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
          {(Object.keys(BUILD_SOURCES) as BuildSource[]).map(src => (
            <Button key={`pick:${src}`} label={src === dsBuildSrc ? `[${src}]` : src} plain dimColor onPress={onPress({ kind: 'build', op: 'pick', source: src })} />
          ))}
        </Box>
        <Text dimColor wrap="wrap">{BUILD_SOURCES[dsBuildSrc]}</Text>
        <Button key="scan" label={`Scan ${dsBuildSrc}`} variant="primary" onPress={onPress({ kind: 'build', op: 'scan', source: dsBuildSrc })} />
        <Box flexDirection="column">{dsTilesText().map((l, i) => <Text key={`tl${i}`} wrap="wrap" dimColor={i > 0}>{l}</Text>)}</Box>
      </Box>
    )
  }
  if (dsView === 'settings') {
    return (
      <Box flexDirection="column" rowGap={1}>
        <Text bold color={accent}>Settings</Text>
        {SWITCHES.map(x => (
          <Box key={`sw-${x.name}`} columnGap={1}>
            <Text>{`${x.name}: ${dsOn(x.id) ? 'on' : 'off'}`}</Text>
            <Button key={`switch:${x.name}`} label={dsOn(x.id) ? 'Turn off' : 'Turn on'} plain dimColor onPress={onPress({ kind: 'switch', command: dsOn(x.id) ? x.off : x.on })} />
          </Box>
        ))}
        <Text dimColor>Panels for GPU, Godot and PRs stay on /rw-vigil switches for now.</Text>
      </Box>
    )
  }
  const d = await dsBoardData($)
  const order = arranged(dsLayout)
  // Layout controls live in one list of their own, so a tile holds only its reading.
  if (dsArranging) {
    return (
      <Box flexDirection="column" rowGap={1}>
        <Box justifyContent="space-between" columnGap={1}>
          <Text bold color={accent}>Arrange</Text>
          <Box columnGap={2}>
            <Button key="arrange-reset" label="Reset" plain dimColor onPress={onPress({ kind: 'arrange', op: 'reset' })} />
            <Button key="arrange-done" label="Done" variant="primary" onPress={onPress({ kind: 'arrange', op: 'toggle' })} />
          </Box>
        </Box>
        <Box flexDirection="column">
          {order.map(id => (
            <Box key={`row-${id}`} columnGap={2}>
              <Box width={16}><Text wrap="truncate-end">{tileOf(id, d).title}</Text></Box>
              <Button key={`pin:${id}`} label={dsLayout.pinned.includes(id) ? 'Unpin' : 'Pin'} plain dimColor onPress={onPress({ kind: 'tile', op: 'pin', id })} />
              <Button key={`collapse:${id}`} label={dsLayout.collapsed.includes(id) ? 'Unfold' : 'Fold'} plain dimColor onPress={onPress({ kind: 'tile', op: 'collapse', id })} />
              <Button key={`up:${id}`} label="Up" plain dimColor onPress={onPress({ kind: 'tile', op: 'up', id })} />
              <Button key={`down:${id}`} label="Down" plain dimColor onPress={onPress({ kind: 'tile', op: 'down', id })} />
            </Box>
          ))}
        </Box>
      </Box>
    )
  }
  const shown = order.filter(id => !dsLayout.collapsed.includes(id))
  const folded = order.filter(id => dsLayout.collapsed.includes(id))
  const width = tileWidth(columns)
  return (
    <Box flexDirection="column" rowGap={1}>
      <Box flexDirection="column">
        {gridRows(shown, gridColumns(columns)).map((row, r) => (
          <Box key={`grid${r}`} columnGap={1}>
            {row.map(id => {
              const t = tileOf(id, d)
              const pic = tilePicture(t.picture)
              return (
                <Box key={`tile-${id}`} flexDirection="column" borderStyle="round" borderColor={dsTheme.colors.rule} paddingX={1} width={width}>
                  <Box justifyContent="space-between" columnGap={1}>
                    <Button key={`open:${id}`} plain onPress={onPress({ kind: 'tile', op: 'open', id })}><Text bold>{t.title}</Text></Button>
                    <Text bold color={t.tone && t.tone !== 'ok' ? toneStyle(dsTheme, t.tone).color : undefined} wrap="truncate-end">{t.big}</Text>
                  </Box>
                  <Text color={dsTheme.colors.dim} wrap="truncate-end">{t.sub}</Text>
                  {pic ? dsPicture(table, pic, 40) : null}
                </Box>
              )
            })}
          </Box>
        ))}
      </Box>
      {folded.length ? (
        <Box flexWrap="wrap" columnGap={2}>
          <Text dimColor>Folded</Text>
          {folded.map(id => {
            const t = tileOf(id, d)
            return <Button key={`open:${id}`} plain dimColor onPress={onPress({ kind: 'tile', op: 'open', id })}>{t.title} <Text bold>{t.big}</Text></Button>
          })}
        </Box>
      ) : null}
      <Box justifyContent="flex-end">
        <Button key="arrange" label="Arrange" plain dimColor onPress={onPress({ kind: 'arrange', op: 'toggle' })} />
      </Box>
    </Box>
  )
}

/** Hide or bring back the band; the choice holds across sessions. */
async function dsSetBandHidden($: EngineInterface, hidden: boolean): Promise<void> {
  dsBandHidden = hidden
  // A store that fails costs only the memory: the band still hides in this session.
  await $.store.set('bandHidden', hidden).catch(() => undefined)
  await dsBandBump($)
}

const BAND_HIDDEN_NOTE = 'vigil is hidden. /rw-vigil show brings the strip back; the status line stays.'

/** pacewright's live decision and the auto-mode switches it reads, both under ~/.dispatch/. */
function dsDispatch(name: string): string {
  return `${dsHome}/.dispatch/${name}`
}

async function dsLoadSpend($: EngineInterface): Promise<void> {
  const now = await $.clock.now()
  dsBudget = parseBudget(await dsRead($, dsDispatch('budget-decision.json')), now)
  dsAuto = parseAutoModes(await dsRead($, dsDispatch('spend-modes.json')))
}

/** The one writer of spend-modes.json is the person: a press or a typed command, never a hook by itself. */
async function dsSetAuto($: EngineInterface, mode: (typeof AUTO_MODES)[number], on: boolean): Promise<string> {
  await dsLoadSpend($)
  dsAuto = { ...dsAuto, [mode]: on }
  await $.fs.write(dsDispatch('spend-modes.json'), serializeAutoModes(dsAuto, await $.clock.now()))
  return on ? `${mode}: pacewright may enter it by itself again.` : `${mode}: pacewright enters it only when you say so.`
}

/** The user's own tiles folder: data only, on this machine, never in the plugin. */
function dsTilesDir(): string {
  return dsPath('vigil/tiles')
}

/** Re-reads every spec in the tiles folder. A refused file is listed with its reasons, never half-loaded. */
async function dsLoadTiles($: EngineInterface): Promise<void> {
  dsLink = parseLink(await dsRead($, dsPath('link.json')))
  const files: Array<{ dir: string; name: string; size: number }> = []
  // Your linked folder first; a file of the same name in the tiles folder on this machine wins.
  for (const dir of [dsTilesDir(), ...(dsLink ? [`${dsLink.folder}/tiles`] : [])]) {
    try {
      for (const e of await $.fs.list(dir)) if (e.kind === 'file' && e.name.endsWith('.json') && !files.some(x => x.name === e.name)) files.push({ dir, name: e.name, size: e.size })
    } catch {
      // No such folder: nothing to load from it.
    }
  }
  files.sort((a, b) => a.name.localeCompare(b.name))
  const mine: TileSpec[] = []
  const errors: Array<{ file: string; errors: string[] }> = []
  for (const f of files) {
    if (mine.length >= TILES_MAX) {
      errors.push({ file: f.name, errors: [`over the ${TILES_MAX}-tile limit`] })
      continue
    }
    if (f.size > 20_000) {
      errors.push({ file: f.name, errors: ['larger than 20 KB'] })
      continue
    }
    const r = parseSpec((await dsRead($, `${f.dir}/${f.name}`)) ?? '', f.name.slice(0, -5))
    if ('spec' in r) mine.push(r.spec)
    else errors.push({ file: f.name, errors: r.errors })
  }
  dsMine = mine
  dsMineErrors = errors
  dsMineDrawn = null
  dsLayout = parseLayout(dsLayout, mine.map(t => tileKey(t.id)))
}

/** What one tile's source holds right now. Read only; a file over 1 MB is not read. */
async function dsReadTile($: EngineInterface, spec: TileSpec): Promise<Reading> {
  const path = resolvePath(spec.source.path, dsHome, dsRoot, dsLink?.root ?? '')
  if (!path) return { kind: 'missing', why: spec.source.path.startsWith('@/') ? 'no link yet: /rw-vigil link' : 'no repo here for a ./ path' }
  try {
    const st = await $.fs.stat(path, { resolve: true })
    const base = async (p: string) => (p ? (await $.fs.stat(p, { resolve: true }).catch(() => undefined))?.realPath ?? '' : '')
    const why = realProblem(st.realPath, [await base(dsHome), await base(dsRoot), await base(dsLink?.root ?? '')], spec.source.kind === 'size')
    if (why) return { kind: 'missing', why }
    if (spec.source.kind === 'size') return st.kind === 'file' ? { kind: 'size', size: st.size } : { kind: 'missing', why: 'not a file' }
    if (spec.source.kind === 'files') {
      if (st.kind !== 'dir') return { kind: 'missing', why: 'not a folder' }
      return { kind: 'files', entries: (await $.fs.list(path)).slice(0, 2000).map(e => ({ name: e.name, kind: e.kind, mtimeMs: e.mtimeMs })) }
    }
    if (st.kind !== 'file') return { kind: 'missing', why: 'not a file' }
    if (spec.source.kind === 'age') return { kind: 'text', text: '', mtimeMs: st.mtimeMs }
    if (st.size > READ_MAX_BYTES) return { kind: 'missing', why: 'larger than 1 MB' }
    return { kind: 'text', text: await $.fs.read(path), mtimeMs: st.mtimeMs }
  } catch {
    return { kind: 'missing', why: 'no such file' }
  }
}

/** The user's tiles, read and drawn; kept 30 seconds so a redraw does not re-read every file. */
async function dsMineTiles($: EngineInterface, now: number): Promise<Map<string, MineTile>> {
  if (dsMineDrawn && now - dsMineDrawn.at < 30_000) return dsMineDrawn.map
  const map = new Map<string, MineTile>()
  for (const spec of dsMine) map.set(tileKey(spec.id), userTileOf(spec, valueOf(spec, await dsReadTile($, spec), now), now))
  dsMineDrawn = { at: now, map }
  return map
}

/** Your tiles as text: each loaded one, each refused file and why, and where they live. */
function dsTilesText(): string[] {
  const out = [dsMine.length ? `${dsMine.length} tile(s) on the board.` : 'No tiles of your own yet.']
  for (const t of dsMine) out.push(`  ${t.id}: ${t.title}, a ${t.picture} from ${t.source.path}`)
  for (const e of dsMineErrors) out.push(`  ${e.file} refused: ${e.errors.slice(0, 3).join('; ')}`)
  out.push(`Folder: ${dsTilesDir()}. Delete a file to remove its tile.`)
  out.push(dsLink ? `Linked: ${dsLink.folder} (tiles, themes); @/ is ${dsLink.root}.` : '/rw-vigil link keeps your own tiles and themes in a private folder.')
  return out
}

/** Build a tile: hands Claude the read-only scan brief. Claude proposes; nothing is saved until the user says yes. */
async function dsBuild($: EngineInterface, src: BuildSource): Promise<string> {
  dsBuildSrc = src
  const text = buildPrompt(src, dsTilesDir())
  $.clock.after(HANDOFF_MS, () => void $.prompt.submit({ text }).catch(() => undefined))
  return `Asked Claude to scan ${BUILD_SOURCES[src]}. It proposes tiles in chat and saves nothing until you say yes.`
}

async function dsSaveLayout($: EngineInterface, l: Layout): Promise<void> {
  dsLayout = l
  await $.store.set('layout', l)
}

/** Everything the board reads, in one place, so the pane and a typed /rw-vigil board agree. */
async function dsBoardData($: EngineInterface): Promise<BoardData> {
  const now = await $.clock.now()
  const feed = dsFeed ?? (await dsRoll($))
  const live = dsLive && now - dsLive.at <= STALE_MS ? dsLive : liveFromMeterFile(await dsRead($, ((await $.env.get('CLAUDE_USAGE_WINDOWS')) ?? `${dsHome}/.claude/usage-windows.json`).replace(/\\/g, '/'))) ?? dsLive
  const shroud = parseShroudBeat(await dsRead($, dsPath('health/shroud.json')), fnv1a(dsSession))
  return { live, now, feed, daily: dailyTokens(dsMem, now), inbox: openCount(dsSuggest, now), budget: dsBudget, auto: dsAuto, mine: await dsMineTiles($, now), shroud }
}

async function dsSaveSuggest($: EngineInterface): Promise<void> {
  if (dsRecording()) await dsWrite($, dsPath('vigil/suggestions.json'), serializeSuggestions(dsSuggest, await $.clock.now()))
}

/** Do it: hands Claude a drafted change in chat, or the built-in that already does the job. Writes nothing. */
async function dsDoIt($: EngineInterface, id: string): Promise<void> {
  const row = dsSuggest.find(r => r.id === id)
  if (!row) return
  const now = await $.clock.now()
  dsSuggest = dsSuggest.map(r => (r.id === id ? { ...r, state: 'accepted' as const, stateAt: now } : r))
  await dsSaveSuggest($)
  const d = doItOf(row)
  // A run started inside the press's own hook is refused, so it goes out on the clock (the launcher's hand-off).
  if (d.kind === 'command') $.clock.after(HANDOFF_MS, () => void $.command.run({ command: d.command, args: '' }).catch(() => undefined))
  else $.clock.after(HANDOFF_MS, () => void $.prompt.submit({ text: d.text }).catch(() => undefined))
  $.ui.toast(d.kind === 'command' ? `Opening /${d.command}; it asks before it writes.` : 'Drafted in chat. Nothing is written until you say yes there.')
}

async function dsPress($: EngineInterface, p: Press): Promise<void> {
  if (p.kind === 'arrange') {
    if (p.op === 'toggle') dsArranging = !dsArranging
    else await dsSaveLayout($, parseLayout(null, dsMine.map(t => tileKey(t.id))))
    return
  }
  if (p.kind === 'tile') {
    if (p.op === 'open') {
      if (p.id === 'inbox') dsView = 'cards'
      else {
        dsDetail = p.id
        dsView = 'detail'
      }
      return
    }
    const l = p.op === 'collapse' ? toggleCollapsed(dsLayout, p.id) : p.op === 'pin' ? togglePinned(dsLayout, p.id) : moveTile(dsLayout, p.id, p.op === 'up' ? -1 : 1)
    await dsSaveLayout($, l)
    return
  }
  if (p.kind === 'tile-act') {
    const act = dsMine.find(s => tileKey(s.id) === p.id)?.act
    if (act) {
      $.clock.after(HANDOFF_MS, () => void $.prompt.submit({ text: act.prompt }).catch(() => undefined))
      $.ui.toast('Drafted in chat. Nothing is written until you say yes there.')
    }
    return
  }
  if (p.kind === 'theme') {
    $.ui.toast(await dsApplyTheme($, p.name))
    return
  }
  if (p.kind === 'background') {
    $.ui.toast(await dsApplyBackground($, p.bg))
    return
  }
  if (p.kind === 'card') {
    const now = await $.clock.now()
    await dsReloadSuggest($)
    if (p.op === 'do') await dsDoIt($, p.id)
    else if (p.op === 'never') {
      dsSuggest = neverAgain(dsSuggest, p.id, now)
      await dsSaveSuggest($)
    }
    else if (p.op === 'notnow') {
      const r = notNow(dsSuggest, p.id, now)
      dsSuggest = r.rows
      dsUndo = r.before
      await dsSaveSuggest($)
      if (r.before) $.ui.toast(`Hidden for ${r.days} days: ${r.before.title}. Undo is on the board.`)
    } else if (p.op === 'undo' && dsUndo && dsUndo.id === p.id) {
      dsSuggest = undoRow(dsSuggest, dsUndo)
      dsUndo = null
      await dsSaveSuggest($)
    }
    if (dsNote && !dsSuggest.some(x => x.id === dsNote?.id && x.state === 'shown')) dsNote = null
    return
  }
  if (p.kind === 'switch') {
    await dsLoadSwitches($)
    // A press in the pane is the person's own: the same as typing the command.
    const r = applySwitchCommand(dsSw, p.command, true, new Date(await $.clock.now()).toISOString())
    if (r.changed) {
      await dsSaveSwitches($, r.sw)
      if (p.command.startsWith('records')) {
        await $.store.set('recordsAnswered', true)
        dsAskRecords = false
        if (dsRecording()) dsBuffer = [...dsMem]
      }
      await dsHeartbeat($)
    }
    $.ui.toast(r.text.split('\n')[0]!)
    return
  }
  if (p.kind === 'auto') {
    $.ui.toast(await dsSetAuto($, p.mode, p.on))
    return
  }
  if (p.kind === 'rotate') {
    // shroud owns the vault, so the draft is its own: vigil only asks for it, on the clock (the hand-off rule).
    $.clock.after(HANDOFF_MS, () => void $.command.run({ command: 'rw-shroud', args: 'rotate' }).catch(() => undefined))
    $.ui.toast('Asked shroud to draft a keywarden rotation in chat. Nothing changes until you say yes there.')
    return
  }
  if (p.kind === 'build') {
    if (p.op === 'pick') dsBuildSrc = p.source
    else $.ui.toast(await dsBuild($, p.source))
    return
  }
  if (p.kind === 'view') {
    // The same refresh the typed /rw-vigil <verb> does, so a press and a command show the same view.
    if (p.view === 'health') await dsRoll($, true)
    else if (p.view !== 'theme') await dsRoll($)
    if (p.view === 'board' || p.view === 'detail') await dsLoadSpend($)
    if (p.view === 'board' || p.view === 'tiles') await dsLoadTiles($)
    dsView = p.view
  }
}

async function dsLines($: EngineInterface, view: View): Promise<Line[]> {
  const now = await $.clock.now()
  const feed = dsFeed ?? (await dsRoll($))
  const live = dsLive && now - dsLive.at <= STALE_MS ? dsLive : liveFromMeterFile(await dsRead($, ((await $.env.get('CLAUDE_USAGE_WINDOWS')) ?? `${dsHome}/.claude/usage-windows.json`).replace(/\\/g, '/'))) ?? dsLive
  const th = dsTheme
  const text = (title: string, xs: string[]): Line[] => panelLines(th, title, xs)
  switch (view) {
    case 'board': return text('vigil', [glanceText(glanceOf(await dsBoardData($)), dsGlyphs()), '', ...boardText(dsLayout, await dsBoardData($), dsGlyphs()).map(l => l.slice(2))])
    case 'detail': {
      const d = detailOf(dsDetail, await dsBoardData($))
      return text(d.title, [pictureGlyph(d.picture, dsGlyphs()), ...d.lines])
    }
    case 'cards': {
      const { cards, waiting } = cardsOf(dsSuggest, now)
      if (!cards.length) return text('Inbox', ['Nothing waits.'])
      return text('Inbox', [...cards.flatMap((c, i) => [`${i + 1}. ${c.title}`, `   ${c.evidence}`]), ...(waiting ? [`${waiting} more wait.`] : []), '/rw-vigil suggest accept|dismiss|snooze <n>. In the pane: Do it, Not now, Never.'])
    }
    case 'tiles': return text('Your tiles', dsTilesText())
    case 'settings': return text('Settings', [...SWITCHES.map(x => `${x.name}: ${dsOn(x.id) ? 'on' : 'off'}`), `Auto spend modes: ${AUTO_MODES.map(m => `${m} ${dsAuto[m] ? 'on' : 'off'}`).join(', ')}`, '/rw-vigil switches lists every feature id.'])
    case 'skills': return skillsLines(feed, th, { sources: dsSkillSources })
    case 'skills-all': return skillsLines(feed, th, { all: true, sources: dsSkillSources })
    case 'dupes': return dupesLines(feed, th, dsSkillSources)
    case 'meters': return metersLines(live, feed, now, th)
    case 'health': return healthLines(feed.health, th, findDupes(feed.skills, dsSkillSources))
    case 'tasks': return dsTaskLines($)
    case 'theme': return themeLines(dsThemes, dsTheme.name, dsTheme, dsThemeErrors, dsConsole)
    case 'context': {
      try {
        const u = await $.session.usage({ breakdown: 'summary' })
        const b = u.context.breakdown
        if (!b) return text('Context', ['No breakdown yet: it is taken after the first answer.'])
        return text('Context', [
          `${Math.round(b.totalTokens / 1000)}k of ${Math.round((b.rawMaxTokens || b.maxTokens) / 1000)}k used (${Math.round(b.percentage)}%)`,
          '',
          ...[...b.categories].sort((x, y) => y.tokens - x.tokens).slice(0, 12).map(c => `  ${c.name.padEnd(26).slice(0, 26)} ${`${Math.round(c.tokens / 100) / 10}k`.padStart(7)}`),
        ])
      } catch {
        return text('Context', ['No context breakdown on this host.'])
      }
    }
    default: {
      const tl = visibleTasks(dsTasks, now).length || dsLedgerPath ? tasksHeadline(dsTasks, dsLedgerLine()) : null
      return overviewLines({ live, feed, now, tasksLine: tl, theme: th })
    }
  }
}

async function dsDoctor($: EngineInterface): Promise<string> {
  const g = dsTheme.glyphs
  const v = await $.session.version()
  const vOk = versionAtLeast(v.version, MIN_CLAUDE)
  const surfaces = await $.session.surfaces()
  const draws = surfaces.includes('terminal') || surfaces.includes('desktop')
  const rows: string[][] = [
    [vOk ? g.ok : g.bad, 'Claude Code', `${v.version}${vOk ? '' : `: mods need ${MIN_CLAUDE} or newer`}`],
    [g.ok, 'surface', `${surfaces.join(', ') || 'none reported'}: ${draws ? 'the /rw-vigil pane draws here' : 'text only (VS Code: the mods/vscode extension)'}`],
    [dsSw.off ? g.warn : g.ok, 'switches', `${(await $.fs.exists(dsPath('switches.json'))) ? 'file present' : 'shipped defaults'}${g.sep.trim() ? ` ${g.sep.trim()} ` : ', '}kill switch ${dsSw.off ? 'ON' : 'off'}`],
    [g.ok, 'collector', dsRecording() ? 'keeping counts in ~/.claude/revenantworks/vigil/' : 'this session only (/rw-vigil records on)'],
    [dsThemeErrors.length ? g.warn : g.ok, 'theme', `${dsTheme.name}${dsThemeErrors.length ? `, ${dsThemeErrors.length} theme file(s) skipped` : ''}`],
  ]
  const now = await $.clock.now()
  for (const [label, path] of [['meter file', `${dsHome}/.claude/usage-windows.json`], ['feed', dsPath('vigil/feed.json')]] as const) {
    try {
      rows.push([g.ok, label, `${formatAge(now - (await $.fs.stat(path)).mtimeMs)} old`])
    } catch {
      rows.push([g.off, label, 'absent'])
    }
  }
  const pad = Math.max(...rows.map(r => r[1]!.length))
  return [headerText(dsTheme, 'vigil doctor'), ...rows.map(r => `  ${r[0]} ${r[1]!.padEnd(pad)}  ${r[2]}`), '', ...healthLines(await dsHealthNow($, true), dsTheme).map(l => l.text)].join('\n')
}

async function dsPurge($: EngineInterface): Promise<string> {
  for (const key of await $.store.keys()) await $.store.delete(key)
  // The pre-rename dash/ folder goes too.
  const out: string[] = []
  for (const name of ['vigil', 'dash'] as const) {
    const dir = dsPath(name)
    if (name === 'dash' && !(await $.fs.exists(dir).catch(() => false))) continue
    const argv = purgeArgv(dsIsWin, dir)
    if (!argv) {
      out.push(`Refused to run a remove command on ${dir}: the path is not a vigil folder or holds a shell character. Delete it by hand.`)
      continue
    }
    try {
      const r = await $.process.run(argv, { timeoutMs: 10000 })
      out.push(r.exitCode === 0 ? `Removed ${dir}.` : `Could not remove ${dir} (exit ${r.exitCode}). Delete it by hand.`)
    } catch {
      out.push(`Could not run the remove command. Delete ${dir} by hand.`)
    }
  }
  dsMem = []
  dsBuffer = []
  dsSuggest = []
  dsFeed = null
  return [...out, 'The switch file stays; /rw-vigil records off stops new counts.'].join('\n')
}

/** Bundled themes, then the person's theme files; the active one from VIGIL_THEME or theme.json. */
async function dsLoadTheme($: EngineInterface): Promise<void> {
  const files: Array<{ file: string; text: string | null }> = []
  dsLink = parseLink(await dsRead($, dsPath('link.json')))
  // The linked folder first, so a theme file on this machine wins over one of the same name.
  for (const dir of [...(dsLink ? [`${dsLink.folder}/themes`] : []), dsPath('themes')]) {
    try {
      for (const e of (await $.fs.list(dir)).filter(x => x.kind === 'file' && /\.json$/i.test(x.name)).slice(0, 30)) {
        files.push({ file: e.name, text: await dsRead($, `${dir}/${e.name}`) })
      }
    } catch {
      // No such folder: nothing to load from it.
    }
  }
  const d = discoverThemes(files)
  dsThemes = d.themes
  dsThemeErrors = d.errors
  let ccTheme: string | null = null
  try {
    // The Claude Code theme is the /config row keyed "theme" (dark, light, dark-daltonized, light-ansi, auto...).
    const row = (await $.config.list()).find(x => x.key === 'theme')
    ccTheme = typeof row?.value === 'string' ? row.value : null
  } catch {
    // No settings rows on this host: the override and COLORFGBG still decide.
  }
  const saved = await dsRead($, dsPath('theme.json'))
  // The saved background answers what no host tells a mod: whether the app is drawn light or dark.
  dsConsole = consoleBackground(ccTheme, (await dsEnv($, 'THEME_BACKGROUND')) ?? parseBackground(saved), (await $.env.get('COLORFGBG')) ?? null)
  // High contrast is the light set: on a dark console the person's own theme keeps its contrast.
  const contrast = wantsContrast((await dsEnv($, 'THEME_CONTRAST')) ?? null, ccTheme) && dsConsole.bg === 'light'
  const p = pickTheme(d.themes, (await dsEnv($, 'THEME')) ?? null, parseActive(saved), contrast)
  dsThemeBase = p.theme
  dsTheme = resolveVariant(p.theme, dsConsole.bg).theme
  // One notice per problem a session: a bad file falls back to neutral, never stops the dashboard.
  const notice = p.notice ?? (d.errors.length ? `vigil: theme file skipped (${d.errors[0]}). /rw-vigil theme lists the themes.` : null)
  if (notice && notice !== dsThemeNoticed) {
    dsThemeNoticed = notice
    await dsSay($, notice)
  }
}

/** theme.json keeps the choice and the console's background together. */
async function dsSaveThemeChoice($: EngineInterface, active: string | null, background: ConsoleBg | null): Promise<void> {
  await $.fs.write(dsPath('theme.json'), `${JSON.stringify({ ...(active ? { active } : {}), ...(background ? { background } : {}) })}\n`)
  await dsLoadTheme($)
  // A module variable alone redraws nothing: an open pane and the band take the new colours now.
  await dsRedraw($)
}

async function dsApplyTheme($: EngineInterface, name: string): Promise<string> {
  await dsSaveThemeChoice($, name, parseBackground(await dsRead($, dsPath('theme.json'))))
  return linesText(themeApplied(dsThemes[name]!.theme, dsConsole, (await dsEnv($, 'THEME')) ?? null))
}

async function dsApplyBackground($: EngineInterface, bg: ConsoleBg | 'auto'): Promise<string> {
  await dsSaveThemeChoice($, parseActive(await dsRead($, dsPath('theme.json'))), bg === 'auto' ? null : bg)
  return bg === 'auto' ? `Console background: automatic, now ${dsConsole.bg}.` : `Console background: ${bg}.`
}

/** /rw-vigil theme: the list, a name to apply, or the console's background. A theme of your own is a JSON file. */
async function dsThemeVerb($: EngineInterface, rest: string): Promise<{ text: string }> {
  await dsLoadTheme($)
  const [sub = '', arg = ''] = rest.toLowerCase().split(/\s+/).filter(Boolean)
  if (!sub || sub === 'list') {
    dsView = 'theme'
    await update($, dsPaneRev, n => (n ?? 0) + 1)
    if (dsOn('D3') && (await dsCanDraw($))) await $.ui.open({ id: 'vigil', title: 'vigil' })
    return { text: linesText(themeLines(dsThemes, dsTheme.name, dsTheme, dsThemeErrors, dsConsole, dsPath('themes'))) }
  }
  if (sub === 'background') {
    if (arg !== 'dark' && arg !== 'light' && arg !== 'auto') return { text: 'Usage: /rw-vigil theme background dark|light|auto' }
    return { text: await dsApplyBackground($, arg) }
  }
  if (!dsThemes[sub]) return { text: `No theme "${sub.slice(0, 40)}". Themes: ${Object.keys(dsThemes).join(', ')}.` }
  return { text: await dsApplyTheme($, sub) }
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
  // The command comes first: a later step that throws must not leave /rw-vigil unknown for the
  // whole session (seen on the PC 2026-10-24). A failed setup is retried by the command's own hook.
  try {
    await $.command.register({ name: 'rw-vigil', description: 'vigil: meters, skills, health and suggestions in one view', argumentHint: 'skills · tasks · health · suggest · theme · switches · help' })
  } catch {
    // A name the host refuses is skipped; setup goes on.
  }
  await dsLoadSwitches($)
  await dsLoadTheme($)
  dsSuggest = parseSuggestions(await dsRead($, dsPath('vigil/suggestions.json')))
  dsLayout = parseLayout(await $.store.get('layout'))
  dsBandHidden = (await $.store.get('bandHidden')) === true
  await dsLoadTiles($)
  await dsLoadSpend($)
  // Hash keys only: text keys left by an older build are dropped on read and never written back.
  dsTaskHist = sanitizeTaskHistory(await $.store.get('taskHistory'))
  if (dsOn('D14')) await dsRegisterShort($)
  if (dsOn('D4')) {
    try {
      await $.tool.register({
        name: 'vigil_read',
        description: 'Read the vigil feed on demand: skills fired (slash or automatic), failures, likely misroutes, tokens by skill, the 5-hour and weekly meters, context, cache, background tasks, health and the suggestion queue. Read-only; counts only, never text.',
        inputSchema: { type: 'object', properties: { view: { type: 'string', enum: ['overview', 'skills', 'meters', 'health', 'tasks', 'suggest'] } } },
      })
    } catch {
      // A name the host refuses is skipped; setup goes on.
    }
  }
  dsAskRecords = !dsSw.off && (await $.store.get('recordsAnswered')) !== true && dsSw.features.D1 === undefined
  dsPush({ t: await $.clock.now(), s: dsSKey, k: 'session' })
  await dsRefreshRun($)
  await dsHeartbeat($)
  $.clock.every(60_000, async () => {
    await dsLoadSwitches($)
    const was = `${dsTheme.name}/${dsConsole.bg}`
    await dsLoadTheme($)
    // Another session switched the theme: this one follows at once, not on its next press.
    if (`${dsTheme.name}/${dsConsole.bg}` !== was) await dsRedraw($)
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

/** The switch file changes only through /rw-vigil, which the person types (C2). */
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

/** D14: /rw and every /rw-<short>. A name the host refuses is skipped; the rest still register. */
async function dsRegisterShort($: EngineInterface): Promise<void> {
  const specs = [
    { name: RW, description: 'Revenantworks skills: /rw <name> runs one; bare /rw lists them', argumentHint: '<skill> [what you want]' },
    ...RW_SKILLS.map(s => ({ name: `${RW_PREFIX}${s.short}`, description: rwDescription(s), argumentHint: '[what you want]' })),
  ]
  for (const spec of specs) {
    try {
      await $.command.register(spec)
    } catch {
      // Skipped; the long name still works.
    }
  }
}

/**
 * Hand a short command to the skill's long command. The run is queued on the clock, after this
 * hook returns: a $.command.run inside the hook the turn waits on is refused (PC test, 2026-10-23).
 */
async function dsLaunch($: EngineInterface, name: string, args: string): Promise<CommandRunResult> {
  await dsEnsure($)
  if (!dsOn('D14')) return { text: 'Short commands are off. /rw-vigil on short-commands turns them on; the long names still work.' }
  const s = bySkill(name)
  if (!s) return { text: [`No Revenantworks skill named "${name}".`, ...rwListLines()].join('\n') }
  let names: string[] = []
  try {
    names = (await $.command.list()).map(c => c.name)
  } catch {
    // An unreadable list falls back to the pack's own command.
  }
  const target = resolveTarget(s, names) ?? (names.length === 0 ? `${s.pack}:${s.member}` : null)
  if (!target) return { text: `${s.short} is not installed. Install its pack: /plugin install ${s.pack}@revenantworks` }
  $.clock.after(HANDOFF_MS, () => {
    void $.command.run({ command: target, args }).catch(() => undefined)
  })
  return {}
}

/** /rw-vigil. */
async function dsCommand($: EngineInterface, e: CommandRunInput): Promise<CommandRunResult> {
  try {
    await dsEnsure($)
  } catch (err) {
    return { text: `vigil could not start: ${err instanceof Error ? err.message : String(err)}. Send this line to whoever maintains vigil.` }
  }
  // The desktop app sends what its person types as the SDK host's turn; a routine has no surface.
  const kind = e.origin?.kind
  const isOwner = kind === 'composer' || kind === 'bridge' || (kind === 'sdk' && (await $.session.surfaces()).includes('desktop'))
  const { verb, rest } = parseDashArgs(e.args ?? '')
  const now = await $.clock.now()
  const nowIso = new Date(now).toISOString()
  const show = async (view: View): Promise<{ text: string }> => {
    dsView = view
    const lines = await dsLines($, view)
    // An open pane is already up, so opening it again draws nothing new: bump its revision so a
    // typed /rw-vigil <verb> switches the view at once (the hit-or-miss switch, 2026-10-15).
    await update($, dsPaneRev, n => (n ?? 0) + 1)
    if (dsOn('D3') && (await dsCanDraw($))) await $.ui.open({ id: 'vigil', title: 'vigil' })
    return { text: linesText(lines) }
  }
  switch (verb) {
    case '':
    case 'board':
      await dsRoll($)
      await dsLoadSpend($)
      await dsLoadTiles($)
      return show('board')
    case 'overview':
      await dsRoll($)
      return show('overview')
    case 'hide':
      await dsSetBandHidden($, true)
      await $.ui.close({ id: 'vigil' }).catch(() => undefined)
      return { text: BAND_HIDDEN_NOTE }
    case 'show':
      await dsSetBandHidden($, false)
      return { text: 'The strip above the prompt is back. /rw-vigil hide hides it again.' }
    case 'tile': {
      const [name, op = 'open'] = rest.toLowerCase().split(/\s+/)
      if (!isTile(name)) return { text: `No tile "${(name ?? '').slice(0, 20)}". Tiles: ${arranged(dsLayout).join(', ')}.` }
      if (op !== 'open' && op !== 'up' && op !== 'down' && op !== 'pin' && op !== 'collapse') return { text: 'Usage: /rw-vigil tile <name> open|up|down|pin|collapse' }
      await dsRoll($)
      await dsPress($, { kind: 'tile', op, id: name })
      return show(op === 'open' ? (name === 'inbox' ? 'cards' : 'detail') : 'board')
    }
    case 'tiles': {
      const [sub, src] = rest.toLowerCase().split(/\s+/)
      await dsLoadTiles($)
      if (!sub) return show('tiles')
      if (sub !== 'build') return { text: 'Usage: /rw-vigil tiles [build <source>]' }
      if (!isBuildSource(src)) return { text: `Usage: /rw-vigil tiles build ${Object.keys(BUILD_SOURCES).join('|')}` }
      if (!isOwner) return { text: 'Only you can start a tile scan, by typing /rw-vigil tiles build yourself.' }
      return { text: await dsBuild($, src) }
    }
    case 'link': {
      if (!rest) return { text: dsLink ? `Linked: ${dsLink.folder} (tiles, themes); @/ is ${dsLink.root}.\n/rw-vigil link off stops it; no file there changes.` : 'Not linked. /rw-vigil link <folder holding your clones> <your private folder with tiles/ and themes/>' }
      if (!isOwner) return { text: 'Only you can set the link, by typing /rw-vigil link yourself.' }
      const [root, folder] = rest.split(/\s+/)
      if (rest.toLowerCase() !== 'off' && (!root || !folder)) return { text: 'Usage: /rw-vigil link <folder holding your clones> <your private folder with tiles/ and themes/>' }
      await $.fs.write(dsPath('link.json'), `${JSON.stringify(rest.toLowerCase() === 'off' ? {} : { root, folder })}\n`)
      await dsLoadTheme($)
      await dsLoadTiles($)
      await dsRedraw($)
      return show('tiles')
    }
    case 'layout':
      if (rest.toLowerCase() !== 'reset') return { text: 'Usage: /rw-vigil layout reset' }
      await dsSaveLayout($, parseLayout(null, dsMine.map(t => tileKey(t.id))))
      return show('board')
    case 'inbox':
    case 'cards':
      await dsRoll($)
      return show('cards')
    case 'settings':
      await dsLoadSpend($)
      return show('settings')
    case 'spend': {
      const [word, mode, want] = rest.toLowerCase().split(/\s+/)
      if (word !== 'auto' || !isAutoMode(mode) || (want !== 'on' && want !== 'off')) return { text: `Usage: /rw-vigil spend auto ${AUTO_MODES.join('|')} on|off` }
      if (!isOwner) return { text: 'Only you can change a spend mode, by typing /rw-vigil spend yourself.' }
      return { text: await dsSetAuto($, mode, want === 'on') }
    }
    case 'skills': {
      await dsRoll($)
      const sub = rest.toLowerCase()
      return show(sub === 'all' ? 'skills-all' : sub === 'dupes' ? 'dupes' : 'skills')
    }
    case 'meters':
    case 'tasks':
    case 'context':
      await dsRoll($)
      return show(verb)
    case 'health':
      await dsRoll($, true)
      return show('health')
    case 'suggest': {
      await dsRoll($)
      const [act = '', ...refWords] = rest.split(/\s+/)
      if (act === 'accept' || act === 'dismiss' || act === 'snooze') {
        if (!isOwner) return { text: 'Only you can act on a suggestion, by typing /rw-vigil suggest yourself.' }
        const r = actOn(dsSuggest, act, refWords.join(' '), now)
        dsSuggest = r.rows
        await dsSaveSuggest($)
        if (act === 'accept' && r.hit) await dsDoIt($, r.hit.id)
        if (dsNote && !dsSuggest.some(x => x.id === dsNote?.id && x.state === 'shown')) dsNote = null
        await dsRedraw($)
        return { text: r.text }
      }
      return show('cards')
    }
    case 'doctor':
      return { text: await dsDoctor($) }
    case 'purge':
      if (!isOwner) return { text: 'Only you can purge, by typing /rw-vigil purge yourself.' }
      return { text: await dsPurge($) }
    case 'help':
      return { text: [headerText(dsTheme, 'vigil commands'), ...HELP.map(l => `  ${l}`)].join('\n') }
    case 'theme':
      return dsThemeVerb($, rest)
    case 'switches':
    case 'list':
    case 'on':
    case 'off':
    case 'records': {
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
        // A switch can show or hide a band row (the records ask, D3 tasks, D5 notes).
        await dsBandBump($)
      }
      return { text: r.text }
    }
    default:
      return { text: [`Unknown: /rw-vigil ${verb}.`, '', ...HELP.map(l => `  ${l}`)].join('\n') }
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    // A setup that throws must not hold the session's own start; /rw-vigil retries it and says why.
    await dsEnsure($).catch(() => undefined)
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await dsEnsure($)
    const now = await $.clock.now()
    const prev = dsLive
    dsLive = liveFromMeasure(e.rateLimits, e.context.percent, e.cost?.usd ?? null, dsLastHit, now)
    // One toast when a meter crosses 80% or 90%, never a repeat until it drops back under 80.
    for (const [key, label] of [['five', '5-hour'], ['week', 'Weekly'], ['ctx', 'Context']] as const) {
      const cur = dsLive[key]
      if (cur !== null && cur < 80) dsAlerted[key] = 0
      const hit = crossed(prev?.[key] ?? null, cur).filter(l => l > dsAlerted[key]).pop()
      if (hit !== undefined && dsOn('D2') && (await dsCanDraw($))) {
        dsAlerted[key] = hit
        $.ui.toast(`${label} meter passed ${hit}%.`)
      }
    }
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
      // A burst carries several notifications in one submission: settle each.
      for (const n of parseTaskNotifications(e.text)) {
        const t = dsTasks.find(x => x.id === n.id)
        dsTasks = t?.kind === 'agent' ? endAgent(dsTasks, n.id, n.status, now) : settleTask(dsTasks, n.id, n.status, now)
        if (t?.sig && t.state === 'running' && n.status === 'completed') {
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
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('skill.prompt', async ($, e, next) => {
    await dsEnsure($)
    const now = await $.clock.now()
    const slash = dsLastSlash && now - dsLastSlash.at < 30_000 && (dsLastSlash.name === e.skill || e.skill.endsWith(`:${dsLastSlash.name}`) || e.skill.endsWith(`-${dsLastSlash.name}`))
    await dsSkillFired($, e.skill, slash ? 'slash' : 'auto')
    return next(e)
  }).catch(($, e, next) => {
    dsCaught += 1
    return next(e)
  })

  // Only the dialogs the person sees. `tool.check` saying "ask" also covers every call auto mode's
  // classifier settles on its own, which the person never sees (owner 2026-10-13: report the
  // prompts I answer, not the permissions used). The classic PermissionRequest fires as a dialog
  // is about to open; vigil records its shape and answers nothing. It also fires where no dialog
  // can open (`-p`, a routine) and the call is denied on its own: no surface, no prompt, no count.
  on('classic.PermissionRequest', async ($, e, next) => {
    await dsEnsure($)
    if ((await $.session.surfaces()).length === 0) return next(e)
    const shape = permissionShape(e.tool_name, e.tool_input as Record<string, unknown> | undefined)
    if (shape) dsPush({ t: await $.clock.now(), s: dsSKey, k: 'prompt', shape })
    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.call', async ($, e, next) => {
    await dsEnsure($)
    if (e.tool === 'mcp__vigil__vigil_read') {
      if (!dsOn('D4')) return { deny: 'vigil_read is switched off (/rw-vigil on read-tool).' }
      const view = String((e as { view?: unknown }).view ?? 'overview') as View
      await dsRoll($)
      // An MCP tool result is a string or content blocks; a { text } object fails the host's output check.
      if (view === 'suggest') return { result: linesText(await dsLines($, 'cards')) }
      return { result: linesText(await dsLines($, ['overview', 'skills', 'meters', 'health', 'tasks'].includes(view) ? view : 'overview')) }
    }
    const shell = dsShell(e)
    const filePath = typeof (e as { file_path?: unknown }).file_path === 'string' ? (e as { file_path: string }).file_path : null
    // C2: the switch file holds the person's choices; it changes only through /rw-vigil, which they type.
    if ((e.tool === 'Edit' || e.tool === 'Write') && filePath && /revenantworks[\\/]switches\.json$/i.test(filePath)) {
      return { deny: 'vigil: the mods switch file changes only through /rw-vigil, which you type.' }
    }
    if (shell && dsWritesSwitchFile(shell.command, shell.shell)) {
      return { deny: 'vigil: this would write the mods switch file; it changes only through /rw-vigil, which you type.' }
    }
    const now = await $.clock.now()
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
    }
    if (e.tool === 'Edit' && filePath && ok) {
      const r = onEdit(dsMis, fnv1a(normPath(filePath)), fnv1a(e.old_string), fnv1a(e.new_string), now)
      dsMis = r.st
      if (r.misroute) dsPush({ t: now, s: dsSKey, k: 'misroute', skill: r.misroute, why: 'revert' })
    }
    // F3, F3f: background tasks and agents. A call from an agent marked ended means it runs again.
    if (e.agentId && dsTasks.some(t => t.id === e.agentId && t.state !== 'running')) dsTasks = reopenTask(dsTasks, e.agentId)
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
          ...(e.agentId ? { parent: e.agentId } : {}),
          ...(typeof timeout === 'number' ? { timeoutMs: timeout } : {}),
          ...(typeof result.outputFile === 'string' ? { outputFile: result.outputFile } : {}),
        })
      }
      if (e.tool === 'TaskStop') {
        const stopId = (e as { task_id?: unknown }).task_id
        if (typeof stopId === 'string') dsTasks = settleTask(dsTasks, stopId, 'killed', now)
      }
    }
    return ran
  }).catch(($, e, next) => {
    dsCaught += 1
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    await dsEnsure($)
    const now = await $.clock.now()
    // A subagent's loop runs as one turn: its end is the agent's end signal (a handback included).
    if (e.agentId) dsTasks = endAgent(dsTasks, e.agentId, e.isAborted ? 'killed' : e.reason === 'answer' ? 'completed' : 'failed', now)
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
      if (!e.agentId && isRecordingOn(dsSw, 'D7') && dsRunOwned && dsLedgerPath) {
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
        dsSkillSources = Object.fromEntries((b?.skills?.skillFrontmatter ?? []).filter(s => typeof s.source === 'string').map(s => [s.name, s.source]))
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
        await dsBandBump($)
        if (dsRecording()) await dsWrite($, dsPath('vigil/suggestions.json'), serializeSuggestions(dsSuggest, now))
        if (!(await dsCanDraw($))) dsNotes.push(`vigil suggests: ${p.note.title}\n  why: ${p.note.evidence}\n  /rw-vigil suggest to accept, dismiss or snooze`)
      }
    }
    if (dsAskRecords && !dsAskedAsText && !(await dsCanDraw($))) {
      dsAskedAsText = true
      dsNotes.push('vigil keeps counts for this session only until you say yes: /rw-vigil records on keeps them across sessions (counts, never text); /rw-vigil records off stops asking.')
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

  // D14: one command.run hook per name (the engine matches a hook to one command).
  on('command.run', { command: RW }, async ($, e) => {
    const { skill, rest } = parseRw(e.args ?? '')
    if (!skill) {
      await dsEnsure($)
      return { text: rwListLines().join('\n') }
    }
    return dsLaunch($, skill, rest)
  })
  for (const s of RW_SKILLS) on('command.run', { command: `${RW_PREFIX}${s.short}` }, ($, e) => dsLaunch($, s.short, e.args ?? ''))

  // D14: the long names leave the typeahead and /help while the short ones serve them.
  on('command.describe', async ($, e, next) => {
    const r = await next(e)
    if (!isLongName(e.command)) return r
    await dsEnsure($)
    return dsOn('D14') ? { ...r, isHidden: true } : r
  })


  on('command.run', { command: 'rw-vigil' }, dsCommand)

  on('ui.render', async ($, e, next) => {
    await dsEnsure($)
    if (e.component === 'Pane' && e.requestId === 'vigil') {
      const { Box, Button, Text } = $.ui.resolve(e)
      // Reading the revision subscribes this pane; a press bumps it, which redraws it at once. An
      // invalidate alone could be folded away, so a press only showed on the next click (2026-10-13).
      await read($, dsPaneRev)
      const onPress = (p: Press) => async () => {
        await dsPress($, p)
        await update($, dsPaneRev, n => (n ?? 0) + 1)
        // A pane press can change the band too: a dismiss or snooze of the noted suggestion.
        await dsBandBump($)
      }
      const tabs = (
        <Box key="tabs" justifyContent="space-between" columnGap={2}>
          <Box flexWrap="wrap" columnGap={2}>
            {navTabs(dsView).map(t => (t.active
              ? <Button key={`view:${t.view}`} plain onPress={onPress({ kind: 'view', view: t.view })}><Text bold color={dsTheme.colors.accent}>{t.label}</Text></Button>
              : <Button key={`view:${t.view}`} label={t.label} plain dimColor onPress={onPress({ kind: 'view', view: t.view })} />))}
          </Box>
          <Button key="close" label="Close" hotkey="q" role="dismiss" plain dimColor onPress={() => $.ui.close({ id: 'vigil' })} />
        </Box>
      )
      if (dsView === 'board' || dsView === 'detail' || dsView === 'cards' || dsView === 'settings' || dsView === 'tiles') {
        const table = $.ui.resolve(e)
        return <Box flexDirection="column" rowGap={1}>{tabs}{await dsBoardTree($, table, onPress, e.props.bodyColumns)}</Box>
      }
      const lines = await dsLines($, dsView)
      // The theme paints each tone; a colour is a theme key or a hex the person chose.
      return (
        <Box flexDirection="column" rowGap={1}>
          {tabs}
          <Box flexDirection="column">
          {lines.map((l, i) => {
            const s = l.color ? { color: l.color, bold: false } : toneStyle(dsTheme, l.tone)
            const text = <Text color={s.color} bold={s.bold} wrap="truncate-end">{l.text || ' '}</Text>
            // Keys are addresses: stable across redraws, so a test or a hotkey names what it presses.
            // A Button takes a string label only before 2.1.295, so a row keeps its coloured Text and
            // gains a small Open; the back row is a Button of its own.
            if (l.buttons?.length) {
              return (
                <Box key={`d${i}`} columnGap={1}>
                  {text}
                  {l.buttons.map((b, j) => <Button key={b.press.kind === 'theme' ? `theme:${b.press.name}` : b.press.kind === 'background' ? `bg:${b.press.bg}` : b.press.kind === 'view' ? `view:${b.press.view}` : `d${i}b${j}`} label={b.label} plain dimColor onPress={onPress(b.press)} />)}
                </Box>
              )
            }
            return <Text key={`d${i}`} color={s.color} bold={s.bold} wrap="truncate-end">{l.text || ' '}</Text>
          })}
          </Box>
        </Box>
      )
    }
    if (e.component !== 'AbovePrompt' || e.props.hasSurvey || dsBandHidden) return next(e)
    const { Box, Button, Text } = $.ui.resolve(e)
    // Reading the band's revision subscribes it; every band press bumps it, so the press shows at
    // once rather than on the next unrelated redraw (the dead Later button, 2026-10-15).
    await read($, dsBandRev)
    const bump = () => dsBandBump($)
    const now = await $.clock.now()
    const rows: JSX.Element[] = []
    // The glance strip: three readings, a mark only when something needs you, and its two controls.
    let glance: JSX.Element | null = null
    if (dsOn('D2')) {
      const gl = glanceOf(await dsBoardData($))
      if (gl.rings.some(r => r.pct !== null) || gl.needsYou || gl.shield) {
        glance = (
          <Box columnGap={2}>
            {glanceMeters(gl).map(m => (
              <Box key={`m-${m.label}`} columnGap={1}>
                <Text dimColor>{m.label}</Text>
                <Text bold color={m.tone ? toneStyle(dsTheme, m.tone).color : undefined}>{m.value}</Text>
              </Box>
            ))}
            {gl.shield ? <Text color={gl.shield.red ? dsTheme.colors.bad : dsTheme.colors.dim}>{shieldText(gl.shield)}</Text> : null}
            {gl.needsYou ? <Text color={dsTheme.colors.accent} wrap="truncate-end">{`${dsTheme.glyphs.on} ${gl.needsYou}`}</Text> : null}
          </Box>
        )
      }
    }
    if (dsUndo) {
      const u = dsUndo
      rows.push(
        <Box key="undo" columnGap={1}>
          <Text dimColor wrap="truncate-end">{`Hidden: ${u.title}`}</Text>
          <Button key="undo-btn" label="Undo" onPress={async () => { await dsPress($, { kind: 'card', op: 'undo', id: u.id }); await bump(); await update($, dsPaneRev, n => (n ?? 0) + 1) }} />
        </Box>,
      )
    }
    if (dsAskRecords) {
      rows.push(
        <Box key="ask" columnGap={1}>
          <Text bold color={dsTheme.colors.accent}>vigil</Text>
          <Text dimColor wrap="truncate-end">keep counts across sessions? Counts, hashes and shapes only, never text; on this machine.</Text>
          <Button key="ask-on" label="Turn on" onPress={async () => {
            dsAskRecords = false
            await $.store.set('recordsAnswered', true)
            await dsSaveSwitches($, applySwitchCommand(dsSw, 'records on', true, new Date(await $.clock.now()).toISOString()).sw)
            dsBuffer = [...dsMem]
            await bump()
          }} />
          <Button key="ask-off" label="Keep off" onPress={async () => {
            dsAskRecords = false
            await $.store.set('recordsAnswered', true)
            await dsSaveSwitches($, applySwitchCommand(dsSw, 'records off', true, new Date(await $.clock.now()).toISOString()).sw)
            await bump()
          }} />
          <Button key="ask-later" label="Ask me later" onPress={async () => { dsAskRecords = false; await bump() }} />
        </Box>,
      )
    }
    if (dsOn('D5') && dsNote) {
      const note = dsNote
      rows.push(
        <Box key="note" columnGap={1}>
          <Text bold color={dsTheme.colors.accent}>vigil suggests</Text>
          <Text wrap="truncate-end">{`${note.title} (${note.evidence})`}</Text>
          <Button key="note-show" label="Show" onPress={async () => { dsNote = null; dsView = 'cards'; await bump(); await update($, dsPaneRev, n => (n ?? 0) + 1); await $.ui.open({ id: 'vigil', title: 'vigil' }) }} />
          <Button key="note-later" label="Later" onPress={async () => { dsNote = null; await bump() }} />
        </Box>,
      )
    }
    if (dsOn('D3')) {
      const running = visibleTasks(dsTasks, now)
      if (running.length > 0) rows.push(<Text key="tasks" dimColor wrap="truncate-end">{`${tasksHeadline(dsTasks, null)} · /rw-vigil tasks`}</Text>)
    }
    if (rows.length === 0 && !glance) return next(e)
    const open = async () => { dsView = 'board'; await update($, dsPaneRev, n => (n ?? 0) + 1); await $.ui.open({ id: 'vigil', title: 'vigil' }) }
    const hide = async () => { await dsSetBandHidden($, true); $.ui.toast(BAND_HIDDEN_NOTE) }
    // One head row carries the controls, so every row the band can show has a way out.
    const headRow = (
      <Box key="band-head" justifyContent="space-between" columnGap={2}>
        {glance ?? <Text bold color={dsTheme.colors.accent}>vigil</Text>}
        <Box columnGap={2}>
          <Button key="glance-open" label="Board" plain dimColor onPress={open} />
          <Button key="band-hide" label="Hide" role="dismiss" plain dimColor onPress={hide} />
        </Box>
      </Box>
    )
    return <Box flexDirection="column">{headRow}{rows}{await next(e)}</Box>
  })
}

