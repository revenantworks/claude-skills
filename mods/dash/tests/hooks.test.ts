import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'
import { describe, expect, mock, test } from 'claude-code/testing'

import { DAY, sessionKey, serializeEvents, type DashEvent } from '../hooks/collector-logic'
import { defaultSwitches, parseSwitches, serializeSwitches } from '../hooks/lib/switches'
import { fnv1a, heartbeatAlive, mergeHeartbeat } from '../hooks/lib/util'

const NOW = Date.UTC(2026, 9, 8, 12)
const HOME = '/u/t'
const SW = `${HOME}/.claude/revenantworks/switches.json`
const DIR = `${HOME}/.claude/revenantworks/dash`
const RECORDS = serializeSwitches({ ...defaultSwitches(), features: { D1: true } })

// Text that must never reach a file: a prompt, a command's arguments, a skill's body, a path.
const PROMPT = 'please refactor the billing module for the Falcon client'
const CMD_ARG = 'customer-ledger-2026.csv'
const SKILL_BODY = 'SKILL BODY: confidential procedure text'
const PATH = '/r/src/billing/secret-plan.ts'

// On Windows the test host hands a stub the resolved path (drive letter, backslashes); key files by the posix form.
const key = (p: string) => p.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')
type FsX = { list?: (path: string) => unknown[]; stat?: (path: string) => unknown }
/** Fixture tasks: the agent list the engine returns, and a tool result per call description. */
type TaskFx = { agents?: unknown[]; results?: Record<string, unknown> }
const world = (on: On, files: Record<string, string>, surfaces: string[] = ['terminal'], fsx: FsX = {}, env: Record<string, string> = {}, fx: TaskFx = {}) => {
  mock.store(on)
  mock.clock(on, { now: NOW })
  on('env.get', async ($, e) => ({ value: e.name === 'HOME' || e.name === 'USERPROFILE' ? HOME : env[e.name] }) as never)
  on('session.id', async () => ({ value: 'sess-1' }) as never)
  on('session.cwd', async () => ({ value: '/r' }) as never)
  on('session.repo', async () => ({ value: { root: '/r', remote: null } }) as never)
  on('session.surfaces', async () => ({ value: surfaces }) as never)
  on('session.version', async () => ({ value: { version: '2.1.295' } }) as never)
  on('session.usage', async () => ({ value: { context: { window: 200000, breakdown: { skills: { totalSkills: 2, includedSkills: 2, tokens: 10, skillFrontmatter: [{ name: 'alpha' }, { name: 'beta' }] } } } } }) as never)
  on('fs.read', async ($, e) => {
    if (files[key(e.path)] !== undefined) return { value: files[key(e.path)] } as never
    throw new Error('ENOENT')
  })
  on('fs.write', async ($, e) => {
    files[key(e.path)] = e.text
    return { value: undefined } as never
  })
  on('fs.exists', async ($, e) => ({ value: files[key(e.path)] !== undefined }) as never)
  on('fs.list', async ($, e) => ({ value: fsx.list?.(key(e.path)) ?? [] }) as never)
  on('fs.stat', async ($, e) => {
    const st = fsx.stat?.(key(e.path))
    if (st === undefined) throw new Error('ENOENT')
    return { value: st } as never
  })
  on('process.run', async () => ({ value: { exitCode: 1, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never)
  on('command.register', async ($, e) => ({ value: { command: e.name } }) as never)
  on('tool.register', async () => ({ value: { tool: 'dash_read' } }) as never)
  on('agent.list', async () => ({ value: fx.agents ?? [] }) as never)
  on('ui.open', async () => ({ value: { isPlaced: true } }) as never)
  on('prompt.submit', async ($, e) => ({ text: e.text }) as never)
  on('skill.prompt', async ($, e) => ({ text: e.text }) as never)
  on('turn.complete', async () => ({ text: '' }) as never)
  on('tool.call', async ($, e) => ({ result: (fx.results?.[String((e as { description?: unknown }).description)] ?? { stdout: '', stderr: '', interrupted: false }) as never }))
}

/** A short session: a typed prompt, an automatic skill, a command with arguments, an edit, a turn. */
const session = async ($: Engine) => {
  await $.prompt.submit({ text: PROMPT, origin: { kind: 'composer' } } as never)
  await $.skill.prompt({ skill: 'alpha', text: SKILL_BODY } as never)
  await $.tool.call({ tool: 'Bash', command: `python3 tools/import.py --input ${CMD_ARG} -v` } as never)
  await $.tool.call({ tool: 'Edit', file_path: PATH, old_string: 'a', new_string: 'b' } as never)
  await $.turn.complete({ answer: 'done', durationMs: 10, isAborted: false, turnId: 't1', reason: 'answer', usage: { input_tokens: 100, output_tokens: 50, cache_read_input_tokens: 900, cache_creation_input_tokens: 0, model: 'm' } } as never)
}

const dashFiles = (files: Record<string, string>) => Object.entries(files).filter(([k]) => k.startsWith(DIR))

describe('the collector', () => {
  test('before the records yes, nothing is written; the session still shows', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files)
    await session($)
    const ran = await $.command.run({ command: 'dash', args: 'skills', origin: { kind: 'composer' } } as never)
    expect(JSON.stringify(ran)).toMatch(/alpha +1 +0 +1 +0 +0 /)
    expect(dashFiles(files)).toEqual([])
  })

  test('with the yes it writes events.jsonl and feed.json, and no prompt, command, skill text or path', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    await session($)
    await $.command.run({ command: 'dash', args: '', origin: { kind: 'composer' } } as never)
    const written = dashFiles(files)
    expect(written.map(([k]) => k.slice(DIR.length + 1)).sort()).toEqual(['events.jsonl', 'feed.json', 'suggestions.json'])
    const all = written.map(([, v]) => v).join('\n')
    for (const secret of [PROMPT, 'Falcon', CMD_ARG, SKILL_BODY, 'confidential', PATH, 'secret-plan', 'billing']) expect(all).not.toContain(secret)
    expect(all).toContain('"shape":"python3 *.py --input -v"')
    const feed = JSON.parse(files[`${DIR}/feed.json`]!) as { skills: Array<{ name: string; listed: boolean; tokens7: number }> }
    expect(feed.skills.find(s => s.name === 'alpha')).toMatchObject({ listed: true, tokens7: 1050 })
    expect(feed.skills.find(s => s.name === 'beta')?.listed).toBe(true)
  })

  test('a different skill soon after an automatic one is a likely misroute', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    await $.skill.prompt({ skill: 'alpha', text: 'x' } as never)
    await $.skill.prompt({ skill: 'beta', text: 'y' } as never)
    const ran = await $.command.run({ command: 'dash', args: 'skills', origin: { kind: 'composer' } } as never)
    expect(JSON.stringify(ran)).toMatch(/alpha +1 +0 +1 +0 +1 /)
  })

  test('a typed /name is a slash fire', async ($, on) => {
    world(on, {})
    await $.prompt.submit({ text: '/alpha do it', origin: { kind: 'composer' } } as never)
    await $.skill.prompt({ skill: 'alpha', text: 'x' } as never)
    const ran = await $.command.run({ command: 'dash', args: 'skills', origin: { kind: 'composer' } } as never)
    expect(JSON.stringify(ran)).toMatch(/alpha +1 +1 +0 /)
  })
})

