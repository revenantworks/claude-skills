import { describe, expect, test } from 'claude-code/testing'

import type { Feed, SkillRow } from '../hooks/collector-logic'
import { NEUTRAL } from '../hooks/theme-logic'
import { dupesLines, findDupes, healthLines, linesText, skillSource, skillsLines } from '../hooks/view-logic'

const row = (name: string, over: Partial<SkillRow> = {}): SkillRow => ({
  name, listed: true, firstListed: 0, fires7: 0, fires30: 0, slash30: 0, auto30: 0, failures30: 0, misroutes30: 0, tokens7: 0, cost7: null, lastFired: null, ...over,
})
const feedOf = (skills: SkillRow[]): Feed => ({ skills } as unknown as Feed)
const fit80 = (text: string) => { for (const l of text.split('\n')) expect(l.length).toBeLessThanOrEqual(80) }

describe('skills view: the filter', () => {
  const skills = [
    row('alpha', { fires30: 3, slash30: 1, auto30: 2, tokens7: 1500, cost7: 0.12 }),
    row('quiet-one'),
    row('quiet-two'),
    row('broken', { failures30: 1 }),
  ]
  test('the default view shows what fired or failed, then one line for the rest', () => {
    const text = linesText(skillsLines(feedOf(skills), NEUTRAL))
    expect(text).toMatch(/alpha\s+3\s+1\s+2\s+0\s+0\s+1\.5k\s+\$0\.12/)
    expect(text).toMatch(/broken/)
    expect(text).not.toMatch(/quiet-one/)
    expect(text).toMatch(/2 enabled, never fired · \/dash skills all/)
    expect(text).not.toMatch(/ - +- /)
    expect(text.match(/misr/g)?.length).toBe(2)
    fit80(text)
  })
  test('/dash skills all keeps every row, with · for a skill that never fired', () => {
    const text = linesText(skillsLines(feedOf(skills), NEUTRAL, { all: true }))
    expect(text).toMatch(/quiet-one\s+·/)
    expect(text).not.toMatch(/never fired · \/dash skills all/)
    fit80(text)
  })
})

describe('skills view: sources and names', () => {
  test('the source: the engine\'s word when known, else the name\'s prefix', () => {
    expect(skillSource('anthropic-skills:docx')).toBe('claude.ai synced')
    expect(skillSource('engineering:code-review')).toBe('plugin')
    expect(skillSource('revenantworks-foundation-agentwright')).toBe('local')
    expect(skillSource('simplify', 'built-in')).toBe('built-in')
    expect(skillSource('docx', 'syncedSkills')).toBe('claude.ai synced')
    expect(skillSource('x', 'userSettings')).toBe('local')
  })
  test('rows group by source in a fixed order, with short names', () => {
    const skills = [
      row('anthropic-skills:docx', { fires30: 1 }),
      row('simplify', { fires30: 2 }),
      row('engineering:code-review', { fires30: 4 }),
      row('revenantworks-foundation-agentwright', { fires30: 5 }),
    ]
    const text = linesText(skillsLines(feedOf(skills), NEUTRAL, { sources: { simplify: 'built-in' } }))
    const at = (s: RegExp) => text.search(s)
    expect(at(/^  local$/m)).toBeLessThan(at(/^  plugin$/m))
    expect(at(/^  plugin$/m)).toBeLessThan(at(/^  claude\.ai synced$/m))
    expect(at(/^  claude\.ai synced$/m)).toBeLessThan(at(/^  built-in$/m))
    expect(text).toMatch(/^ {4}agentwright\s+5/m)
    expect(text).toMatch(/^ {4}docx\s+1/m)
    expect(text).not.toMatch(/revenantworks-foundation-/)
    fit80(text)
  })
})

describe('skills view: duplicates', () => {
  const skills = [
    row('revenantworks-foundation-agentwright', { fires30: 2 }),
    row('anthropic-skills:revenantworks-foundation-agentwright'),
    row('docx'),
    row('anthropic-skills:docx'),
    row('alone', { fires30: 1 }),
  ]
  test('the same skill from two sources is a pair', () => {
    const d = findDupes(skills)
    expect(d.map(x => x.base)).toEqual(['agentwright', 'docx'])
    expect(d[0]!.sources).toEqual(['local', 'claude.ai synced'])
  })
  test('one line in the skills view, a dupes view, and a health item', () => {
    const text = linesText(skillsLines(feedOf(skills), NEUTRAL))
    expect(text).toMatch(/2 skills loaded twice \(local \+ claude\.ai synced\): \/dash skills dupes/)
    const dv = linesText(dupesLines(feedOf(skills), NEUTRAL))
    expect(dv).toMatch(/agentwright\s+local, claude\.ai synced/)
    expect(dv).toMatch(/docx\s+local, claude\.ai synced/)
    fit80(dv)
    const h = linesText(healthLines({ plugins: {}, drift: [], gatewarden: null, pinsChanged: 0 } as never, NEUTRAL, 2))
    expect(h).toMatch(/2 skills loaded twice: \/dash skills dupes/)
    expect(linesText(dupesLines(feedOf([row('solo')]), NEUTRAL))).toMatch(/No skill is loaded twice/)
  })
})
