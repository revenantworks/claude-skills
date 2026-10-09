import { describe, expect, test } from 'claude-code/testing'

import { newestLedger } from '../hooks/tasks-logic'
import {
  BUNDLED, GLYPHS, NEUTRAL, REVENANTWORKS, columns, contrast, contrastWarnings, discoverThemes, extractTokens, headerText, parseTheme,
  pickTheme, serializeTheme, themeFromAnswers, themeFromTokens,
} from '../hooks/theme-logic'

describe('theme files', () => {
  test('neutral is the default and uses only the person\'s theme keys; revenantworks is opt-in', () => {
    expect(pickTheme(discoverThemes([]).themes, null, null).theme).toBe(NEUTRAL)
    expect(Object.values(NEUTRAL.colors).every(c => !c.startsWith('#'))).toBe(true)
    expect(Object.keys(BUNDLED).sort()).toEqual(['neutral', 'revenantworks'])
    expect(pickTheme(discoverThemes([]).themes, null, 'revenantworks').theme).toBe(REVENANTWORKS)
  })
  test('DASH_THEME wins over the saved choice; an unknown name falls back with a notice', () => {
    const { themes } = discoverThemes([])
    expect(pickTheme(themes, 'revenantworks', 'neutral').theme.name).toBe('revenantworks')
    const r = pickTheme(themes, null, 'ghost')
    expect(r.theme).toBe(NEUTRAL)
    expect(r.notice).toMatch(/theme "ghost" not found/)
  })
  test('a theme file is refused for each kind of mistake, with the reason', () => {
    expect(parseTheme('{').error).toBe('not valid JSON')
    expect(parseTheme('[]').error).toBe('not a JSON object')
    expect(parseTheme(JSON.stringify({ name: 'Bad Name' })).error).toMatch(/lower-case/)
    expect(parseTheme(JSON.stringify({ name: 'a', colors: { shiny: '#fff' } })).error).toMatch(/unknown colour role "shiny"/)
    expect(parseTheme(JSON.stringify({ name: 'a', colors: { ok: 'green' } })).error).toMatch(/colour ok must be/)
    expect(parseTheme(JSON.stringify({ name: 'a', header: 'fancy' })).error).toMatch(/header/)
    expect(parseTheme(JSON.stringify({ name: 'a', glyphs: { ok: 'toolong' } })).error).toMatch(/glyph ok/)
    expect(parseTheme(JSON.stringify({ name: 'a', background: 'blue' })).error).toMatch(/background/)
  })
  test('a partial theme takes neutral for what it leaves out, and round-trips', () => {
    const t = parseTheme(JSON.stringify({ name: 'part', colors: { accent: '#123456' }, glyphs: 'ascii' })).theme!
    expect(t.colors).toEqual({ ...NEUTRAL.colors, accent: '#123456' })
    expect(t.glyphs).toEqual(GLYPHS.ascii)
    expect(parseTheme(serializeTheme(t)).theme).toEqual(t)
  })
  test('the file name names a theme that has no name field; a bad file is skipped, not fatal', () => {
    const d = discoverThemes([{ file: 'x/plain-one.json', text: '{"colors":{"bad":"#ff0000"}}' }, { file: 'nope.json', text: null }])
    expect(d.themes['plain-one']?.source).toBe('user')
    expect(d.errors).toEqual(['nope.json: not valid JSON'])
  })
})

describe('contrast', () => {
  test('WCAG ratios: black on white is 21:1, a colour on itself is 1:1', () => {
    expect(Math.round(contrast('#000000', '#FFFFFF') * 1000) / 1000).toBe(21)
    expect(Math.round(contrast('#777', '#777777') * 1000) / 1000).toBe(1)
  })
  test('the bundled revenantworks theme clears every floor on a dark background', () => {
    expect(contrastWarnings(REVENANTWORKS)).toEqual([])
  })
  test('the same colours on a light background are flagged', () => {
    const light = { ...REVENANTWORKS, background: 'light' }
    expect(contrastWarnings(light).join('\n')).toMatch(/accent #00E5FF is 1\.\d\d:1 on a light background/)
  })
})

describe('making a theme', () => {
  test('from answers: bare hex takes a #, keys are checked', () => {
    const r = themeFromAnswers('acme', ['accent=3366ff', 'header=block', 'background=light'])
    expect(r.theme?.colors.accent).toBe('#3366ff')
    expect(r.theme?.header).toBe('block')
    expect(themeFromAnswers('acme', ['colour=#fff']).error).toMatch(/unknown key "colour"/)
    expect(themeFromAnswers('acme', ['accent']).error).toMatch(/not key=value/)
  })
  test('from a brand definition table: the role words on each row pick the colour', () => {
    const md = [
      '| role | token | hex |',
      '| accent | `threshold` | `#00E5FF` |',
      '| muted text | `ash` | `#8D9FA2` |',
      '| border | `edge` | `#6C7678` |',
      '| `magenta` | `#FF0099` | hot, urgent, wrong | **error / broken** |',
      '| `ember` | `#FF8B00` | warm, live | **warn / live** |',
      '| background | `void` | `#060B0C` |',
    ].join('\n')
    const r = themeFromTokens('house', md)
    expect(r.theme?.colors).toEqual({ accent: '#00E5FF', ok: 'success', warn: '#FF8B00', bad: '#FF0099', dim: '#8D9FA2', rule: '#6C7678' })
    expect(r.theme?.background).toBe('dark')
    expect(r.missing).toEqual(['ok'])
  })
  test('CSS variables and a file with no colour', () => {
    expect(extractTokens(':root {\n  --color-primary: #112233;\n  --success: #0a0;\n}')).toEqual([{ name: 'color primary', hex: '#112233' }, { name: 'success', hex: '#0a0' }])
    expect(themeFromTokens('x', 'no colours here').error).toBe('no hex colours found in the file')
  })
})

describe('drawing helpers', () => {
  test('headers in each style and aligned columns', () => {
    expect(headerText(NEUTRAL, 'Health')).toMatch(/^── Health ─+$/)
    expect(headerText(NEUTRAL, 'Health').length).toBe(60)
    expect(headerText(REVENANTWORKS, 'Health')).toBe('▍ Health')
    expect(headerText({ ...NEUTRAL, header: 'plain' }, 'Health')).toBe('Health')
    expect(columns([['a', '1'], ['long', '22']], [1])).toEqual(['  a      1', '  long  22'])
  })
})

describe('current run', () => {
  test('the newest ledger file wins; a tie breaks by path', () => {
    expect(newestLedger([{ path: '/a/ledger.md', mtimeMs: 5 }, { path: '/b/ledger.md', mtimeMs: 9 }])).toBe('/b/ledger.md')
    expect(newestLedger([])).toBeNull()
  })
})
