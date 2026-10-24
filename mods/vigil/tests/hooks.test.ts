import type {
  AgentInfo, CommandPresentation, CommandRunInput, FsEntry, FsStat, On, PromptSubmitInput, RenderSurface,
  SessionUsage, SiteScroll, TurnCompleteInput,
} from 'claude-code'
import type { Engine } from 'claude-code/testing'
import { describe, expect, mock, test } from 'claude-code/testing'

import { DAY, sessionKey, serializeEvents, type DashEvent } from '../hooks/collector-logic'
import { defaultSwitches, parseSwitches, serializeSwitches } from '../hooks/lib/switches'
import { fnv1a, heartbeatAlive, mergeHeartbeat } from '../hooks/lib/util'

const NOW = Date.UTC(2026, 9, 8, 12)
const HOME = '/u/t'
const SW = `${HOME}/.claude/revenantworks/switches.json`
const DIR = `${HOME}/.claude/revenantworks/vigil`
const RECORDS = serializeSwitches({ ...defaultSwitches(), features: { D1: true } })

// Text that must never reach a file: a prompt, a command's arguments, a skill's body, a path.
const PROMPT = 'please refactor the billing module for the Falcon client'
const CMD_ARG = 'customer-ledger-2026.csv'
const SKILL_BODY = 'SKILL BODY: confidential procedure text'
const PATH = '/r/src/billing/secret-plan.ts'

// On Windows the test host hands a stub the resolved path (drive letter, backslashes); key files by the posix form.
const key = (p: string) => p.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')
type FsX = { list?: (path: string) => FsEntry[]; stat?: (path: string) => FsStat | undefined }
/** Fixture tasks: the agent list the engine returns, and a tool result per call description. */
type TaskFx = { agents?: AgentInfo[]; results?: Record<string, unknown>; brokenStore?: boolean; registered?: string[] }

// Typed engine inputs and results (obs 0344): no stub casts its shape away, so a stub that drifts
// from the host's type fails the type check instead of passing a shape the host would refuse.
const PRESENT: CommandPresentation = { isFullscreen: false, columns: 100 }
/** A /command as the composer sends it; the host adds how it is presented. */
const cmd = (e: Omit<CommandRunInput, 'presentation'>): CommandRunInput => ({ ...e, presentation: PRESENT })
/** A submitted prompt; the stubbed engine beneath never waits on a turn. */
const submit = (e: Omit<PromptSubmitInput, 'wait'>): PromptSubmitInput => ({ ...e, wait: false })
/** A tool call made inside a subagent's loop: the host stamps the agent's id beside the tool's own input.
 *  ToolCallArgs has no agentId, so this forges a host-stamped field on purpose (as shroud's kept cast does). */
type ToolCallArg = Parameters<Engine['tool']['call']>[0]
const fromAgent = <I extends ToolCallArg>(agentId: string, input: I): I & { agentId: string } => ({ ...input, agentId })
const SCROLL: SiteScroll = { offset: 0, bodyRows: 40 }
const USAGE: SessionUsage = {
  startedAt: NOW,
  rateLimits: [],
  context: {
    window: 200000,
    breakdown: {
      categories: [], totalTokens: 0, maxTokens: 200000, rawMaxTokens: 200000, autocompactSource: 'model-default', percentage: 0,
      gridRows: [], model: 'm', memoryFiles: [], mcpTools: [], agents: [], isAutoCompactEnabled: false, apiUsage: null,
      skills: { totalSkills: 2, includedSkills: 2, tokens: 10, skillFrontmatter: [{ name: 'alpha', source: 'plugin', tokens: 5 }, { name: 'beta', source: 'plugin', tokens: 5 }] },
    },
  },
}

const world = (on: On, files: Record<string, string>, surfaces: RenderSurface[] = ['terminal'], fsx: FsX = {}, env: Record<string, string> = {}, fx: TaskFx = {}) => {
  if (fx.brokenStore) on('store.get', async () => { throw new Error('store unavailable') })
  else mock.store(on)
  mock.clock(on, { now: NOW })
  on('env.get', async ($, e) => ({ value: e.name === 'HOME' || e.name === 'USERPROFILE' ? HOME : env[e.name] }))
  on('session.id', async () => ({ value: 'sess-1' }))
  on('session.cwd', async () => ({ value: '/r' }))
  on('session.repo', async () => ({ value: { root: '/r', remote: null, internal: false, name: null } }))
  on('session.surfaces', async () => ({ value: surfaces }))
  on('session.version', async () => ({ value: { version: '2.1.295' } }))
  on('session.usage', async () => ({ value: USAGE }))
  on('fs.read', async ($, e) => {
    const text = files[key(e.path)]
    if (text !== undefined) return { value: text }
    throw new Error('ENOENT')
  })
  on('fs.write', async ($, e) => {
    files[key(e.path)] = e.text
    return { value: undefined }
  })
  on('fs.exists', async ($, e) => ({ value: files[key(e.path)] !== undefined }))
  on('fs.list', async ($, e) => ({ value: fsx.list?.(key(e.path)) ?? [] }))
  on('fs.stat', async ($, e) => {
    const st = fsx.stat?.(key(e.path))
    if (st === undefined) throw new Error('ENOENT')
    return { value: st }
  })
  on('process.run', async () => ({ value: { exitCode: 1, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }))
  on('command.register', async ($, e) => {
    fx.registered?.push(e.name)
    return { value: { command: e.name } }
  })
  on('tool.register', async () => ({ value: { tool: 'vigil_read' } }))
  on('agent.list', async () => ({ value: fx.agents ?? [] }))
  on('ui.open', async () => ({ value: { isPlaced: true } }))
  on('prompt.submit', async ($, e) => ({ text: e.text }))
  on('skill.prompt', async ($, e) => ({ text: e.text }))
  on('turn.complete', async () => ({ text: '' }))
  on('tool.call', async ($, e) => ({ result: fx.results?.[String((e as { description?: unknown }).description)] ?? { stdout: '', stderr: '', interrupted: false } }))
}

/** A short session: a typed prompt, an automatic skill, a command with arguments, an edit, a turn. */
const session = async ($: Engine) => {
  await $.prompt.submit(submit({ text: PROMPT, origin: { kind: 'composer' } }))
  await $.skill.prompt({ skill: 'alpha', text: SKILL_BODY })
  await $.tool.call({ tool: 'Bash', command: `python3 tools/import.py --input ${CMD_ARG} -v` })
  await $.tool.call({ tool: 'Edit', file_path: PATH, old_string: 'a', new_string: 'b' })
  await $.turn.complete({ answer: 'done', durationMs: 10, isAborted: false, turnId: 't1', reason: 'answer', usage: { input_tokens: 100, output_tokens: 50, cache_read_input_tokens: 900, cache_creation_input_tokens: 0, model: 'm' } })
}

const dashFiles = (files: Record<string, string>) => Object.entries(files).filter(([k]) => k.startsWith(DIR))

describe('a setup that fails', () => {
  test('/rw-vigil is still registered and says why, and the session still starts', async ($, on) => {
    const names: string[] = []
    world(on, {}, ['terminal'], {}, {}, { brokenStore: true, registered: names })
    on('session.start', async ($, e) => ({ cwd: e.cwd }))
    await $.session.start({ cwd: '/r', surface: 'terminal', isInteractive: true })
    expect(names).toContain('rw-vigil')
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: '', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/vigil could not start: .*store\.get/)
  })
})

