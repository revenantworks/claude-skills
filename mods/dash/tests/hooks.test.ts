import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'
import { describe, expect, mock, test } from 'claude-code/testing'

import { DAY, sessionKey, serializeEvents, type DashEvent } from '../hooks/collector-logic'
import { defaultSwitches, parseSwitches, serializeSwitches } from '../hooks/lib/switches'

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
const world = (on: On, files: Record<string, string>, surfaces: string[] = ['terminal']) => {
  mock.store(on)
  mock.clock(on, { now: NOW })
  on('env.get', async ($, e) => ({ value: e.name === 'HOME' || e.name === 'USERPROFILE' ? HOME : undefined }) as never)
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
  on('fs.list', async () => ({ value: [] }) as never)
  on('fs.stat', async () => {
    throw new Error('ENOENT')
  })
  on('process.run', async () => ({ value: { exitCode: 1, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never)
  on('command.register', async ($, e) => ({ value: { command: e.name } }) as never)
  on('tool.register', async () => ({ value: { tool: 'dash_read' } }) as never)
  on('agent.list', async () => ({ value: [] }) as never)
  on('ui.open', async () => ({ value: { isPlaced: true } }) as never)
  on('prompt.submit', async ($, e) => ({ text: e.text }) as never)
  on('skill.prompt', async ($, e) => ({ text: e.text }) as never)
  on('turn.complete', async () => ({ text: '' }) as never)
  on('tool.call', async ($, e) => ({ result: { stdout: '', stderr: '', interrupted: false } as never }))
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
    expect(JSON.stringify(ran)).toMatch(/alpha: 1 fire\(s\) · 0 slash \/ 1 auto/)
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
    expect(JSON.stringify(ran)).toMatch(/alpha: 1 fire\(s\)[^"]*1 likely misroute/)
  })

  test('a typed /name is a slash fire', async ($, on) => {
    world(on, {})
    await $.prompt.submit({ text: '/alpha do it', origin: { kind: 'composer' } } as never)
    await $.skill.prompt({ skill: 'alpha', text: 'x' } as never)
    const ran = await $.command.run({ command: 'dash', args: 'skills', origin: { kind: 'composer' } } as never)
    expect(JSON.stringify(ran)).toMatch(/1 slash \/ 0 auto/)
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
      expect(await ui.find({ type: 'Text', text: /Skills \(30 days\)/ })).toBeDefined()
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
