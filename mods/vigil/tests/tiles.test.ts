import { describe, expect, test } from 'claude-code/testing'

import { arranged, detailOf, parseLayout, tileOf, type BoardData } from '../hooks/board-logic'
import { DAY, emptyHealth } from '../hooks/collector-logic'
import { parseAutoModes } from '../hooks/board-logic'
import { buildPrompt, levelOf, parseSpec, pathProblem, realProblem, resolvePath, tileKey, userTileOf, valueOf, type TileSpec } from '../hooks/tiles-logic'

const NOW = Date.UTC(2026, 9, 23, 12)
const spec = (over: Record<string, unknown> = {}): string => JSON.stringify({ schema: 1, id: 'ci', title: 'CI runs', source: { kind: 'json', path: './state/ci.json', field: 'runs' }, picture: 'dots', ...over })
const ok = (text: string, id?: string): TileSpec => {
  const r = parseSpec(text, id)
  if (!('spec' in r)) throw new Error(r.errors.join('; '))
  return r.spec
}
const errs = (text: string, id?: string): string[] => {
  const r = parseSpec(text, id)
  return 'errors' in r ? r.errors : []
}

describe('a tile spec is data, checked before it loads', () => {
  test('a good spec loads; its id must match the file name', () => {
    expect(ok(spec(), 'ci').picture).toBe('dots')
    expect(errs(spec(), 'other').join()).toMatch(/does not match the file name/)
  })
  test('unknown keys are refused, so a script field never passes silently', () => {
    expect(errs(spec({ run: 'rm -rf ~' })).join()).toMatch(/unknown key "run"/)
    expect(errs(spec({ source: { kind: 'json', path: './a.json', field: 'x', cmd: 'ls' } })).join()).toMatch(/source.cmd does not apply/)
  })
  test('a source feeds only the pictures it can', () => {
    expect(errs(spec({ source: { kind: 'date', path: './ROADMAP.md' }, picture: 'ring' })).join()).toMatch(/cannot draw a ring/)
    expect(ok(spec({ source: { kind: 'date', path: './ROADMAP.md' }, picture: 'countdown' })).source.kind).toBe('date')
  })
  test('paths: home or repo only, no climbing, never a key, token, secret or .git', () => {
    expect(pathProblem('./docs/a.md')).toBeNull()
    expect(pathProblem('~/notes/todo.md')).toBeNull()
    expect(pathProblem('/etc/passwd')).toMatch(/must start with/)
    expect(pathProblem('./../x')).toMatch(/climb/)
    for (const bad of ['~/.ssh/id_ed25519', './.env', './.git/info/kestrel-pattern', '~/.config/gh/token.json', '~/keys/server.pem', '~/.aws/credentials']) expect(pathProblem(bad)).not.toBeNull()
    expect(resolvePath('~/a.md', '/u/t', '')).toBe('/u/t/a.md')
    expect(resolvePath('./a.md', '/u/t', '')).toBeNull()
  })
  test('a link is checked where it lands', () => {
    expect(realProblem('/u/t/notes/a.md', ['/u/t'])).toBeNull()
    expect(realProblem('/u/t/.ssh/id_rsa', ['/u/t'])).toMatch(/never read/)
    expect(realProblem('/etc/shadow', ['/u/t', '/repo'])).toMatch(/outside/)
    expect(realProblem(undefined, ['/u/t'])).toMatch(/could not be resolved/)
  })
})