describe('the collector', () => {
  test('before the records yes, nothing is written; the session still shows', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files)
    await session($)
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: 'skills', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/alpha +1 +0 +1 +0 +0 /)
    expect(dashFiles(files)).toEqual([])
  })

  test('with the yes it writes events.jsonl and feed.json, and no prompt, command, skill text or path', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    await session($)
    await $.command.run(cmd({ command: 'rw-vigil', args: '', origin: { kind: 'composer' } }))
    const written = dashFiles(files)
    expect(written.map(([k]) => k.slice(DIR.length + 1)).sort()).toEqual(['events.jsonl', 'feed.json', 'suggestions.json'])
    const all = written.map(([, v]) => v).join('\n')
    for (const secret of [PROMPT, 'Falcon', CMD_ARG, SKILL_BODY, 'confidential', PATH, 'secret-plan', 'billing']) expect(all).not.toContain(secret)
    expect(all).toContain('"shape":"python3 *.py --input -v"')
    const feed = JSON.parse(files[`${DIR}/feed.json`]!) as { skills: Array<{ name: string; listed: boolean; tokens7: number }> }
    expect(feed.skills.find(s => s.name === 'alpha')).toMatchObject({ listed: true, tokens7: 1050 })
    expect(feed.skills.find(s => s.name === 'beta')?.listed).toBe(true)
  })

  test('a permission dialog you saw is counted as a prompt; nothing else is', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    on('classic.PermissionRequest', async () => ({}))   // the engine beneath: the dialog opens
    await session($)
    for (let i = 0; i < 3; i++) await $.classic.PermissionRequest({ tool_name: 'Bash', tool_input: { command: `docker compose up ${CMD_ARG}` } })
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    const events = files[`${DIR}/events.jsonl`] ?? ''
    expect(events.match(/"k":"prompt","shape":"bash docker compose"/g)?.length).toBe(3)
    expect(events).not.toMatch(/"k":"perm"/)
    expect(events).not.toContain(CMD_ARG)
    expect(files[`${DIR}/suggestions.json`]).toMatch(/"key": "prompt:bash docker compose"/)
  })

  test('where no dialog can open (-p, a routine) a permission request is not a prompt', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files, [])
    on('classic.PermissionRequest', async () => ({}))
    await session($)
    for (let i = 0; i < 3; i++) await $.classic.PermissionRequest({ tool_name: 'Bash', tool_input: { command: 'docker compose up' } })
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    expect(files[`${DIR}/events.jsonl`] ?? '').not.toMatch(/"k":"prompt"/)
  })

  test('a different skill soon after an automatic one is a likely misroute', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    await $.skill.prompt({ skill: 'alpha', text: 'x' })
    await $.skill.prompt({ skill: 'beta', text: 'y' })
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: 'skills', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/alpha +1 +0 +1 +0 +1 /)
  })

  test('a typed /name is a slash fire', async ($, on) => {
    world(on, {})
    await $.prompt.submit(submit({ text: '/alpha do it', origin: { kind: 'composer' } }))
    await $.skill.prompt({ skill: 'alpha', text: 'x' })
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: 'skills', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/alpha +1 +1 +0 /)
  })
})

