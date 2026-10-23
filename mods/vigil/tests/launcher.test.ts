import type { CommandInfo, CommandPresentation, CommandRunInput, On } from 'claude-code'
import { describe, expect, mock, test } from 'claude-code/testing'

import { bySkill, isLongName, parseRw, resolveTarget, rwListLines } from '../hooks/launcher-logic'
import { defaultSwitches, serializeSwitches } from '../hooks/lib/switches'
import { RW_SKILLS } from '../hooks/rw-skills'

const NOW = Date.UTC(2026, 9, 23, 12)
const HOME = '/u/t'
const SW = `${HOME}/.claude/revenantworks/switches.json`
const PRESENT: CommandPresentation = { isFullscreen: false, columns: 100 }
const cmd = (e: Omit<CommandRunInput, 'presentation'>): CommandRunInput => ({ ...e, presentation: PRESENT })
const AGENT = RW_SKILLS.find(s => s.short === 'agentwright')!
const LONG = `${AGENT.pack}:${AGENT.member}`

/** The engine beneath: a file map, the installed commands, and a log of every run the mod hands off. */
const world = (on: On, files: Record<string, string>, installed: CommandInfo[], ran: Array<{ command: string; args: string }>) => {
  mock.store(on)
  const clock = mock.clock(on, { now: NOW })
  on('env.get', async ($, e) => ({ value: e.name === 'HOME' ? HOME : undefined }))
  on('session.id', async () => ({ value: 'sess-1' }))
  on('session.cwd', async () => ({ value: '/r' }))
  on('session.repo', async () => ({ value: null }))
  on('session.surfaces', async () => ({ value: [] }))
  on('session.version', async () => ({ value: { version: '2.1.309' } }))
  on('fs.read', async ($, e) => {
    const text = files[e.path.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')]
    if (text !== undefined) return { value: text }
    throw new Error('ENOENT')
  })
  on('fs.write', async ($, e) => {
    files[e.path.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')] = e.text
    return { value: undefined }
  })
  on('fs.exists', async ($, e) => ({ value: files[e.path.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')] !== undefined }))
  on('fs.list', async () => ({ value: [] }))
  on('command.register', async ($, e) => ({ value: { command: e.name } }))
  on('tool.register', async () => ({ value: { tool: 'vigil_read' } }))
  on('command.list', async () => ({ value: installed }))
  on('command.run', async ($, e) => {
    ran.push({ command: e.command, args: e.args })
    return { text: '' }
  })
  return clock
}

const pack = (name: string): CommandInfo => ({ name, description: '', source: 'plugin' })

describe('the short-command logic', () => {
  test('every rostered skill has a short name, and none repeats', () => {
    const shorts = RW_SKILLS.map(s => s.short)
    expect(shorts.length).toBe(29)
    expect(new Set(shorts).size).toBe(shorts.length)
  })
  test('a skill is found by short name, /rw- form or member name', () => {
    expect(bySkill('agentwright')?.member).toBe(AGENT.member)
    expect(bySkill('/rw-agentwright')?.member).toBe(AGENT.member)
    expect(bySkill(AGENT.member)?.short).toBe('agentwright')
    expect(bySkill('nosuch')).toBe(undefined)
  })
  test('the hand-off prefers the pack, then the featured plugin, then a bare skill', () => {
    expect(resolveTarget(AGENT, [LONG, AGENT.member])).toBe(LONG)
    expect(resolveTarget(AGENT, [`agentwright:${AGENT.member}`, AGENT.member])).toBe(`agentwright:${AGENT.member}`)
    expect(resolveTarget(AGENT, [AGENT.member])).toBe(AGENT.member)
    expect(resolveTarget(AGENT, ['other:thing'])).toBe(null)
  })
  test('only a Revenantworks long name is hidden', () => {
    expect(isLongName(LONG)).toBe(true)
    expect(isLongName(AGENT.member)).toBe(true)
    expect(isLongName('rw-agentwright')).toBe(false)
    expect(isLongName('acme:revenantworks-foundation-notaskill')).toBe(false)
  })
  test('/rw splits the skill from what you want', () => {
    expect(parseRw('agentwright audit my routine')).toEqual({ skill: 'agentwright', rest: 'audit my routine' })
    expect(parseRw('  ')).toEqual({ skill: '', rest: '' })
  })
  test('the list names every short command', () => {
    const text = rwListLines().join('\n')
    for (const s of RW_SKILLS) expect(text).toContain(`/rw-${s.short}`)
  })
})

describe('the short commands', () => {
  test('/rw-<skill> hands off to the long command with the arguments, after the hook returns', async ($, on) => {
    const ran: Array<{ command: string; args: string }> = []
    const clock = world(on, {}, [pack(LONG)], ran)
    const out = await $.command.run(cmd({ command: 'rw-agentwright', args: 'audit my routine', origin: { kind: 'composer' } }))
    expect(out.text ?? '').toBe('')
    expect(ran.some(r => r.command === LONG)).toBe(false)
    await clock.advance(100)
    expect(ran).toContainEqual({ command: LONG, args: 'audit my routine' })
  })
  test('/rw <skill> does the same; bare /rw lists them', async ($, on) => {
    const ran: Array<{ command: string; args: string }> = []
    const clock = world(on, {}, [pack(LONG)], ran)
    const list = await $.command.run(cmd({ command: 'rw', args: '', origin: { kind: 'composer' } }))
    expect(list.text).toContain('/rw-pacewright')
    await $.command.run(cmd({ command: 'rw', args: 'agentwright emit', origin: { kind: 'composer' } }))
    await clock.advance(100)
    expect(ran).toContainEqual({ command: LONG, args: 'emit' })
  })
  test('a skill that is not installed says how to install it, and runs nothing', async ($, on) => {
    const ran: Array<{ command: string; args: string }> = []
    const clock = world(on, {}, [pack('other:thing')], ran)
    const out = await $.command.run(cmd({ command: 'rw-agentwright', args: '', origin: { kind: 'composer' } }))
    expect(out.text).toContain('/plugin install foundation@revenantworks')
    await clock.advance(100)
    expect(ran.filter(r => r.command !== 'rw-agentwright')).toEqual([])
  })
  test('the long name leaves the typeahead; another command does not', async ($, on) => {
    world(on, {}, [pack(LONG)], [])
    on('command.describe', async ($, e) => ({ description: e.description, isHidden: e.isHidden }))
    const provider = { plugin: 'foundation', tier: 'plugin' as const }
    const hidden = await $.command.describe({ command: LONG, description: 'x', isHidden: false, immediate: false, provider })
    expect(hidden.isHidden).toBe(true)
    const kept = await $.command.describe({ command: 'compact', description: 'y', isHidden: false, immediate: false, provider })
    expect(kept.isHidden).toBe(false)
  })
  test('switched off, the short commands answer so and the long names stay listed', async ($, on) => {
    const files = { [SW]: serializeSwitches({ ...defaultSwitches(), features: { D14: false } }) }
    const ran: Array<{ command: string; args: string }> = []
    world(on, files, [pack(LONG)], ran)
    on('command.describe', async ($, e) => ({ description: e.description, isHidden: e.isHidden }))
    const out = await $.command.run(cmd({ command: 'rw-agentwright', args: '', origin: { kind: 'composer' } }))
    expect(out.text).toContain('Short commands are off')
    const d = await $.command.describe({ command: LONG, description: 'x', isHidden: false, immediate: false, provider: { plugin: 'foundation', tier: 'plugin' } })
    expect(d.isHidden).toBe(false)
  })
})

describe('the rename (dash to vigil, 2026-10-23)', () => {
  test('/dash still answers, as /rw-vigil does, and is hidden from the typeahead', async ($, on) => {
    world(on, {}, [], [])
    on('command.describe', async ($, e) => ({ description: e.description, isHidden: e.isHidden }))
    const old = await $.command.run(cmd({ command: 'dash', args: 'help', origin: { kind: 'composer' } }))
    const now = await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
    expect(old.text).toBe(now.text)
    expect(now.text).toContain('/rw-vigil')
    const d = await $.command.describe({ command: 'dash', description: 'x', isHidden: false, immediate: false, provider: { plugin: 'vigil', tier: 'plugin' } })
    expect(d.isHidden).toBe(true)
  })
  test('records under dash/ carry on under vigil/; a vigil/ file of its own is never overwritten', async ($, on) => {
    const OLD = `${HOME}/.claude/revenantworks/dash`
    const NEW = `${HOME}/.claude/revenantworks/vigil`
    const files: Record<string, string> = { [`${OLD}/feed.json`]: '{"old":1}', [`${OLD}/suggestions.json`]: '{"old":2}', [`${NEW}/suggestions.json`]: '{"new":2}' }
    world(on, files, [], [])
    await $.command.run(cmd({ command: 'rw-vigil', args: 'help', origin: { kind: 'composer' } }))
    expect(files[`${NEW}/feed.json`]).toBe('{"old":1}')
    expect(files[`${NEW}/suggestions.json`]).toBe('{"new":2}')
    expect(files[`${OLD}/feed.json`]).toBe('{"old":1}')
  })
})
