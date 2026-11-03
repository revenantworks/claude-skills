// vigil themes: pure logic (no $). A theme names a colour for each role the views use, a glyph set
// and a header style. Four themes ship in the mod, in picker order: `neutral` (the default; every
// colour is a key of the person's own Claude Code theme, so it follows the app's light or dark),
// `revenantworks` (opt-in, a dark and a light variant), `hc-light` (the default when the person asks
// for more contrast on a light console) and `off` (no colour). The person's own themes live as
// JSON files in ~/.claude/revenantworks/themes/ and win over a bundled theme of the same name.
// Colour shows only where a surface paints (the /rw-vigil pane); text surfaces get the glyphs and
// headers, never escape codes.

export const ROLES = ['accent', 'ok', 'warn', 'bad', 'dim', 'rule'] as const
export type Role = (typeof ROLES)[number]
export type HeaderStyle = 'rule' | 'plain' | 'block'
export type Glyphs = { ok: string; warn: string; bad: string; on: string; off: string; sep: string; rule: string; mark: string; full: string; empty: string }
export type ConsoleBg = 'dark' | 'light'
/** One set of colours for one console background. */
export type Palette = { background: string; colors: Record<Role, string> }
/**
 * `background` and `colors` are the palette in use. A theme may also carry `variants`, one palette
 * for dark consoles and one for light; vigil then picks the one that matches the console
 * (resolveVariant). A theme without variants has one palette for every console.
 */
export type Theme = { name: string; description: string; background: string; colors: Record<Role, string>; glyphs: Glyphs; header: HeaderStyle; variants?: Partial<Record<ConsoleBg, Palette>> }

export const GLYPHS: Record<'unicode' | 'ascii', Glyphs> = {
  unicode: { ok: '✓', warn: '!', bad: '✗', on: '●', off: '○', sep: ' · ', rule: '─', mark: '▍', full: '█', empty: '░' },
  ascii: { ok: '+', warn: '!', bad: 'x', on: '*', off: 'o', sep: ' | ', rule: '-', mark: '>', full: '#', empty: '.' },
}

/** Claude Code theme keys a colour may name; they follow the person's terminal theme. */
export const THEME_KEYS = ['text', 'inverseText', 'inactive', 'subtle', 'suggestion', 'remember', 'success', 'error', 'warning', 'merged', 'claude', 'permission', 'planMode', 'autoAccept', 'promptBorder', 'bashBorder', 'ide'] as const

export const NEUTRAL: Theme = {
  name: 'neutral',
  description: 'Your own Claude Code theme colours',
  background: 'dark',
  colors: { accent: 'suggestion', ok: 'success', warn: 'warning', bad: 'error', dim: 'subtle', rule: 'inactive' },
  glyphs: GLYPHS.unicode,
  header: 'rule',
}

// The one brand theme in this repo (owner decision 2026-10-09): opt-in, never the default. The
// dark variant is the brand's published dark-ground tokens: threshold-blue, ember-orange (warn /
// live), glitch-magenta (error / broken), ash-grey (muted text) and the high-contrast border. The
// light variant is the brand's base/ink rule: each accent's `ink` companion (solved to clear
// 4.5:1 on warm bone, definition v2.25.0) and the light-role neutrals (muted text #554B3F, border
// #BDB6AD). `ok` is the brand's `success`, azure (definition v2.28.0): #53A0FF dark, #0060BB light.
export const REVENANTWORKS: Theme = {
  name: 'revenantworks',
  description: 'Brand colours, cursor-block headers',
  background: 'dark',
  colors: { accent: '#00E5FF', ok: '#53A0FF', warn: '#FF8B00', bad: '#FF0099', dim: '#8D9FA2', rule: '#6C7678' },
  glyphs: GLYPHS.unicode,
  header: 'block',
  variants: {
    dark: { background: 'dark', colors: { accent: '#00E5FF', ok: '#53A0FF', warn: '#FF8B00', bad: '#FF0099', dim: '#8D9FA2', rule: '#6C7678' } },
    light: { background: 'light', colors: { accent: '#006A77', ok: '#0060BB', warn: '#944E00', bad: '#BB006F', dim: '#554B3F', rule: '#BDB6AD' } },
  },
}