describe('reading and switching', () => {
  test('vigil_read answers a plain string, the shape an MCP result must have', async ($, on) => {
    world(on, {})
    const ran = await $.tool.call({ tool: 'mcp__vigil__vigil_read', view: 'meters' })
    expect(typeof (ran as { result?: unknown }).result).toBe('string')
  })
  test('the switch file changes only through /rw-vigil; any other edit goes through', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files)
    const held = await $.tool.call({ tool: 'Write', file_path: SW, content: '{}' })
    expect(held.deny).toMatch(/only through \/rw-vigil/)
    const sh = await $.tool.call({ tool: 'Bash', command: `echo {} > ${SW}` })
    expect(sh.deny).toMatch(/only through \/rw-vigil/)
    const ok = await $.tool.call({ tool: 'Edit', file_path: '/r/a.ts', old_string: 'a', new_string: 'b' })
    expect(ok.deny).toBe(undefined)
    await $.command.run(cmd({ command: 'rw-vigil', args: 'records on', origin: { kind: 'composer' } }))
    expect(parseSwitches(files[SW]).features.D1).toBe(true)
    const refused = await $.command.run(cmd({ command: 'rw-vigil', args: 'off', origin: { kind: 'peer' } }))
    expect(JSON.stringify(refused)).toMatch(/Only you/)
    expect(parseSwitches(files[SW]).off).toBe(false)
  })
  test('under the kill switch nothing is counted', async ($, on) => {
    const files: Record<string, string> = { [SW]: serializeSwitches({ ...defaultSwitches(), off: true, features: { D1: true } }) }
    world(on, files)
    await session($)
    await $.command.run(cmd({ command: 'rw-vigil', args: '', origin: { kind: 'composer' } }))
    expect(files[`${DIR}/events.jsonl`] ?? '').toBe('')
  })
  test('/rw-vigil publish writes a snapshot with counts and no path', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    await session($)
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: 'publish', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/private Artifact/)
    const snap = files[`${DIR}/snapshot.json`]!
    expect(snap).toMatch(/revenantworks-vigil-snapshot/)
    expect(snap).not.toMatch(/\/r\/|\/u\/t|secret-plan/)
  })
})

