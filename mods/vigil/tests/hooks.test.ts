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
type TaskFx = { store?: Record<string, unknown>; agents?: AgentInfo[]; results?: Record<string, unknown>; brokenStore?: boolean; registered?: string[] }

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
  else mock.store(on, fx.store)
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

const BAND_PROPS = { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: SCROLL, view: {} }
const PANE_PROPS = { title: 'vigil', isFocused: true, bodyColumns: 100, placement: 'dock' as const, scroll: SCROLL, view: {} }
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

  test('two skills loaded together are a batch, not a likely misroute', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    await $.skill.prompt({ skill: 'alpha', text: 'x' })
    await $.skill.prompt({ skill: 'beta', text: 'y' })
    const ran = await $.command.run(cmd({ command: 'rw-vigil', args: 'skills', origin: { kind: 'composer' } }))
    expect(JSON.stringify(ran)).toMatch(/alpha +1 +0 +1 +0 +0 /)
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
})

describe('the suggestion queue in a session', () => {
  const asked = (n: number, shape = 'bash docker compose'): DashEvent[] => Array.from({ length: n }, (_, i) => ({ t: NOW - DAY - i, s: sessionKey(`old-${i % 3}`), k: 'prompt', shape }))
  const RUN = (args: string, kind: 'composer' | 'sdk' | 'task-notification' = 'composer') => cmd({ command: 'rw-vigil', args, origin: { kind } })
  const rowsOf = (files: Record<string, string>) => (JSON.parse(files[`${DIR}/suggestions.json`]!) as { rows: Array<{ id: string; key: string; state: string; forever?: boolean }> }).rows

  test('one note a session, as text where nothing draws; accepting drafts in chat and writes no setting', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS, [`${DIR}/events.jsonl`]: serializeEvents(asked(4)) }
    world(on, files, [])
    const turn: TurnCompleteInput = { answer: '', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' }
    const first = await $.turn.complete(turn)
    const second = await $.turn.complete({ ...turn, turnId: 't2' })
    expect(first.text).toMatch(/vigil suggests: You keep being asked about "bash docker compose"/)
    expect(second.text).not.toMatch(/vigil suggests/)
    expect((await $.command.run(RUN('suggest'))).text).toMatch(/1\. You keep being asked/)
    expect((await $.command.run(RUN('suggest accept 1'))).text).toMatch(/Taken: You keep being asked/)
    expect(rowsOf(files)[0]!.state).toBe('accepted')
    expect(Object.keys(files).some(k => /NEXT\.md|settings\.json/.test(k))).toBe(false)
  })
  test('a row another session dismissed stays dismissed when this one rolls (bug: the queue filled up again)', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS, [`${DIR}/events.jsonl`]: serializeEvents(asked(4)) }
    world(on, files, [])
    await $.command.run(RUN('suggest'))
    expect(rowsOf(files)[0]!.state).toBe('new')
    // The other session writes the file; this one still holds its old copy in memory.
    files[`${DIR}/suggestions.json`] = files[`${DIR}/suggestions.json`]!.replace('"state": "new"', '"state": "dismissed"')
    await $.command.run(RUN('suggest'))
    expect(rowsOf(files)[0]!.state).toBe('dismissed')
    expect((await $.command.run(RUN('suggest'))).text).toMatch(/Nothing waits/)
  })
  test('the queue the owner has heals on the first roll: chain rows leave, the prompt stays', async ($, on) => {
    const old = (key: string) => ({ key, kind: 'command', title: key, evidence: '166 runs', action: 'a', id: key.slice(-6), state: 'new', createdAt: NOW, stateAt: NOW, lastSeen: NOW, count: 166 })
    const files: Record<string, string> = {
      [SW]: RECORDS,
      [`${DIR}/events.jsonl`]: serializeEvents(asked(4)),
      [`${DIR}/suggestions.json`]: JSON.stringify({ rows: Array.from({ length: 187 }, (_, i) => old(`command:cd ; git add ; tool${i}`)) }),
    }
    world(on, files, [])
    await $.command.run(RUN('suggest'))
    expect(rowsOf(files).map(r => r.key)).toEqual(['prompt:bash docker compose'])
  })
  test('Never in the pane keeps a card away for good', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS, [`${DIR}/events.jsonl`]: serializeEvents(asked(4)) }
    world(on, files)
    on('ui.toast', async () => ({ value: undefined }))
    await $.command.run(RUN('suggest'))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    await ui.press({ key: `never:${rowsOf(files)[0]!.id}` })
    expect(await ui.find({ type: 'Text', text: 'Nothing waits.' })).toBeDefined()
    expect(rowsOf(files)[0]).toMatchObject({ state: 'dismissed', forever: true })
    await ui.unmount()
  })
  test('the desktop app sends typed commands as the SDK host: its person counts, a routine does not', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files, [])
    expect((await $.command.run(RUN('on word-list', 'sdk'))).text).toMatch(/Only you/)
    expect(files[SW]).toBeUndefined()
    expect((await $.command.run(RUN('on word-list', 'task-notification'))).text).toMatch(/Only you/)
  })
  test('with a desktop surface the SDK turn is the person', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files, ['desktop'])
    expect((await $.command.run(RUN('on word-list', 'sdk'))).text).toMatch(/Done: word-list on/)
    expect(parseSwitches(files[SW]).features.W5).toBe(true)
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
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    const card = await ui.find({ type: 'Text', text: /docker compose/ })
    expect(card).toBeDefined()
    const id = (JSON.parse(files[`${DIR}/suggestions.json`] ?? '{"rows":[]}') as { rows: Array<{ id: string }> }).rows[0]?.id
    expect(id).toBeDefined()
    await ui.press({ key: `notnow:${id}` })
    expect(await ui.find({ type: 'Text', text: 'Nothing waits.' })).toBeDefined()
    await ui.press({ key: 'undo' })
    expect(await ui.find({ type: 'Text', text: /docker compose/ })).toBeDefined()
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
    await ui.press({ key: 'arrange' })
    await ui.press({ key: 'down:usage' })
    await ui.press({ key: 'pin:health' })
    await ui.press({ key: 'collapse:spend' })
    await ui.press({ key: 'arrange-done' })
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
  for (const surface of ['terminal', 'desktop'] as const) {
    test(`the band hides by its button and by command, and stays hidden across sessions (${surface})`, async ($, on) => {
      world(on, {})
      on('ui.render', async () => ({ type: 'Box', props: {} }))
      await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
      const props = { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: SCROLL, view: {} }
      const ui = await $.ui.mount({ plugin: 'vigil', surface, component: 'AbovePrompt', props })
      await ui.press({ key: 'band-hide' })
      expect(await ui.find({ type: 'Button', key: 'band-hide' })).toBeUndefined()
      const shown = await $.command.run(cmd({ command: 'rw-vigil', args: 'show', origin: { kind: 'composer' } }))
      expect(shown.text).toMatch(/is back/)
      await ui.redraw()
      expect(await ui.find({ type: 'Button', key: 'band-hide' })).toBeDefined()
      const hidden = await $.command.run(cmd({ command: 'rw-vigil', args: 'hide', origin: { kind: 'composer' } }))
      expect(hidden.text).toMatch(/\/rw-vigil show/)
      await ui.redraw()
      expect(await ui.find({ type: 'Button', key: 'band-hide' })).toBeUndefined()
      await ui.unmount()
    })
  }
  test('a band hidden in an earlier session stays hidden until /rw-vigil show', async ($, on) => {
    world(on, {}, ['terminal'], {}, {}, { store: { bandHidden: true } })
    on('ui.render', async () => ({ type: 'Box', props: {} }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
    const props = { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: SCROLL, view: {} }
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props })
    expect(await ui.find({ type: 'Button', key: 'band-hide' })).toBeUndefined()
    await $.command.run(cmd({ command: 'rw-vigil', args: 'show', origin: { kind: 'composer' } }))
    await ui.redraw()
    expect(await ui.find({ type: 'Button', key: 'band-hide' })).toBeDefined()
    await ui.unmount()
  })
  test('the board is a uniform grid: no layout controls until Arrange, and a Close on the bar', async ($, on) => {
    world(on, {})
    await $.command.run(cmd({ command: 'rw-vigil', args: '', origin: { kind: 'composer' } }))
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: { title: 'vigil', isFocused: true, bodyColumns: 100, placement: 'dock', scroll: SCROLL, view: {} } })
    expect(await ui.find({ type: 'Button', key: 'pin:usage' })).toBeUndefined()
    expect(await ui.find({ type: 'Button', key: 'close' })).toBeDefined()
    await ui.press({ key: 'arrange' })
    expect(await ui.find({ type: 'Button', key: 'pin:usage' })).toBeDefined()
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
    await ui.press({ key: 'view:cards' })
    await ui.redraw()
    expect(await ui.find({ type: 'Text', text: 'Inbox' })).toBeDefined()
    await ui.press({ key: 'view:skills' })
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
    expect(await ui.find({ type: 'Text', text: 'Inbox' })).toBeDefined()
    await ui.unmount()
  })
})