describe('reading and switching', () => {
  test('dash_read answers a plain string, the shape an MCP result must have', async ($, on) => {
    world(on, {})
    const ran = await $.tool.call({ tool: 'mcp__dash__dash_read', view: 'meters' } as never)
    expect(typeof (ran as { result?: unknown }).result).toBe('string')
  })
  test('the switch file changes only through /dash; any other edit goes through', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files)
    const held = await $.tool.call({ tool: 'Write', file_path: SW, content: '{}' } as never)
    expect(held.deny).toMatch(/only through \/dash/)
    const sh = await $.tool.call({ tool: 'Bash', command: `echo {} > ${SW}` } as never)
    expect(sh.deny).toMatch(/only through \/dash/)
    const ok = await $.tool.call({ tool: 'Edit', file_path: '/r/a.ts', old_string: 'a', new_string: 'b' } as never)
    expect(ok.deny).toBe(undefined)
    await $.command.run({ command: 'dash', args: 'records on', origin: { kind: 'composer' } } as never)
    expect(parseSwitches(files[SW]).features.D1).toBe(true)
    const refused = await $.command.run({ command: 'dash', args: 'off', origin: { kind: 'peer' } } as never)
    expect(JSON.stringify(refused)).toMatch(/Only you/)
    expect(parseSwitches(files[SW]).off).toBe(false)
  })
  test('under the kill switch nothing is counted', async ($, on) => {
    const files: Record<string, string> = { [SW]: serializeSwitches({ ...defaultSwitches(), off: true, features: { D1: true } }) }
    world(on, files)
    await session($)
    await $.command.run({ command: 'dash', args: '', origin: { kind: 'composer' } } as never)
    expect(files[`${DIR}/events.jsonl`] ?? '').toBe('')
  })
  test('/dash publish writes a snapshot with counts and no path', async ($, on) => {
    const files: Record<string, string> = { [SW]: RECORDS }
    world(on, files)
    await session($)
    const ran = await $.command.run({ command: 'dash', args: 'publish', origin: { kind: 'composer' } } as never)
    expect(JSON.stringify(ran)).toMatch(/private Artifact/)
    const snap = files[`${DIR}/snapshot.json`]!
    expect(snap).toMatch(/revenantworks-dash-snapshot/)
    expect(snap).not.toMatch(/\/r\/|\/u\/t|secret-plan/)
  })
})