// The brand's high-contrast light tokens (definition v2.27.0; owner 2026-10-23: high contrast is the
// light set, not the dark one): a warm bone ground, never pure white, the inks clearing 7:1 on it and
// the border 4.5:1. Picked by itself only when the person asks for more contrast on a light console
// (pickTheme); otherwise opt-in like revenantworks. `ok` is the brand's hc-light `success`,
// #004387 (definition v2.28.0).
export const HC_LIGHT: Theme = {
  name: 'hc-light',
  description: 'High contrast on a light ground',
  background: '#FAF6F1',
  colors: { accent: '#044C56', ok: '#004387', warn: '#6B3704', bad: '#86044D', dim: '#4C4236', rule: '#746D64' },
  glyphs: GLYPHS.unicode,
  header: 'block',
}

// Theming switched off: every role is the person's own text colour and headers are plain.
export const OFF: Theme = {
  name: 'off',
  description: 'No colour, plain headers',
  background: 'dark',
  colors: { accent: 'text', ok: 'text', warn: 'text', bad: 'text', dim: 'text', rule: 'text' },
  glyphs: GLYPHS.unicode,
  header: 'plain',
}

export const BUNDLED: Record<string, Theme> = { neutral: NEUTRAL, revenantworks: REVENANTWORKS, 'hc-light': HC_LIGHT, off: OFF }

/** The picker order (owner, 2026-10-23): neutral, the brand, high contrast, off; the person's own after. */
export const THEME_ORDER: readonly string[] = ['neutral', 'revenantworks', 'hc-light', 'off']

/** Names sorted for the picker: the bundled order first, then the person's themes A to Z. */
export const orderThemes = (names: readonly string[]): string[] => {
  const rank = (n: string) => (THEME_ORDER.includes(n) ? THEME_ORDER.indexOf(n) : THEME_ORDER.length)
  return [...names].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
}

/**
 * Whether the person asked for more contrast: VIGIL_THEME_CONTRAST=more (the terminal has no
 * prefers-contrast query to read), or a Claude Code or editor theme whose name says high contrast.
 */
export const wantsContrast = (override: string | null, ccTheme: string | null): boolean => {
  const o = (override ?? '').trim().toLowerCase()
  if (o === 'more' || o === 'high') return true
  if (o === 'normal' || o === 'no-preference') return false
  return /contrast|(^|-)hc(-|$)/.test((ccTheme ?? '').trim().toLowerCase())
}

const HEX = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/
export const isColor = (v: unknown): v is string => typeof v === 'string' && (HEX.test(v) || (THEME_KEYS as readonly string[]).includes(v))
export const NAME = /^[a-z0-9][a-z0-9-]{0,39}$/

