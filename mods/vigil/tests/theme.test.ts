import { describe, expect, test } from 'claude-code/testing'

import { newestLedger } from '../hooks/tasks-logic'
import {
  BUNDLED, GLYPHS, HC_LIGHT, NEUTRAL, OFF, REVENANTWORKS, orderThemes, wantsContrast, columns, contrast, discoverThemes, headerText, parseActive, parseBackground, parseTheme,
  pickTheme, consoleBackground, grade, resolveVariant, roleChecks,
} from '../hooks/theme-logic'
import { linesText, themeApplied, themeLines } from '../hooks/view-logic'

describe('theme files', () => {
  test('neutral is the default and uses only the person\'s theme keys; revenantworks is opt-in', () => {
    expect(pickTheme(discoverThemes([]).themes, null, null).theme).toBe(NEUTRAL)
    expect(Object.values(NEUTRAL.colors).every(c => !c.startsWith('#'))).toBe(true)
    expect(Object.keys(BUNDLED).sort()).toEqual(['hc-light', 'neutral', 'off', 'revenantworks'])
    expect(pickTheme(discoverThemes([]).themes, null, 'revenantworks').theme).toBe(REVENANTWORKS)
  })
  test('more contrast picks hc-light only when nothing else was chosen', () => {
    const { themes } = discoverThemes([])
    expect(pickTheme(themes, null, null, true).theme).toBe(HC_LIGHT)
    expect(pickTheme(themes, null, 'revenantworks', true).theme).toBe(REVENANTWORKS)
    expect(pickTheme(themes, 'neutral', null, true).theme).toBe(NEUTRAL)
    expect(wantsContrast('more', null)).toBe(true)
    expect(wantsContrast('normal', 'dark-high-contrast')).toBe(false)
    expect(wantsContrast(null, 'dark-high-contrast')).toBe(true)
    expect(wantsContrast(null, 'dark-daltonized')).toBe(false)
    expect(wantsContrast(null, null)).toBe(false)
  })
  test('the picker order is neutral, the brand, high contrast, off, then the person\'s own', () => {
    expect(orderThemes(['mine', 'off', 'hc-light', 'abc', 'revenantworks', 'neutral'])).toEqual(['neutral', 'revenantworks', 'hc-light', 'off', 'abc', 'mine'])
    expect(Object.values(OFF.colors).every(c => c === 'text')).toBe(true)
    expect(OFF.header).toBe('plain')
  })
  test('VIGIL_THEME wins over the saved choice; an unknown name falls back with a notice', () => {
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
  test('a partial theme takes neutral for what it leaves out', () => {
    const t = parseTheme(JSON.stringify({ name: 'part', colors: { accent: '#123456' }, glyphs: 'ascii' })).theme!
    expect(t.colors).toEqual({ ...NEUTRAL.colors, accent: '#123456' })
    expect(t.glyphs).toEqual(GLYPHS.ascii)
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

describe('light and dark variants', () => {
  test('revenantworks carries a dark variant (base values) and a light one (the brand inks)', () => {
    expect(REVENANTWORKS.variants?.dark?.colors).toEqual(REVENANTWORKS.colors)
    expect(REVENANTWORKS.variants?.light?.colors).toEqual({ accent: '#006A77', ok: '#0060BB', warn: '#944E00', bad: '#BB006F', dim: '#554B3F', rule: '#BDB6AD' })
    expect(NEUTRAL.variants).toBeUndefined()
  })
  test('the console picks the variant; a one-palette theme is itself on any console', () => {
    const l = resolveVariant(REVENANTWORKS, 'light')
    expect(l.variant).toBe('light')
    expect(l.theme.colors.accent).toBe('#006A77')
    expect(l.theme.background).toBe('light')
    expect(l.theme.header).toBe('block')
    expect(resolveVariant(REVENANTWORKS, 'dark').theme.colors.accent).toBe('#00E5FF')
    const n = resolveVariant(NEUTRAL, 'light')
    expect(n.variant).toBeNull()
    expect(n.theme).toBe(NEUTRAL)
  })
  test('both revenantworks variants clear every floor on their own console', () => {
    for (const bg of ['dark', 'light'] as const) {
      const checks = roleChecks(resolveVariant(REVENANTWORKS, bg).theme.colors, bg)
      expect(checks.filter(c => c.grade === 'fail' || c.grade === 'borderline')).toEqual([])
    }
  })
  test('hc-light clears every floor on a light console', () => {
    const checks = roleChecks(HC_LIGHT.colors, 'light')
    expect(checks.filter(c => c.grade === 'fail' || c.grade === 'borderline')).toEqual([])
  })
  test('the console background: override, then the Claude Code theme, then COLORFGBG, else assumed dark', () => {
    expect(consoleBackground('dark', 'light', null)).toMatchObject({ bg: 'light', sure: true })
    expect(consoleBackground('light-daltonized', null, null)).toMatchObject({ bg: 'light', sure: true })
    expect(consoleBackground('dark-ansi', null, null)).toMatchObject({ bg: 'dark', sure: true })
    expect(consoleBackground('auto', null, '0;15')).toMatchObject({ bg: 'light', sure: true })
    expect(consoleBackground('auto', null, '15;0')).toMatchObject({ bg: 'dark', sure: true })
    const a = consoleBackground('auto', null, null)
    expect(a).toMatchObject({ bg: 'dark', sure: false })
    expect(a.source).toMatch(/theme background/)
    expect(consoleBackground(null, 'purple', null).bg).toBe('dark')
  })
  test('a theme file may carry variants; old one-palette files stay valid', () => {
    const t = parseTheme(JSON.stringify({ name: 'two', variants: { dark: { colors: { accent: '#00E5FF' } }, light: { colors: { accent: '#006D7B' } } } })).theme!
    expect(t.variants?.light?.colors.accent).toBe('#006D7B')
    expect(t.variants?.light?.background).toBe('light')
    expect(t.colors.accent).toBe('#00E5FF')
    expect(parseTheme(JSON.stringify({ name: 'a', variants: { dusk: {} } })).error).toMatch(/variant "dusk"/)
    expect(parseTheme(JSON.stringify({ name: 'a', variants: { light: { colors: { accent: 'blue' } } } })).error).toMatch(/light: colour accent/)
    expect(parseTheme(JSON.stringify({ name: 'a', colors: { accent: '#123456' } })).theme?.variants).toBeUndefined()
  })
})

describe('contrast grades', () => {
  test('pass, borderline within 0.3 above the floor, fail under it, follows for a theme key', () => {
    expect(grade(5, 4.5)).toBe('pass')
    expect(grade(4.6, 4.5)).toBe('borderline')
    expect(grade(4.49, 4.5)).toBe('fail')
    expect(grade(null, 4.5)).toBe('follows')
  })
})

describe('theme outputs', () => {
  const con = (bg: 'dark' | 'light') => consoleBackground(bg, null, null)
  test('apply: one line, then the undo', () => {
    const ok = linesText(themeApplied(REVENANTWORKS, con('light'), null))
    expect(ok).toBe('Applied: revenantworks (light variant; this console is light).\nUndo: /rw-vigil theme neutral')
    const bad = linesText(themeApplied({ ...REVENANTWORKS, name: 'darkonly', variants: undefined }, con('light'), 'mine'))
    expect(bad.split('\n')[0]).toBe('Applied: darkonly (one palette, made for dark consoles; this console is light).')
    expect(bad).toMatch(/VIGIL_THEME=mine is set and wins/)
  })
  test('the picker: active marked with no button, every other theme a Use button in its own accent; fits 80 columns', () => {
    const { themes } = discoverThemes([])
    const lines = themeLines(themes, 'revenantworks', resolveVariant(REVENANTWORKS, 'dark').theme, [], con('dark'))
    const row = (n: string) => lines.find(l => l.text.includes(` ${n} `))!
    expect(row('revenantworks').text).toMatch(/● revenantworks/)
    expect(row('revenantworks').buttons).toBeUndefined()
    expect(row('neutral').buttons?.[0]).toEqual({ label: 'Use', press: { kind: 'theme', name: 'neutral' } })
    expect(row('hc-light').color).toBe('#044C56')
    for (const l of lines) expect(l.text.length).toBeLessThanOrEqual(80)
    expect(lines.find(l => /This console is dark/.test(l.text))!.buttons!.map(b => b.label)).toEqual(['dark', 'light', 'auto'])
  })
  test('theme.json keeps the choice and the background; a bad file reads as neither', () => {
    expect(parseActive('{"active":"off","background":"light"}')).toBe('off')
    expect(parseBackground('{"active":"off","background":"light"}')).toBe('light')
    expect(parseBackground('{"background":"blue"}')).toBeNull()
    expect(parseBackground('nope')).toBeNull()
  })
})