describe('reading a source keeps numbers and dates only', () => {
  test('json: a list of runs becomes pass and fail dots', () => {
    const s = ok(spec())
    const v = valueOf(s, { kind: 'text', text: JSON.stringify({ runs: [{ conclusion: 'success' }, { conclusion: 'failure' }, 'pass'] }), mtimeMs: NOW }, NOW)
    expect(v).toEqual({ kind: 'flags', flags: [true, false, true] })
  })
  test('lines: counts lines holding the match', () => {
    const s = ok(spec({ source: { kind: 'lines', path: './TODO.md', match: 'TODO' }, picture: 'count' }))
    expect(valueOf(s, { kind: 'text', text: 'TODO a\nb\n- TODO c\n\n', mtimeMs: NOW }, NOW)).toEqual({ kind: 'n', n: 2 })
  })
  test('files: stale files counted; a spark of files by day', () => {
    const entries = [{ name: 'a.md', kind: 'file', mtimeMs: NOW - 40 * DAY }, { name: 'b.md', kind: 'file', mtimeMs: NOW - 1 * DAY }, { name: 'c.txt', kind: 'file', mtimeMs: NOW }, { name: 'd', kind: 'dir', mtimeMs: 0 }]
    const stale = ok(spec({ source: { kind: 'files', path: './notes', ext: 'md', olderThanDays: 30 }, picture: 'count' }))
    expect(valueOf(stale, { kind: 'files', entries }, NOW)).toEqual({ kind: 'n', n: 1 })
    const spark = ok(spec({ source: { kind: 'files', path: './notes' }, picture: 'spark' }))
    const v = valueOf(spark, { kind: 'files', entries }, NOW)
    expect(v.kind === 'ns' && v.ns.slice(-2)).toEqual([1, 1])
  })
  test('date: the first date in a file, as a countdown', () => {
    const s = ok(spec({ source: { kind: 'date', path: './ROADMAP.md' }, picture: 'countdown' }))
    const v = valueOf(s, { kind: 'text', text: '# Roadmap\nRelease on 2026-11-02, then rest.', mtimeMs: NOW }, NOW)
    expect(v).toEqual({ kind: 'at', at: Date.UTC(2026, 10, 2) })
    const t = userTileOf(s, v, NOW)
    expect(t.tile.big).toBe('10d')
    expect(t.tile.sub).toBe('to go')
  })
  test('a missing file or field draws a dash with the reason, never a guess', () => {
    const s = ok(spec({ picture: 'count' }))
    expect(valueOf(s, { kind: 'missing', why: 'no such file' }, NOW)).toEqual({ kind: 'none', why: 'no such file' })
    expect(valueOf(s, { kind: 'text', text: '{"other":1}', mtimeMs: NOW }, NOW)).toEqual({ kind: 'none', why: 'no field runs' })
    expect(userTileOf(s, { kind: 'none', why: 'no such file' }, NOW).tile.big).toBe('–')
  })
})

describe('on the board', () => {
  test('a rule marks warn and bad; lowIsBad flips it', () => {
    const s = ok(spec({ picture: 'ring', source: { kind: 'json', path: './a.json', field: 'used' }, max: 200, warnAt: 150, badAt: 190 }))
    expect(levelOf(s, 160)).toBe('warn')
    expect(levelOf(s, 195)).toBe('bad')
    const t = userTileOf(s, { kind: 'n', n: 100 }, NOW)
    expect(t.tile.big).toBe('50%')
    expect(levelOf({ ...s, lowIsBad: true }, 100)).toBe('bad')
  })
  test('the layout takes the user tiles after the shipped ones and drops tiles that are gone', () => {
    const l = parseLayout({ order: ['my:gone', 'health', 'usage'] }, [tileKey('ci')])
    expect(l.order).not.toContain('my:gone')
    expect(arranged(l).at(-1)).toBe('my:ci')
  })
  test('the board and the detail draw a user tile from what was read', () => {
    const s = ok(spec({ note: 'Open the workflow run list.' }))
    const mine = new Map([[tileKey('ci'), userTileOf(s, { kind: 'flags', flags: [true, false] }, NOW)]])
    const d: BoardData = { live: null, now: NOW, feed: { version: 1, generatedAt: NOW, recording: false, sessions7: 0, tokens7: 0, turns7: 0, cost7: null, ctx80Days7: 0, skills: [], meters: null, health: emptyHealth(), suggestionsNew: 0 }, daily: [], inbox: 0, budget: null, auto: parseAutoModes(null), mine }
    expect(tileOf('my:ci', d).big).toBe('1 failing')
    expect(detailOf('my:ci', d).lines).toEqual(['1 pass, 1 fail, 0 unknown.', 'Reads ./state/ci.json, field runs.', 'Open the workflow run list.'])
    expect(tileOf('my:gone', d).sub).toBe('not loaded')
  })
  test('the builder brief reads only and saves nothing before a yes', () => {
    const p = buildPrompt('repo', '/u/t/.claude/revenantworks/vigil/tiles')
    expect(p).toMatch(/Read only/)
    expect(p).toMatch(/Write nothing until I say yes\./)
    expect(p).toContain('/u/t/.claude/revenantworks/vigil/tiles/<id>.json')
  })
})