describe('the suggestion queue in a session', () => {
  test('one note a session, as text where nothing draws; it never builds', async ($, on) => {
    const s = (n: number) => sessionKey(`old-${n}`)
    const seeded: DashEvent[] = Array.from({ length: 6 }, (_, i) => ({ t: NOW - DAY - i, s: s(i % 3), k: 'cmd', shape: 'npm run build' }))
    const files: Record<string, string> = { [SW]: RECORDS, [`${DIR}/events.jsonl`]: serializeEvents(seeded) }
    world(on, files, [])
    const turn: TurnCompleteInput = { answer: '', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' }
    const first = await $.turn.complete(turn)
    const second = await $.turn.complete({ ...turn, turnId: 't2' })
    expect(first.text).toMatch(/vigil suggests: Make "npm run build" a command or a skill/)
    expect(second.text).not.toMatch(/vigil suggests/)
    const list = await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    expect((list as { text: string }).text).toMatch(/1\. shell: npm\s+ran 6/)
    const drill = await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest 1', origin: { kind: 'composer' } }))
    expect((drill as { text: string }).text).toMatch(/1\.1 \[shown\] npm run build/)
    const acc = await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest accept 1', origin: { kind: 'composer' } }))
    expect(JSON.stringify(acc)).toMatch(/Copy this line to NEXT\.md yourself/)
    expect(Object.keys(files).some(k => /NEXT\.md|settings\.json/.test(k))).toBe(false)
  })
})

describe('drawing', () => {
  test('the pane draws the overview on the terminal and the desktop Code tab', async ($, on) => {
    world(on, {})
    await $.command.run(cmd({ command: 'rw-vigil', args: 'overview', origin: { kind: 'composer' } }))
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'vigil', surface, component: 'Pane', requestId: 'vigil', props: { title: 'vigil', isFocused: true, bodyColumns: 80, placement: 'dock', scroll: SCROLL, view: {} } })
      expect(await ui.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
      await ui.unmount()
    }
  })
  test('a bare /rw-vigil opens the board: a tile per area, pictures as SVG on the desktop, glyphs in the terminal', async ($, on) => {
    world(on, {})
    const r = await $.command.run(cmd({ command: 'rw-vigil', args: '', origin: { kind: 'composer' } }))
    expect(r.text).toMatch(/Usage: /)
    expect(r.text).toMatch(/Inbox: /)
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'vigil', surface, component: 'Pane', requestId: 'vigil', props: { title: 'vigil', isFocused: true, bodyColumns: 80, placement: 'dock', scroll: SCROLL, view: {} } })
      for (const t of ['Usage', 'Context', 'Inbox', 'Spend mode', 'Spend', 'Skills', 'Health']) expect(await ui.find({ type: 'Text', text: t })).toBeDefined()
      if (surface === 'desktop') expect(await ui.find({ type: 'Svg' })).toBeDefined()
      else expect(await ui.find({ type: 'Svg' })).toBeUndefined()
      await ui.unmount()
    }
  })
  test('inbox cards: Not now hides a card and Undo brings it back; spend auto writes only on your word', async ($, on) => {
    const files = noteFiles()
    world(on, files)
    on('ui.toast', async () => ({ value: undefined }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'inbox', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    const card = await ui.find({ type: 'Text', text: /npm run build/ })
    expect(card).toBeDefined()
    const id = (JSON.parse(files[`${DIR}/suggestions.json`] ?? '{"rows":[]}') as { rows: Array<{ id: string }> }).rows[0]?.id
    expect(id).toBeDefined()
    await ui.press({ key: `notnow:${id}` })
    expect(await ui.find({ type: 'Text', text: 'Nothing waits.' })).toBeDefined()
    await ui.press({ key: 'undo' })
    expect(await ui.find({ type: 'Text', text: /npm run build/ })).toBeDefined()
    await ui.unmount()
    const denied = await $.command.run(cmd({ command: 'rw-vigil', args: 'spend auto overnight off', origin: { kind: 'task-notification' } }))
    expect(denied.text).toMatch(/Only you/)
    expect(files[`${HOME}/.dispatch/spend-modes.json`]).toBeUndefined()
    const r = await $.command.run(cmd({ command: 'rw-vigil', args: 'spend auto overnight off', origin: { kind: 'composer' } }))
    expect(r.text).toMatch(/only when you say so/)
    expect(JSON.parse(files[`${HOME}/.dispatch/spend-modes.json`]!).auto.overnight).toBe(false)
  })
  test('tile controls: move, pin and collapse are saved; Open shows the detail and Back returns', async ($, on) => {
    world(on, {})
    await $.command.run(cmd({ command: 'rw-vigil', args: '', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: { title: 'vigil', isFocused: true, bodyColumns: 100, placement: 'dock', scroll: SCROLL, view: {} } })
    await ui.press({ key: 'down:usage' })
    await ui.press({ key: 'pin:health' })
    await ui.press({ key: 'collapse:spend' })
    const b = (await $.command.run(cmd({ command: 'rw-vigil', args: 'board', origin: { kind: 'composer' } }))).text
    const titles = b.split('\n').map(l => /^\s*([A-Z][a-z]+(?: mode)?)(?: \(pinned\))?: /.exec(l)?.[1]).filter(Boolean)
    expect(titles.slice(0, 3)).toEqual(['Health', 'Context', 'Usage'])
    expect(b).toMatch(/Health \(pinned\): /)
    expect(b).toMatch(/^\s*Spend: \S+$/m)
    await ui.press({ key: 'open:usage' })
    expect(await ui.find({ type: 'Text', text: /At this pace|No forecast yet/ })).toBeDefined()
    await ui.press({ key: 'back' })
    expect(await ui.find({ type: 'Text', text: 'Spend mode' })).toBeDefined()
    const t = await $.command.run(cmd({ command: 'rw-vigil', args: 'layout reset', origin: { kind: 'composer' } }))
    expect(t.text).toMatch(/Usage: /)
    expect(t.text).not.toMatch(/pinned/)
    await ui.unmount()
  })
  test('your own tiles: a spec in the tiles folder draws on the board; a bad one is refused with its reason; a scan is yours to start', async ($, on) => {
    const TD = `${DIR}/tiles`
    const files: Record<string, string> = {
      [`${TD}/release.json`]: JSON.stringify({ schema: 1, id: 'release', title: 'Release', source: { kind: 'date', path: './ROADMAP.md' }, picture: 'countdown' }),
      [`${TD}/keys.json`]: JSON.stringify({ schema: 1, id: 'keys', title: 'Keys', source: { kind: 'lines', path: '~/.ssh/known_hosts' }, picture: 'count' }),
      '/r/ROADMAP.md': 'Ship on 2026-11-02.',
    }
    const entry = (name: string): FsEntry => ({ name, kind: 'file', size: 200, mtimeMs: NOW, isLink: false }) as FsEntry
    const stat = (p: string): FsStat | undefined => (files[p] !== undefined ? ({ kind: 'file', size: files[p]!.length, mtimeMs: NOW, isLink: false, realPath: p } as FsStat) : p === HOME || p === '/r' ? ({ kind: 'dir', size: 0, mtimeMs: 0, isLink: false, realPath: p } as FsStat) : undefined)
    world(on, files, ['terminal'], { list: p => (p === TD ? [entry('keys.json'), entry('release.json')] : []), stat })
    const b = (await $.command.run(cmd({ command: 'rw-vigil', args: 'board', origin: { kind: 'composer' } }))).text
    expect(b).toMatch(/Release: \d+d, to go/)
    const t = (await $.command.run(cmd({ command: 'rw-vigil', args: 'tiles', origin: { kind: 'composer' } }))).text
    expect(t).toMatch(/release: Release, a countdown from \.\/ROADMAP\.md/)
    expect(t).toMatch(/keys\.json refused: source\.path reaches "\.ssh"/)
    const denied = await $.command.run(cmd({ command: 'rw-vigil', args: 'tiles build repo', origin: { kind: 'task-notification' } }))
    expect(denied.text).toMatch(/Only you/)
    const r = await $.command.run(cmd({ command: 'rw-vigil', args: 'tiles build repo', origin: { kind: 'composer' } }))
    expect(r.text).toMatch(/saves nothing until you say yes/)
  })
  test('the suggestion pane: click a group to drill in, back to every group, dismiss a group', async ($, on) => {
    const s = (n: number) => sessionKey(`old-${n}`)
    const seeded: DashEvent[] = [
      ...Array.from({ length: 6 }, (_, i) => ({ t: NOW - DAY - i, s: s(i % 3), k: 'cmd', shape: 'npm run build' }) as DashEvent),
      ...Array.from({ length: 4 }, (_, i) => ({ t: NOW - DAY - i, s: s(0), k: 'prompt', shape: 'bash cd ; git push' }) as DashEvent),
    ]
    const files: Record<string, string> = { [SW]: RECORDS, [`${DIR}/events.jsonl`]: serializeEvents(seeded) }
    world(on, files, [])
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: { title: 'vigil', isFocused: true, bodyColumns: 100, placement: 'dock', scroll: SCROLL, view: {} } })
    expect(await ui.find({ type: 'Text', text: /1\. shell: git/ })).toBeDefined()
    await ui.press({ key: 'drill:shell: git' })
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: /1\.1 \[new\] cd ; git push/ })).toBeDefined()
    await ui.press({ key: 'dismiss:shell: git' })
    expect(files[`${DIR}/suggestions.json`]).toMatch(/"state": "dismissed"/)
    await ui.press({ key: 'drill:*' })
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: /shell: npm/ })).toBeDefined()
    await ui.unmount()
  })
  test('the band asks once about records, and Turn on writes the switch', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files)
    // The engine beneath draws an empty band: a typed RenderElement, not a cast drawing.
    on('ui.render', async () => ({ type: 'Box', props: {} }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: SCROLL, view: {} } })
    await ui.press({ key: 'ask-on' })
    expect(parseSwitches(files[SW]).features.D1).toBe(true)
    await ui.unmount()
  })
  test('the band: Ask me later hides the ask', async ($, on) => {
    world(on, {})
    on('ui.render', async () => ({ type: 'Box', props: {} }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: SCROLL, view: {} } })
    expect(await ui.find({ type: 'Text', text: /keep counts across sessions/ })).toBeDefined()
    await ui.press({ key: 'ask-later' })
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: /keep counts across sessions/ })).toBeUndefined()
    await ui.unmount()
  })
  test('the pane view bar opens each view in place, and back to the overview', async ($, on) => {
    world(on, { [SW]: RECORDS })
    await $.command.run(cmd({ command: 'rw-vigil', args: 'overview', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: { title: 'vigil', isFocused: true, bodyColumns: 100, placement: 'dock', scroll: SCROLL, view: {} } })
    expect(await ui.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    await ui.press({ key: 'view:theme' })
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: /Themes/ })).toBeDefined()
    await ui.press({ key: 'view:suggest' })
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: /Suggestions/ })).toBeDefined()
    await ui.press({ key: 'view:overview' })
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    await ui.unmount()
  })
  test('a typed /rw-vigil <verb> switches a pane that is already open', async ($, on) => {
    world(on, { [SW]: RECORDS })
    await $.command.run(cmd({ command: 'rw-vigil', args: 'overview', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: { title: 'vigil', isFocused: true, bodyColumns: 100, placement: 'dock', scroll: SCROLL, view: {} } })
    expect(await ui.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: /Suggestions/ })).toBeDefined()
    await ui.unmount()
  })
})