/** A theme file's text to a theme, or the reason it is refused. Missing roles take the neutral value. */
export const parseTheme = (text: string | null, fallbackName = ''): { theme: Theme | null; error: string | null } => {
  let o: Record<string, unknown>
  try {
    o = JSON.parse(text ?? '') as Record<string, unknown>
    if (!o || typeof o !== 'object' || Array.isArray(o)) return { theme: null, error: 'not a JSON object' }
  } catch {
    return { theme: null, error: 'not valid JSON' }
  }
  const name = typeof o.name === 'string' ? o.name : fallbackName
  if (!NAME.test(name)) return { theme: null, error: `name "${String(name).slice(0, 40)}" must be lower-case letters, digits and dashes` }
  const readColors = (raw: unknown, base: Record<Role, string>, where: string): { colors: Record<Role, string> } | { error: string } => {
    const colors = { ...base }
    if (raw === undefined) return { colors }
    if (!raw || typeof raw !== 'object') return { error: `${where}"colors" must be an object` }
    for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
      if (!(ROLES as readonly string[]).includes(k)) return { error: `${where}unknown colour role "${k.slice(0, 20)}" (roles: ${ROLES.join(', ')})` }
      if (!isColor(v)) return { error: `${where}colour ${k} must be #rgb, #rrggbb or a Claude Code theme key` }
      colors[k as Role] = v
    }
    return { colors }
  }
  const isBg = (b: unknown): boolean => b === 'dark' || b === 'light' || (typeof b === 'string' && HEX.test(b))
  let variants: Partial<Record<ConsoleBg, Palette>> | undefined
  if (o.variants !== undefined) {
    if (!o.variants || typeof o.variants !== 'object' || Array.isArray(o.variants)) return { theme: null, error: '"variants" must be an object with dark and/or light' }
    variants = {}
    for (const [k, v] of Object.entries(o.variants as Record<string, unknown>)) {
      if (k !== 'dark' && k !== 'light') return { theme: null, error: `variant "${k.slice(0, 20)}" must be dark or light` }
      const vo = (v && typeof v === 'object' ? v : {}) as Record<string, unknown>
      const c = readColors(vo.colors, NEUTRAL.colors, `${k}: `)
      if ('error' in c) return { theme: null, error: c.error }
      const vb = vo.background ?? k
      if (!isBg(vb)) return { theme: null, error: `${k}: "background" must be dark, light or a hex colour` }
      variants[k] = { background: vb as string, colors: c.colors }
    }
    if (!variants.dark && !variants.light) variants = undefined
  }
  // The top-level palette: its own colours, else the dark variant's (or the light one's).
  const fallback = variants?.dark ?? variants?.light
  const top = readColors(o.colors, o.colors === undefined && fallback ? fallback.colors : NEUTRAL.colors, '')
  if ('error' in top) return { theme: null, error: top.error }
  const colors = top.colors
  let glyphs = GLYPHS.unicode
  if (o.glyphs === 'ascii' || o.glyphs === 'unicode') glyphs = GLYPHS[o.glyphs]
  else if (o.glyphs && typeof o.glyphs === 'object') {
    glyphs = { ...GLYPHS.unicode }
    for (const [k, v] of Object.entries(o.glyphs as Record<string, unknown>)) {
      if (!(k in glyphs) || typeof v !== 'string' || v.length === 0 || v.length > 3) return { theme: null, error: `glyph ${k.slice(0, 20)} must be a known glyph of 1-3 characters` }
      glyphs = { ...glyphs, [k]: v }
    }
  } else if (o.glyphs !== undefined) return { theme: null, error: '"glyphs" must be "unicode", "ascii" or an object' }
  const header = o.header ?? 'rule'
  if (header !== 'rule' && header !== 'plain' && header !== 'block') return { theme: null, error: '"header" must be rule, plain or block' }
  const background = o.background ?? (o.colors === undefined && fallback ? fallback.background : 'dark')
  if (!isBg(background)) return { theme: null, error: '"background" must be dark, light or a hex colour' }
  const description = typeof o.description === 'string' ? o.description.slice(0, 120) : ''
  return { theme: { name, description, background: background as string, colors, glyphs, header, ...(variants ? { variants } : {}) }, error: null }
}

/** The palette a console gets: the matching variant when the theme has one, else the theme as it is. */
export const resolveVariant = (t: Theme, bg: ConsoleBg): { theme: Theme; variant: ConsoleBg | null } => {
  const v = t.variants?.[bg]
  if (!v) return { theme: t, variant: null }
  return { theme: { ...t, background: v.background, colors: v.colors }, variant: bg }
}

/** Which ground a one-palette theme was made for. */
export const madeFor = (background: string): ConsoleBg => (background === 'light' ? 'light' : background === 'dark' ? 'dark' : lum(background) < 0.2 ? 'dark' : 'light')