describe('the suggestion queue in a session', () => {
  test('one note a session, as text where nothing draws; it never builds', async ($, on) => {
    const s = (n: number) => sessionKey(`old-${n}`)
    const seeded: DashEvent[] = Array.from({ length: 6 }, (_, i) => ({ t: NOW - DAY - i, s: s(i % 3), k: 'cmd', shape: 'npm run build' }))
    const files: Record<string, string> = { [SW]: RECORDS, [`${DIR}/events.jsonl`]: serializeEvents(seeded) }
    world(on, files, [])
    const turn = { answer: '', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' }
    const first = await $.turn.complete(turn as never)
    const second = await $.turn.complete({ ...turn, turnId: 't2' } as never)
    expect(first.text).toMatch(/dash suggests: Make "npm run build" a command or a skill/)
    expect(second.text).not.toMatch(/dash suggests/)
    const list = await $.command.run({ command: 'dash', args: 'suggest', origin: { kind: 'composer' } } as never)
    expect((list as { text: string }).text).toMatch(/\[shown\] Make "npm run build"/)
    const acc = await $.command.run({ command: 'dash', args: 'suggest accept 1', origin: { kind: 'composer' } } as never)
    expect(JSON.stringify(acc)).toMatch(/Copy this line to NEXT\.md yourself/)
    expect(Object.keys(files).some(k => /NEXT\.md|settings\.json/.test(k))).toBe(false)
  })
})

describe('drawing', () => {
  test('the pane draws the overview on the terminal and the desktop Code tab', async ($, on) => {
    world(on, {})
    await $.command.run({ command: 'dash', args: '', origin: { kind: 'composer' } } as never)
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'dash', surface, component: 'Pane', requestId: 'dash', props: { title: 'dash', isFocused: true, bodyColumns: 80, placement: 'dock' } as never })
      expect(await ui.find({ type: 'Text', text: /Skills, last 30 days/ })).toBeDefined()
      await ui.unmount()
    }
  })
  test('the band asks once about records, and Turn on writes the switch', async ($, on) => {
    const files: Record<string, string> = {}
    world(on, files)
    on('ui.render', async ($, e) => {
      const { Box } = $.ui.resolve(e)
      return h(Box, {}) as never
    })
    await $.command.run({ command: 'dash', args: 'help', origin: { kind: 'composer' } } as never)
    const ui = await $.ui.mount({ plugin: 'dash', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100 } as never })
    await ui.press({ key: 'ask-on' })
    expect(parseSwitches(files[SW]).features.D1).toBe(true)
    await ui.unmount()
  })
})