// A press must redraw its own site: no test below calls ui.redraw() after a press, so a handler that
// only changes a module variable leaves the old drawing up and the test fails (the dead Later, AD).
const ASK = /keep counts across sessions/
const NOTE = /vigil suggests/
/** One permission dialog shown four times this week: enough for one suggestion note. */
const noteFiles = (): Record<string, string> => ({
  [SW]: RECORDS,
  [`${DIR}/events.jsonl`]: serializeEvents(Array.from({ length: 4 }, (_, i) => ({ t: NOW - DAY - i, s: sessionKey(`old-${i % 3}`), k: 'prompt', shape: 'bash docker compose' }))),
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
    expect(await pane.find({ type: 'Text', text: 'Inbox' })).toBeDefined()
    await ui.unmount()
    await pane.unmount()
  })
})

describe('the pane redraws on every press, with no redraw of the test\'s own', () => {
  test('view bar and Not now each show at once', async ($, on) => {
    const files = noteFiles()
    world(on, files)
    on('ui.toast', async () => ({ value: undefined }))
    await $.command.run(cmd({ command: 'rw-vigil', args: 'overview', origin: { kind: 'composer' } }))
    const pane = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    expect(await pane.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    await pane.press({ key: 'view:cards' })
    expect(await pane.find({ type: 'Text', text: /docker compose/ })).toBeDefined()
    const id = (JSON.parse(files[`${DIR}/suggestions.json`]!) as { rows: Array<{ id: string }> }).rows[0]!.id
    await pane.press({ key: `notnow:${id}` })
    expect(await pane.find({ type: 'Text', text: 'Nothing waits.' })).toBeDefined()
    await pane.press({ key: 'view:skills' })
    expect(await pane.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
    await pane.unmount()
  })
})

describe('the band redraws when something else changes what it shows', () => {
  test('a dismiss pressed in the pane takes the same suggestion off the band at once', async ($, on) => {
    const files = noteFiles()
    world(on, files)
    on('ui.toast', async () => ({ value: undefined }))
    on('ui.render', { component: 'AbovePrompt' }, async () => ({ type: 'Box', props: {} }))
    await $.turn.complete(TURN)
    await $.command.run(cmd({ command: 'rw-vigil', args: 'suggest', origin: { kind: 'composer' } }))
    const pane = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    expect(await ui.find({ type: 'Text', text: NOTE })).toBeDefined()
    await pane.press({ key: `never:${(JSON.parse(files[`${DIR}/suggestions.json`]!) as { rows: Array<{ id: string }> }).rows[0]!.id}` })
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

  const THEME_FILE = `${HOME}/.claude/revenantworks/theme.json`

  test('apply writes theme.json, picks the variant from the console and gives the undo', async ($, on) => {
    const files: Record<string, string> = {}
    themeWorld(on, files, [], {}, 'light-daltonized')
    const a = await run($, 'theme revenantworks')
    expect(a.text.split('\n')[0]).toBe('Applied: revenantworks (light variant; this console is light).')
    expect(a.text).toMatch(/Undo: \/rw-vigil theme neutral/)
    expect(JSON.parse(files[THEME_FILE]!)).toEqual({ active: 'revenantworks' })
    expect((await run($, 'help')).text.split('\n')[0]).toBe('▍ vigil commands')
    expect((await run($, 'theme ghost')).text).toMatch(/No theme "ghost"/)
  })

  test('a typed theme redraws an open pane and the band at once (bug: the switch showed nothing)', async ($, on) => {
    themeWorld(on, {})
    await run($, 'skills')
    const pane = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    expect(await pane.find({ type: 'Text', text: /^── Skills, last 30 days/ })).toBeDefined()
    await run($, 'theme revenantworks')
    expect(await pane.find({ type: 'Text', text: /^▍ Skills, last 30 days/ })).toBeDefined()
    await pane.unmount()
  })

  test('the pane picks a theme with a press, no typing, and the press shows at once', async ($, on) => {
    const files: Record<string, string> = {}
    themeWorld(on, files)
    await run($, 'theme')
    const pane = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    expect(await pane.find({ type: 'Text', text: /^── Themes/ })).toBeDefined()
    await pane.press({ key: 'theme:revenantworks' })
    expect(await pane.find({ type: 'Text', text: /^▍ Themes/ })).toBeDefined()
    expect(JSON.parse(files[THEME_FILE]!)).toEqual({ active: 'revenantworks' })
    // Each theme draws in its own accent, so the list is the preview.
    const line = await pane.find({ type: 'Text', text: /hc-light/ })
    expect(line?.props.color).toBe('#044C56')
    await pane.unmount()
  })

  test('the console background: a press or a word saves it beside the theme, and the variant follows', async ($, on) => {
    const files: Record<string, string> = {}
    themeWorld(on, files, [], {}, 'auto')
    await run($, 'theme revenantworks')
    expect((await run($, 'theme')).text).toMatch(/This console looks dark/)
    await run($, 'theme background light')
    expect(JSON.parse(files[THEME_FILE]!)).toEqual({ active: 'revenantworks', background: 'light' })
    expect((await run($, 'theme')).text).toMatch(/This console is light/)
    await run($, 'theme neutral')
    expect(JSON.parse(files[THEME_FILE]!)).toEqual({ active: 'neutral', background: 'light' })
    await run($, 'theme background auto')
    expect(JSON.parse(files[THEME_FILE]!)).toEqual({ active: 'neutral' })
    expect((await run($, 'theme background blue')).text).toMatch(/Usage/)
  })

  test('VIGIL_THEME_BACKGROUND wins over the Claude Code theme', async ($, on) => {
    themeWorld(on, {}, [], { VIGIL_THEME_BACKGROUND: 'dark' }, 'light')
    expect((await run($, 'theme revenantworks')).text.split('\n')[0]).toBe('Applied: revenantworks (dark variant; this console is dark).')
  })

  test('discovery: bundled themes, the person\'s files, a file over a bundled name, a bad file listed', async ($, on) => {
    const files: Record<string, string> = {
      [`${THEMES}/mine.json`]: JSON.stringify({ name: 'mine', colors: { accent: '#3366FF' } }),
      [`${THEMES}/revenantworks.json`]: JSON.stringify({ name: 'revenantworks', description: 'my copy', header: 'plain' }),
      [`${THEMES}/broken.json`]: '{ not json',
    }
    themeWorld(on, files)
    const r = await run($, 'theme')
    expect(r.text).toMatch(/neutral\s+Your own Claude Code theme colours/)
    expect(r.text).toMatch(/mine\s+yours/)
    expect(r.text).toMatch(/revenantworks\s+my copy · yours/)
    expect(r.text).toMatch(/broken\.json: not valid JSON/)
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
})

describe('retired 2026-11-02', () => {
  test('the panels and the old names are gone, and say how to see every command', async ($, on) => {
    world(on, {})
    for (const verb of ['gpu', 'godot', 'palette', 'prs', 'publish', 'network on']) {
      expect((await $.command.run(cmd({ command: 'rw-vigil', args: verb, origin: { kind: 'composer' } }))).text).toMatch(/Unknown: \/rw-vigil/)
    }
  })
})

describe('/rw-vigil link', () => {
  const LINK = `${HOME}/.claude/revenantworks/link.json`
  const OWN = '/p/own'
  const tile = JSON.stringify({ schema: 1, id: 'step', title: 'Step', picture: 'count', source: { kind: 'lines', path: '@/north/q.yml' }, act: { label: 'Close it', prompt: 'Offer done or skip.' } })
  const theme = JSON.stringify({ name: 'house', colors: { accent: '#3366FF' } })
  const linked = (on: On, files: Record<string, string>) => {
    const entry = (name: string): FsEntry => ({ name, kind: 'file', size: 10, mtimeMs: 1, isLink: false })
    world(on, files, ['terminal'], {
      list: p => (p === `${OWN}/tiles` ? [entry('step.json')] : p === `${OWN}/themes` ? [entry('house.json')] : []),
      stat: p => (p === '/c/north/q.yml' ? { kind: 'file', size: 4, mtimeMs: 1, realPath: p, isLink: false } as FsStat : p === HOME || p === '/r' || p === '/c' ? { kind: 'dir', size: 0, mtimeMs: 1, realPath: p, isLink: false } as FsStat : undefined),
    })
    on('ui.toast', async () => ({ value: undefined }))
  }
  const FILES = (): Record<string, string> => ({ [`${OWN}/tiles/step.json`]: tile, [`${OWN}/themes/house.json`]: theme, '/c/north/q.yml': 'a\nb\n' })
  const run = ($: Engine, args: string, kind: 'composer' | 'task-notification' = 'composer') => $.command.run(cmd({ command: 'rw-vigil', args, origin: { kind } }))

  test('only you can set it; linked, your tiles and themes load and @/ reads the clones', async ($, on) => {
    const files = FILES()
    linked(on, files)
    expect((await run($, 'link /c /p/own', 'task-notification')).text).toMatch(/Only you/)
    expect(files[LINK]).toBeUndefined()
    expect((await run($, 'link')).text).toMatch(/Not linked/)
    expect((await run($, 'link /c /p/own')).text).toMatch(/step: Step/)
    expect(JSON.parse(files[LINK]!)).toEqual({ root: '/c', folder: '/p/own' })
    expect((await run($, 'theme')).text).toMatch(/house\s+yours/)
    expect((await run($, '')).text).toMatch(/Step: 2/)
    expect((await run($, 'link off')).text).not.toMatch(/step: Step/)
    expect((await run($, 'theme')).text).not.toMatch(/house/)
  })
  test('the tile button drafts its prompt in chat and writes nothing', async ($, on) => {
    const files = FILES()
    linked(on, files)
    await run($, 'link /c /p/own')
    await run($, 'tile my:step')
    const before = Object.keys(files).length
    const ui = await $.ui.mount({ plugin: 'vigil', surface: 'terminal', component: 'Pane', requestId: 'vigil', props: PANE_PROPS })
    await ui.press({ key: 'tile-act' })
    expect(Object.keys(files).length).toBe(before)
    await ui.unmount()
  })
})