export type ConsoleInfo = { bg: ConsoleBg; sure: boolean; source: string }

/**
 * The console's background. VIGIL_THEME_BACKGROUND wins; then the Claude Code theme setting (the
 * `theme` row of /config: `dark`, `light`, `dark-daltonized`, `light-ansi`...); for `auto`, the
 * terminal's COLORFGBG ("fg;bg", bg 7 or 15 is a light ground); else dark, marked as a guess.
 */
export const consoleBackground = (ccTheme: string | null, override: string | null, colorfgbg: string | null): ConsoleInfo => {
  const o = (override ?? '').trim().toLowerCase()
  if (o === 'dark' || o === 'light') return { bg: o, sure: true, source: `your choice (${o})` }
  const cc = (ccTheme ?? '').trim().toLowerCase()
  if (cc.startsWith('light')) return { bg: 'light', sure: true, source: `Claude Code theme "${cc.slice(0, 24)}"` }
  if (cc.startsWith('dark')) return { bg: 'dark', sure: true, source: `Claude Code theme "${cc.slice(0, 24)}"` }
  const m = /(\d+)\s*$/.exec(colorfgbg ?? '')
  if (m) {
    const n = Number(m[1])
    return { bg: n === 7 || n === 15 ? 'light' : 'dark', sure: true, source: 'the terminal (COLORFGBG)' }
  }
  return { bg: 'dark', sure: false, source: 'a guess; say with /rw-vigil theme background light|dark' }
}

export type ThemeEntry = { theme: Theme; source: 'bundled' | 'user'; overrides: boolean }

/** Every theme by name: bundled first, then the person's files, a file winning over a bundled name. */
export const discoverThemes = (userFiles: ReadonlyArray<{ file: string; text: string | null }>): { themes: Record<string, ThemeEntry>; errors: string[] } => {
  const themes: Record<string, ThemeEntry> = {}
  for (const t of Object.values(BUNDLED)) themes[t.name] = { theme: t, source: 'bundled', overrides: false }
  const errors: string[] = []
  for (const f of userFiles) {
    const base = f.file.replace(/^.*\//, '').replace(/\.json$/i, '')
    const r = parseTheme(f.text, base)
    if (!r.theme) {
      errors.push(`${base}.json: ${r.error}`)
      continue
    }
    themes[r.theme.name] = { theme: r.theme, source: 'user', overrides: BUNDLED[r.theme.name] !== undefined }
  }
  return { themes, errors }
}

/**
 * The active theme: the env name, else the saved choice, else hc-light when the person asked for more
 * contrast (on a light console: the caller decides), else neutral; a name not found falls back with a notice.
 */
export const pickTheme = (themes: Record<string, ThemeEntry>, envName: string | null, saved: string | null, contrast = false): { theme: Theme; notice: string | null } => {
  const want = (envName || saved || (contrast ? 'hc-light' : 'neutral')).trim().toLowerCase()
  const hit = themes[want]
  if (hit) return { theme: hit.theme, notice: null }
  return { theme: themes.neutral?.theme ?? NEUTRAL, notice: `vigil: theme "${want.slice(0, 40)}" not found or invalid; using neutral. /rw-vigil theme lists the themes.` }
}

/** The console background saved with the choice: what the app is drawn on, when no host says. */
export const parseBackground = (text: string | null): ConsoleBg | null => {
  try {
    const b = (JSON.parse(text ?? '') as { background?: unknown }).background
    return b === 'dark' || b === 'light' ? b : null
  } catch {
    return null
  }
}

export const parseActive = (text: string | null): string | null => {
  try {
    const o = JSON.parse(text ?? '') as { active?: unknown }
    return typeof o.active === 'string' ? o.active : null
  } catch {
    return null
  }
}

// ---------- contrast ----------

const rgb = (hex: string): [number, number, number] => {
  const h = hex.length === 4 ? hex.slice(1).split('').map(c => c + c).join('') : hex.slice(1)
  return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255) as [number, number, number]
}
const lum = (hex: string): number => {
  const [r, g, b] = rgb(hex).map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number]
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
/** WCAG contrast ratio of two hex colours. */
export const contrast = (a: string, b: string): number => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p) as [number, number]
  return (x + 0.05) / (y + 0.05)
}
export const BACKGROUNDS = { dark: '#121212', light: '#FFFFFF' } as const
/** The floor each role must clear: text roles 4.5:1, dim text 3:1, rules (decoration) 1.5:1. */
export const FLOORS: Record<Role, number> = { accent: 4.5, ok: 4.5, warn: 4.5, bad: 4.5, dim: 3, rule: 1.5 }