// A press must redraw its own site: no test below calls ui.redraw() after a press, so a handler that
// only changes a module variable leaves the old drawing up and the test fails (the dead Later, AD).
const BAND_PROPS = { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: SCROLL, view: {} }
const PANE_PROPS = { title: 'vigil', isFocused: true, bodyColumns: 100, placement: 'dock' as const, scroll: SCROLL, view: {} }
const ASK = /keep counts across sessions/
const NOTE = /vigil suggests/
/** Six runs of one shell command across three past sessions: enough for one suggestion note. */
const noteFiles = (): Record<string, string> => ({
  [SW]: RECORDS,
  [`${DIR}/events.jsonl`]: serializeEvents(Array.from({ length: 6 }, (_, i) => ({ t: NOW - DAY - i, s: sessionKey(`old-${i % 3}`), k: 'cmd', shape: 'npm run build' }))),
})
const TURN: TurnCompleteInput = { answer: '', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' }

describe('the band redraws on every press (bug: Later and Ask me later looked dead)', () => {
  for (const [key, d1] of [['ask-on', true], ['ask-off', false], ['ask-later', undefined]] as const) {
    test(`${key} hides the records ask at once`, async ($, on) => {
      const files: Record<string, string> = {}
      world(on, files)
      on('ui.render', async () => ({ type: 'Box', props: {} }))
      await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
      const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
      expect(await ui.find({ type: 'Text', text: ASK })).toBeDefined()
      await ui.press({ key })
      expect(await ui.find({ type: 'Text', text: ASK })).toBeUndefined()
      expect(files[SW] === undefined ? undefined : parseSwitches(files[SW]).features.D1).toBe(d1)
      await ui.unmount()
    })
  }
  test('Later hides the suggestion note at once', async ($, on) => {
    world(on, noteFiles())
    on('ui.render', async () => ({ type: 'Box', props: {} }))
    await $.turn.complete(TURN)
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeDefined()
    await ui.press({ key: 'note-later' })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeUndefined()
    await ui.unmount()
  })
  test('Show hides the note and switches an open pane to Suggestions at once', async ($, on) => {
    world(on, noteFiles())
    on('ui.render', { component: 'AbovePrompt' }, async () => ({ type: 'Box', props: {} }))
    await $.turn.complete(TURN)
    await $.command.run(cmd({ command: 'rw-vigil', args: 'overview', origin: { kind: 'composer' } }))
    const pane = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    expect(await pane.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await ui.press({ key: 'note-show' })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeUndefined()
    expect(await pane.find({ type: 'Text', text: /Suggestions/ })).toBeDefined()
    await ui.unmount()
    await pane.unmount()
  })
})

describe('the pane redraws on every press, with no redraw of the test\'s own', () => {
  test('view bar, a group Open, Snooze and the back row each show at once', async ($, on) => {
    world(on, noteFiles())
    on('ui.toast', async () => ({ value: undefined }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'overview', origin: { kind: 'composer' } }))
    const pane = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    expect(await pane.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    await pane.press({ key: 'view:suggest' })
    expect(await pane.find({ type: 'Text', text: /1\. shell: npm/ })).toBeDefined()
    await pane.press({ key: 'drill:shell: npm' })
    expect(await pane.find({ type: 'Text', text: /npm run build/ })).toBeDefined()
    expect(await pane.find({ type: 'Text', text: /snoozed/ })).toBeUndefined()
    await pane.press({ key: 'snooze:shell: npm' })
    expect(await pane.find({ type: 'Text', text: /snoozed/ })).toBeDefined()
    await pane.press({ key: 'drill:*' })
    expect(await pane.find({ type: 'Text', text: /1\. shell: npm/ })).toBeDefined()
    await pane.press({ key: 'view:overview' })
    expect(await pane.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    await pane.unmount()
  })
})

describe('the band redraws when something else changes what it shows', () => {
  test('a dismiss pressed in the pane takes the same suggestion off the band at once', async ($, on) => {
    world(on, noteFiles())
    on('ui.render', { component: 'AbovePrompt' }, async () => ({ type: 'Box', props: {} }))
    await $.turn.complete(TURN)
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    const pane = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeDefined()
    await pane.press({ key: 'drill:shell: npm' })
    await pane.press({ key: 'dismiss:shell: npm' })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeUndefined()
    await ui.unmount()
    await pane.unmount()
  })
  test('a typed /rw-vigil suggest dismiss takes the note off an open band', async ($, on) => {
    world(on, noteFiles())
    on('ui.render', { component: 'AbovePrompt' }, async () => ({ type: 'Box', props: {} }))
    await $.turn.complete(TURN)
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeDefined()
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest dismiss 1', origin: { kind: 'composer' } }))
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeUndefined()
    await ui.unmount()
  })
  test('a typed /rw-vigil records off takes the ask off an open band', async ($, on) => {
    world(on, {})
    on('ui.render', { component: 'AbovePrompt' }, async () => ({ type: 'Box', props: {} }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    expect(await ui.find({ type: 'Text', text: ASK })).toBeDefined()
    await $.command.run(cmd({ command: 'rw-vigil', args: 'records off', origin: { kind: 'composer' } }))
    expect(await ui.find({ type: 'Text', text: ASK })).toBeUndefined()
    await ui.unmount()
  })
  test('a note picked at turn end shows on a band that is already up', async ($, on) => {
    world(on, noteFiles())
    on('ui.render', { component: 'AbovePrompt' }, async () => ({ type: 'Box', props: {} }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeUndefined()
    await $.turn.complete(TURN)
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeDefined()
    await ui.unmount()
  })
})

describe('health across sessions (bug: shroud NOT LOADED while it was loaded)', () => {
  test('a second session beating into the same file leaves this session loaded', async ($, on) => {
    const files: Record<string, string> = {}
    // This session's shroud beat, then another session's a minute later: one shared file.
    const mine = mergeHeartbeat(null, { plugin: 'shroud', version: '1.0.0', session: fnv1a('sess-1'), at: NOW - 60_000 })
    files[`${HOME}/.claude/revenantworks/health/shroud.json`] = mergeHeartbeat(mine, { plugin: 'shroud', version: '1.0.0', session: fnv1a('sess-2'), at: NOW - 1000 })
    world(on, files)
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: 'health', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/shroud\s+loaded 1\.0\.0/)
    expect(JSON.stringify(ran)).not.toMatch(/not loaded/)
  })
  test('a beat older than ten minutes is not loaded', () => {
    const text = mergeHeartbeat(null, { plugin: 'privacy', session: fnv1a('sess-1'), at: NOW - 11 * 60_000 })
    expect(heartbeatAlive(text, fnv1a('sess-1'), NOW).alive).toBe(false)
    expect(heartbeatAlive(text, fnv1a('sess-1'), NOW - 10 * 60_000).alive).toBe(true)
  })
})

describe('the current run (bug: an old run shown in Tasks)', () => {
  test('the ledger changed last wins, across the repo runs and the home junctions', async ($, on) => {
    const files: Record<string, string> = {}
    const LEDGER = '| unit | status |\n|---|---|\n| U1 | done |\n'
    const mtimes: Record<string, number> = {
      '/r/.dispatch/runs/2026-08-20-old/ledger.md': NOW - 50 * 86_400_000,
      '/r/.dispatch/runs/2026-10-01-mid/ledger.md': NOW - 5 * 86_400_000,
      [`${HOME}/.dispatch/runs/2026-10-08-current/ledger.md`]: NOW - 60_000,
    }
    for (const f of Object.keys(mtimes)) files[f] = LEDGER
    // A listing reports a folder's time as 0 and a junction as a link, as the host does.
    world(on, files, ['terminal'], {
      list: p => (p === '/r/.dispatch/runs'
        ? [{ name: '2026-08-20-old', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }, { name: '2026-10-01-mid', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }]
        : p === `${HOME}/.dispatch/runs` ? [{ name: '2026-10-08-current', kind: 'other', size: 0, mtimeMs: 0, isLink: true }] : []),
      stat: p => (mtimes[p] === undefined ? undefined : { kind: 'file', size: LEDGER.length, mtimeMs: mtimes[p], isLink: false }),
    })
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: 'tasks', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/run 2026-10-08-current/)
    expect(JSON.stringify(ran)).not.toMatch(/2026-08-20-old/)
  })
})

describe('Tasks: finished work shows as done (DM3 bug: 13 items "running" hours after they ended)', () => {
  const OUT = '/t/tasks/b1.output'
  const fx: TaskFx = {
    results: {
      'M14a build': { status: 'async_launched', agentId: 'aM14a' },
      'child run': { backgroundTaskId: 'b1', outputFile: OUT },
      'child watch': { taskId: 'mon1' },
      'main one': { backgroundTaskId: 'bm1' },
      'main two': { backgroundTaskId: 'bm2' },
    },
  }
  const note = (id: string, status: string) => `<task-notification>\n<task-id>${id}</task-id>\n<status>${status}</status>\n</task-notification>`
  test('a subagent turn end, a notification burst, and a child with no end signal', async ($, on) => {
    const files: Record<string, string> = { [OUT]: 'step 1\nstep 2 ok\n' }
    world(on, files, ['terminal'], { stat: p => (p === OUT ? { kind: 'file', size: 16, mtimeMs: NOW - 42 * 60_000, isLink: false } : undefined) }, {}, fx)
    await $.tool.call({ tool: 'Agent', description: 'M14a build', subagent_type: 'opus-medium', prompt: 'p', run_in_background: true })
    await $.tool.call(fromAgent('aM14a', { tool: 'Bash', description: 'child run', command: 'npm test', run_in_background: true }))
    await $.tool.call(fromAgent('aM14a', { tool: 'Monitor', description: 'child watch', timeout_ms: 60_000 }))
    await $.tool.call({ tool: 'Bash', description: 'main one', command: 'sleep 1', run_in_background: true })
    await $.tool.call({ tool: 'Bash', description: 'main two', command: 'sleep 2', run_in_background: true })
    // The subagent's loop ends: its one turn completes.
    await $.turn.complete({ answer: 'handed back', durationMs: 10, isAborted: false, turnId: 'ts', reason: 'answer', agentId: 'aM14a' })
    // Two notifications in one burst.
    await $.prompt.submit(submit({ text: `${note('bm1', 'completed')}\n${note('bm2', 'failed')}`, origin: { kind: 'task-notification' } }))
    const r = (await $.command.run(cmd({ command: 'rw-vigil', args: 'tasks', origin: { kind: 'composer' } }))) as { text: string }
    expect(r.text).toMatch(/0 running · 1 failed · 2 no end signal/)
    expect(r.text).toMatch(/completed agent +M14a build/)
    expect(r.text).toMatch(/completed bash +main one/)
    expect(r.text).toMatch(/failed +bash +main two/)
    expect(r.text).toMatch(/no-signal bash +child run[\s\S]*no end signal — last output 11:18 UTC/)
    expect(r.text).toMatch(/no-signal monitor +child watch[\s\S]*no end signal — no output seen/)
    expect(r.text).not.toMatch(/running for/)
  })
  test('the agent list: an agent the engine dropped has ended, idle still runs', async ($, on) => {
    world(on, {}, ['terminal'], {}, {}, { ...fx, agents: [{ id: 'aT', status: 'idle', description: 'teammate', type: 'teammate' }] })
    await $.tool.call({ tool: 'Agent', description: 'M14a build', subagent_type: 'opus-medium', prompt: 'p', run_in_background: true })
    // Same clock: inside the grace window the absent agent is not judged yet.
    const r = (await $.command.run(cmd({ command: 'rw-vigil', args: 'tasks', origin: { kind: 'composer' } }))) as { text: string }
    expect(r.text).toMatch(/2 running/)
    expect(r.text).toMatch(/running +agent +teammate/)
  })
})

describe('themes', () => {
  const THEMES = `${HOME}/.claude/revenantworks/themes`
  const themeWorld = (on: On, files: Record<string, string>, toasts: string[] = [], env: Record<string, string> = {}, ccTheme: string | null = null) => {
    world(on, files, ['terminal'], {
      list: p => (p !== THEMES ? [] : Object.keys(files).filter(f => f.startsWith(`${THEMES}/`)).map(f => ({ name: f.slice(THEMES.length + 1), kind: 'file', size: 1, mtimeMs: 1, isLink: false }))),
    }, env)
    on('ui.toast', async ($, e) => {
      toasts.push(e.text)
      return { value: undefined }
    })
    // The /config rows: the Claude Code theme is the row keyed "theme".
    on('config.list', async () => ({ value: ccTheme === null ? [] : [{ key: 'theme', label: 'Theme', kind: 'choice', value: ccTheme, provider: { plugin: 'engine', tier: 'core' }, isLocked: false }] }))
  }
  const run = async ($: Engine, args: string, kind: 'composer' | 'task-notification' = 'composer') => (await $.command.run(cmd({ command: 'rw-vigil', args, origin: { kind } }))) as { text: string; context?: string[] }

  test('show previews and never writes; it says which variant this console gets', async ($, on) => {
    const files: Record<string, string> = {}
    themeWorld(on, files, [], {}, 'light')
    const r = await run($, 'theme show revenantworks')
    expect(r.text).toMatch(/This console is light: it gets the light variant\./)
    expect(r.text).toMatch(/Preview only — nothing changed/)
    // Only the session heartbeat is written; no theme choice, no theme file.
    expect(Object.keys(files).filter(f => /theme/.test(f))).toEqual([])
    expect((await run($, 'theme show ghost')).text).toMatch(/No theme "ghost"/)
  })

  test('apply writes theme.json, picks the variant from the console, warns and gives the undo', async ($, on) => {
    const files: Record<string, string> = { [`${THEMES}/darkonly.json`]: JSON.stringify({ name: 'darkonly', background: 'dark', colors: { accent: '#00E5FF', dim: '#8D9FA2' } }) }
    themeWorld(on, files, [], {}, 'light-daltonized')
    const a = await run($, 'theme revenantworks')
    expect(a.text.split('\n')[0]).toBe('Applied: revenantworks (light variant — your console is light).')
    expect(a.text).toMatch(/Undo: \/rw-vigil theme neutral/)
    expect((await run($, 'help')).text.split('\n')[0]).toBe('▍ vigil commands')
    const b = await run($, 'theme darkonly')
    expect(JSON.parse(files[`${HOME}/.claude/revenantworks/theme.json`]!)).toEqual({ active: 'darkonly' })
    expect(b.text).toMatch(/accent\s+#00E5FF\s+1\.\d\d:1\s+under 4\.5:1/)
    expect(b.text).not.toMatch(/Verdict/)
  })

  test('VIGIL_THEME_BACKGROUND wins over the Claude Code theme', async ($, on) => {
    themeWorld(on, {}, [], { VIGIL_THEME_BACKGROUND: 'dark' }, 'light')
    expect((await run($, 'theme revenantworks')).text.split('\n')[0]).toBe('Applied: revenantworks (dark variant — your console is dark).')
  })

  test('discovery: bundled themes, the person\'s files, a file over a bundled name, a bad file listed', async ($, on) => {
    const files: Record<string, string> = {
      [`${THEMES}/mine.json`]: JSON.stringify({ name: 'mine', colors: { accent: '#3366FF' } }),
      [`${THEMES}/revenantworks.json`]: JSON.stringify({ name: 'revenantworks', description: 'my copy', header: 'plain' }),
      [`${THEMES}/broken.json`]: '{ not json',
    }
    themeWorld(on, files)
    const r = await run($, 'theme')
    expect(r.text).toMatch(/neutral\s+bundled, default/)
    expect(r.text).toMatch(/mine\s+yours/)
    expect(r.text).toMatch(/revenantworks\s+yours, over bundled\s+my copy/)
    expect(r.text).toMatch(/broken\.json: not valid JSON/)
  })

  test('switch: only the person, saved to theme.json, and the views take the new style', async ($, on) => {
    const files: Record<string, string> = {}
    themeWorld(on, files)
    expect((await run($, 'help')).text.split('\n')[0]).toMatch(/^── vigil commands ─+$/)
    expect((await run($, 'theme revenantworks', 'task-notification')).text).toMatch(/Only you/)
    const r = await run($, 'theme revenantworks')
    expect(JSON.parse(files[`${HOME}/.claude/revenantworks/theme.json`]!)).toEqual({ active: 'revenantworks' })
    expect(r.text).toMatch(/^Applied: revenantworks \(dark variant — your console looks dark\)\./)
    expect((await run($, 'help')).text.split('\n')[0]).toBe('▍ vigil commands')
  })

  test('an invalid active theme falls back to neutral with one notice', async ($, on) => {
    const toasts: string[] = []
    const files: Record<string, string> = {
      [`${HOME}/.claude/revenantworks/theme.json`]: JSON.stringify({ active: 'bad' }),
      [`${THEMES}/bad.json`]: JSON.stringify({ name: 'bad', colors: { accent: 'not-a-colour' } }),
    }
    themeWorld(on, files, toasts)
    expect((await run($, 'help')).text.split('\n')[0]).toMatch(/^── vigil commands/)
    await run($, 'skills')
    expect(toasts.filter(t => /theme "bad" not found or invalid; using neutral/.test(t)).length).toBe(1)
  })

  test('new from answers: saved, and a low-contrast colour is flagged', async ($, on) => {
    const files: Record<string, string> = {}
    themeWorld(on, files)
    expect((await run($, 'theme new')).text).toMatch(/Three ways/)
    const r = await run($, 'theme new acme accent=#3366FF ok=22A06B warn=#D97706 bad=#DC2626 dim=#333333 glyphs=ascii header=plain')
    const saved = JSON.parse(files[`${THEMES}/acme.json`]!)
    expect(saved).toMatchObject({ name: 'acme', glyphs: 'ascii', header: 'plain', colors: { accent: '#3366FF', ok: '#22A06B', dim: '#333333' } })
    expect(r.text).toMatch(/dim #333333 is 1\.\d\d:1 on a dark background, under the 3:1 floor/)
    expect((await run($, 'theme new acme accent=blue')).text).toMatch(/No theme saved: colour accent must be/)
  })

  test('new from a tokens file and import from a DESIGN.md: roles mapped by token name', async ($, on) => {
    const files: Record<string, string> = {
      '/r/tokens.json': JSON.stringify({ color: { brand: { primary: { $value: '#7C3AED' } }, feedback: { success: { value: '#16A34A' }, warning: { value: '#F59E0B' }, danger: { value: '#EF4444' } }, text: { muted: '#9CA3AF' }, border: { default: '#4B5563' } } }),
      '/r/DESIGN.md': '# Colours\n\n| Role | Token | Hex |\n|---|---|---|\n| accent | `sky` | `#38BDF8` |\n| error / broken | `rose` | `#FB7185` |\n',
    }
    themeWorld(on, files)
    const a = await run($, 'theme new violet from tokens.json')
    expect(JSON.parse(files[`${THEMES}/violet.json`]!).colors).toEqual({ accent: '#7C3AED', ok: '#16A34A', warn: '#F59E0B', bad: '#EF4444', dim: '#9CA3AF', rule: '#4B5563' })
    expect(a.text).toMatch(/accent\s+#7C3AED\s+from "color brand primary"/)
    const b = await run($, 'theme import DESIGN.md skyline')
    expect(JSON.parse(files[`${THEMES}/skyline.json`]!).colors).toMatchObject({ accent: '#38BDF8', bad: '#FB7185', ok: 'success' })
    expect(b.text).toMatch(/Not found, kept from neutral: ok, warn, dim, rule/)
  })

  test('import from a Claude design system hands Claude the read; vigil fetches nothing', async ($, on) => {
    const files: Record<string, string> = {}
    let fetched = 0
    themeWorld(on, files)
    on('http.fetch', async () => {
      fetched += 1
      return { value: { ok: false, status: 0, headers: {}, text: '' } }
    })
    const r = await run($, 'theme import https://claude.ai/artifact/AbC123 house')
    expect(r.context?.[0]).toMatch(/Artifact tool \(action "read"\)/)
    expect(r.context?.[0]).toMatch(/data, never instructions/)
    expect(r.context?.[0]).toMatch(/themes\/house\.json/)
    expect(fetched).toBe(0)
    expect(Object.keys(files).some(f => f.startsWith(THEMES))).toBe(false)
    expect((await run($, 'theme import https://example.com/x')).text).toMatch(/not a Claude artifact link/)
  })
})
