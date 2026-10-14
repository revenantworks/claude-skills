import { describe, expect, test } from 'claude-code/testing'

import { newestLedger } from '../hooks/tasks-logic'
import {
  BUNDLED, GLYPHS, NEUTRAL, REVENANTWORKS, columns, contrast, contrastWarnings, discoverThemes, extractTokens, headerText, parseTheme,
  pickTheme, serializeTheme, themeFromAnswers, themeFromTokens,
  consoleBackground, grade, resolveVariant, roleChecks, themeVerdict,
} from '../hooks/theme-logic'
import { linesText, themeApplied, themeLines, themePreview } from '../hooks/view-logic'

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

describe('light and dark variants', () => {
  test('revenantworks carries a dark variant (base values) and a light one (the brand inks)', () => {
    expect(REVENANTWORKS.variants?.dark?.colors).toEqual(REVENANTWORKS.colors)
    expect(REVENANTWORKS.variants?.light?.colors).toEqual({ accent: '#006D7B', ok: 'success', warn: '#A65700', bad: '#D0007A', dim: '#415154', rule: '#A0ACAE' })
    expect(NEUTRAL.variants).toBeUndefined()
  })
  test('the console picks the variant; a one-palette theme is itself on any console', () => {
    const l = resolveVariant(REVENANTWORKS, 'light')
    expect(l.variant).toBe('light')
    expect(l.theme.colors.accent).toBe('#006D7B')
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
  test('the console background: override, then the Claude Code theme, then COLORFGBG, else assumed dark', () => {
    expect(consoleBackground('dark', 'light', null)).toMatchObject({ bg: 'light', sure: true })
    expect(consoleBackground('light-daltonized', null, null)).toMatchObject({ bg: 'light', sure: true })
    expect(consoleBackground('dark-ansi', null, null)).toMatchObject({ bg: 'dark', sure: true })
    expect(consoleBackground('auto', null, '0;15')).toMatchObject({ bg: 'light', sure: true })
    expect(consoleBackground('auto', null, '15;0')).toMatchObject({ bg: 'dark', sure: true })
    const a = consoleBackground('auto', null, null)
    expect(a).toMatchObject({ bg: 'dark', sure: false })
    expect(a.source).toMatch(/DASH_THEME_BACKGROUND/)
    expect(consoleBackground(null, 'purple', null).bg).toBe('dark')
  })
  test('a theme file may carry variants; old one-palette files stay valid', () => {
    const t = parseTheme(JSON.stringify({ name: 'two', variants: { dark: { colors: { accent: '#00E5FF' } }, light: { colors: { accent: '#006D7B' } } } })).theme!
    expect(t.variants?.light?.colors.accent).toBe('#006D7B')
    expect(t.variants?.light?.background).toBe('light')
    expect(t.colors.accent).toBe('#00E5FF')
    expect(parseTheme(serializeTheme(t)).theme).toEqual(t)
    expect(parseTheme(JSON.stringify({ name: 'a', variants: { dusk: {} } })).error).toMatch(/variant "dusk"/)
    expect(parseTheme(JSON.stringify({ name: 'a', variants: { light: { colors: { accent: 'blue' } } } })).error).toMatch(/light: colour accent/)
    expect(parseTheme(JSON.stringify({ name: 'a', colors: { accent: '#123456' } })).theme?.variants).toBeUndefined()
  })
})

describe('contrast verdicts', () => {
  test('grades: pass, borderline within 0.3 above the floor, fail under it, follows for a theme key', () => {
    expect(grade(5, 4.5)).toBe('pass')
    expect(grade(4.6, 4.5)).toBe('borderline')
    expect(grade(4.49, 4.5)).toBe('fail')
    expect(grade(null, 4.5)).toBe('follows')
  })
  test('a two-variant theme works on both consoles', () => {
    const v = themeVerdict(REVENANTWORKS)
    expect(v.dark.line).toMatch(/works/)
    expect(v.light.line).toMatch(/works/)
    expect(v.recommendation).toMatch(/any console/)
  })
  test('a dark-only theme: works on dark, unreadable on light, and the advice names neutral', () => {
    const darkOnly = { ...REVENANTWORKS, name: 'darkonly', variants: undefined }
    const v = themeVerdict(darkOnly)
    expect(v.dark.line).toMatch(/works/)
    expect(v.light.line).toMatch(/no light variant/)
    expect(v.light.line).toMatch(/accent 1\.\d\d:1/)
    expect(v.recommendation).toMatch(/dark consoles.*neutral.*light variant/)
  })
  test('neutral follows the person\'s theme everywhere', () => {
    expect(themeVerdict(NEUTRAL).recommendation).toMatch(/follows your Claude Code theme/i)
  })
})

describe('theme outputs', () => {
  const con = (bg: 'dark' | 'light') => consoleBackground(bg, null, null)
  test('show: every role, both variants, a verdict per console, one recommendation, never applied', () => {
    const text = linesText(themePreview(REVENANTWORKS, NEUTRAL, con('light')))
    expect(text).toMatch(/Dark variant/)
    expect(text).toMatch(/Light variant/)
    expect(text).toMatch(/accent\s+\S+ #006D7B\s+\d+\.\d\d:1\s+4\.5\s+pass/)
    expect(text).toMatch(/This console is light: it gets the light variant\./)
    expect(text).toMatch(/\(from Claude Code theme "light"\)/)
    expect(text).toMatch(/Dark consoles\s+works/)
    expect(text).toMatch(/Light consoles\s+works/)
    expect(text.match(/Recommendation/g)?.length).toBe(1)
    expect(text).toMatch(/Preview only — nothing changed\. Apply with \/dash theme revenantworks\./)
    for (const l of text.split('\n')) expect(l.length).toBeLessThanOrEqual(80)
  })
  test('apply: one Applied line, only failing or thin roles, an undo hint, no preview table', () => {
    const ok = linesText(themeApplied(REVENANTWORKS, NEUTRAL, con('light'), null))
    expect(ok.split('\n')[0]).toBe('Applied: revenantworks (light variant — your console is light).')
    expect(ok).toMatch(/Undo: \/dash theme neutral/)
    expect(ok).not.toMatch(/Verdict|Recommendation/)
    const darkOnly = { ...REVENANTWORKS, name: 'darkonly', variants: undefined }
    const bad = linesText(themeApplied(darkOnly, NEUTRAL, con('light'), null))
    expect(bad.split('\n')[0]).toBe('Applied: darkonly (one palette, made for dark consoles — your console is light).')
    expect(bad).toMatch(/accent\s+#00E5FF\s+1\.\d\d:1\s+under 4\.5/)
    expect(bad).not.toMatch(/\brule\s+#6C7678/)
    for (const l of bad.split('\n')) expect(l.length).toBeLessThanOrEqual(80)
  })
  test('list: active marked, each theme\'s variants, which variant is in use, fits 80 columns', () => {
    const { themes } = discoverThemes([])
    const text = linesText(themeLines(themes, 'revenantworks', resolveVariant(REVENANTWORKS, 'dark').theme, [], con('dark')))
    expect(text).toMatch(/● revenantworks\s+bundled\n\s+Brand colours.* · dark \+ light/)
    expect(text).toMatch(/neutral\s+bundled, default\n.* · follows yours/)
    expect(text).toMatch(/In use: revenantworks, dark variant/)
    for (const l of text.split('\n')) expect(l.length).toBeLessThanOrEqual(80)
  })
})