export type Grade = 'pass' | 'borderline' | 'fail' | 'follows'
/** A ratio against its floor: under it fails; within 0.3 above it is borderline; null (a theme key) follows the terminal. */
export const grade = (ratio: number | null, floor: number): Grade => (ratio === null ? 'follows' : ratio < floor ? 'fail' : ratio < floor + 0.3 ? 'borderline' : 'pass')

export type RoleCheck = { role: Role; color: string; ratio: number | null; floor: number; grade: Grade }

/** Every role's contrast on a console ground (#121212 dark, #FFFFFF light, or a hex). */
export const roleChecks = (colors: Record<Role, string>, bg: ConsoleBg | string): RoleCheck[] => {
  const ground = bg === 'dark' || bg === 'light' ? BACKGROUNDS[bg] : bg
  return ROLES.map(role => {
    const color = colors[role]
    const ratio = HEX.test(color) ? contrast(color, ground) : null
    return { role, color, ratio, floor: FLOORS[role], grade: grade(ratio, FLOORS[role]) }
  })
}

// ---------- drawing helpers ----------

export type Tone = 'head' | 'accent' | 'ok' | 'warning' | 'error' | 'dim' | 'bold' | 'rule'

/** The colour and weight the pane paints a tone with. */
export const toneStyle = (t: Theme, tone: Tone | undefined): { color?: string; bold?: boolean; dimColor?: boolean } => {
  switch (tone) {
    case 'head': return { color: t.colors.accent, bold: true }
    case 'accent': return { color: t.colors.accent }
    case 'ok': return { color: t.colors.ok }
    case 'warning': return { color: t.colors.warn }
    case 'error': return { color: t.colors.bad }
    case 'dim': return { color: t.colors.dim }
    case 'rule': return { color: t.colors.rule }
    case 'bold': return { bold: true }
    default: return {}
  }
}

export const WIDTH = 60

/** A section header as plain text in the theme's style. */
export const headerText = (t: Theme, title: string): string => {
  if (t.header === 'plain') return title
  if (t.header === 'block') return `${t.glyphs.mark} ${title}`
  const lead = `${t.glyphs.rule.repeat(2)} ${title} `
  return lead + t.glyphs.rule.repeat(Math.max(3, WIDTH - lead.length))
}

/** A 10-cell bar for a percentage. */
export const bar = (t: Theme, pct: number, cells = 10): string => {
  const n = Math.max(0, Math.min(cells, Math.round((pct / 100) * cells)))
  return t.glyphs.full.repeat(n) + t.glyphs.empty.repeat(cells - n)
}

/** Rows padded into columns two spaces apart; `right` lists the columns aligned right. */
export const columns = (rows: ReadonlyArray<readonly string[]>, right: readonly number[] = [], indent = '  '): string[] => {
  const w: number[] = []
  for (const r of rows) r.forEach((c, i) => { w[i] = Math.max(w[i] ?? 0, c.length) })
  return rows.map(r => indent + r.map((c, i) => (i === r.length - 1 && !right.includes(i) ? c : right.includes(i) ? c.padStart(w[i]!) : c.padEnd(w[i]!))).join('  ').trimEnd())
}