describe('health across sessions (bug: privacy NOT LOADED while it was loaded)', () => {
  test('a second session beating into the same file leaves this session loaded', async ($, on) => {
    const files: Record<string, string> = {}
    // This session's privacy beat, then another session's a minute later: one shared file.
    const mine = mergeHeartbeat(null, { plugin: 'privacy', version: '1.0.0', session: fnv1a('sess-1'), at: NOW - 60_000 })
    files[`${HOME}/.claude/revenantworks/health/privacy.json`] = mergeHeartbeat(mine, { plugin: 'privacy', version: '1.0.0', session: fnv1a('sess-2'), at: NOW - 1000 })
    world(on, files)
    const ran = await $.command.run({ command: 'dash', args: 'health', origin: { kind: 'composer' } } as never)
    expect(JSON.stringify(ran)).toMatch(/privacy\s+loaded 1\.0\.0/)
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
    const ran = await $.command.run({ command: 'dash', args: 'tasks', origin: { kind: 'composer' } } as never)
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
    await $.tool.call({ tool: 'Agent', description: 'M14a build', subagent_type: 'opus-medium', prompt: 'p', run_in_background: true } as never)
    await $.tool.call({ tool: 'Bash', description: 'child run', command: 'npm test', run_in_background: true, agentId: 'aM14a' } as never)
    await $.tool.call({ tool: 'Monitor', description: 'child watch', agentId: 'aM14a' } as never)
    await $.tool.call({ tool: 'Bash', description: 'main one', command: 'sleep 1', run_in_background: true } as never)
    await $.tool.call({ tool: 'Bash', description: 'main two', command: 'sleep 2', run_in_background: true } as never)
    // The subagent's loop ends: its one turn completes.
    await $.turn.complete({ answer: 'handed back', durationMs: 10, isAborted: false, turnId: 'ts', reason: 'answer', agentId: 'aM14a' } as never)
    // Two notifications in one burst.
    await $.prompt.submit({ text: `${note('bm1', 'completed')}\n${note('bm2', 'failed')}`, origin: { kind: 'task-notification' } } as never)
    const r = (await $.command.run({ command: 'dash', args: 'tasks', origin: { kind: 'composer' } } as never)) as { text: string }
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
    await $.tool.call({ tool: 'Agent', description: 'M14a build', subagent_type: 'opus-medium', prompt: 'p', run_in_background: true } as never)
    // Same clock: inside the grace window the absent agent is not judged yet.
    const r = (await $.command.run({ command: 'dash', args: 'tasks', origin: { kind: 'composer' } } as never)) as { text: string }
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
      return { value: undefined } as never
    })
    // The /config rows: the Claude Code theme is the row keyed "theme".
    on('config.list', async () => ({ value: ccTheme === null ? [] : [{ key: 'theme', label: 'Theme', kind: 'choice', value: ccTheme, provider: { kind: 'engine' }, isLocked: false }] }) as never)
  }
  const run = async ($: Engine, args: string, kind = 'composer') => (await $.command.run({ command: 'dash', args, origin: { kind } } as never)) as { text: string; context?: string[] }

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
    expect(a.text).toMatch(/Undo: \/dash theme neutral/)
    expect((await run($, 'help')).text.split('\n')[0]).toBe('▍ dash commands')
    const b = await run($, 'theme darkonly')
    expect(JSON.parse(files[`${HOME}/.claude/revenantworks/theme.json`]!)).toEqual({ active: 'darkonly' })
    expect(b.text).toMatch(/accent\s+#00E5FF\s+1\.\d\d:1\s+under 4\.5:1/)
    expect(b.text).not.toMatch(/Verdict/)
  })

  test('DASH_THEME_BACKGROUND wins over the Claude Code theme', async ($, on) => {
    themeWorld(on, {}, [], { DASH_THEME_BACKGROUND: 'dark' }, 'light')
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
    expect((await run($, 'help')).text.split('\n')[0]).toMatch(/^── dash commands ─+$/)
    expect((await run($, 'theme revenantworks', 'task-notification')).text).toMatch(/Only you/)
    const r = await run($, 'theme revenantworks')
    expect(JSON.parse(files[`${HOME}/.claude/revenantworks/theme.json`]!)).toEqual({ active: 'revenantworks' })
    expect(r.text).toMatch(/^Applied: revenantworks \(dark variant — your console looks dark\)\./)
    expect((await run($, 'help')).text.split('\n')[0]).toBe('▍ dash commands')
  })

  test('an invalid active theme falls back to neutral with one notice', async ($, on) => {
    const toasts: string[] = []
    const files: Record<string, string> = {
      [`${HOME}/.claude/revenantworks/theme.json`]: JSON.stringify({ active: 'bad' }),
      [`${THEMES}/bad.json`]: JSON.stringify({ name: 'bad', colors: { accent: 'not-a-colour' } }),
    }
    themeWorld(on, files, toasts)
    expect((await run($, 'help')).text.split('\n')[0]).toMatch(/^── dash commands/)
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

  test('import from a Claude design system hands Claude the read; dash fetches nothing', async ($, on) => {
    const files: Record<string, string> = {}
    let fetched = 0
    themeWorld(on, files)
    on('http.fetch', async () => {
      fetched += 1
      return { value: { ok: false, status: 0, text: '' } } as never
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
