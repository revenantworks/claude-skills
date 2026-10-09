// dash views: pure logic (no $). The lines the /dash pane draws, the same lines as text where no
// pane draws, and what dash_read hands Claude. Every view reads the feed; none reads text.
// Layout rules: one header per section in the theme's style, columns aligned, one separator
// glyph, lines kept under about 72 characters. Colour is a tone the pane paints; text stays plain.
import type { Feed, Health, SkillRow } from './collector-logic'
import { statusText, type Live } from './meters-logic'
import { listed, type Suggestion } from './suggest-logic'
import {
  BACKGROUNDS, NEUTRAL, bar, columns, consoleVerdict, headerText, madeFor, resolveVariant, roleChecks, themeVerdict,
  type ConsoleBg, type ConsoleInfo, type ConsoleVerdict, type Role, type RoleCheck, type Theme, type ThemeEntry, type Tone,
} from './theme-logic'

/** One drawn line: a tone the active theme paints, or (a theme preview) the exact colour it shows. */
export type Line = { text: string; tone?: Tone; color?: string }

export const VIEWS = ['overview', 'skills', 'skills-all', 'dupes', 'meters', 'health', 'tasks', 'suggest', 'context', 'gpu', 'palette', 'godot', 'prs', 'theme'] as const
export type View = (typeof VIEWS)[number]

/** `/dash <verb> <rest>`: the verb lower-cased, the rest as typed. */
export const parseDashArgs = (args: string): { verb: string; rest: string } => {
  const t = args.trim()
  const m = /^(\S+)\s*([\s\S]*)$/.exec(t)
  return m ? { verb: m[1]!.toLowerCase(), rest: m[2]!.trim() } : { verb: '', rest: '' }
}

export const k = (n: number): string => (n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 10_000 ? `${Math.round(n / 1000)}k` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(Math.round(n)))
const usd = (n: number | null): string => (n === null ? '-' : `$${n.toFixed(2)}`)
const plural = (n: number, one: string, many = `${one}s`): string => `${n} ${n === 1 ? one : many}`

export const head = (t: Theme, title: string): Line => ({ text: headerText(t, title), tone: 'head' })
const blank: Line = { text: '' }
const footer = (t: Theme, verbs: readonly string[]): Line => ({ text: `  /dash ${verbs.join(t.glyphs.sep)}`, tone: 'dim' })
/** A skill's name without its source prefix (`anthropic-skills:`, `<plugin>:`) or pack prefix (`revenantworks-<pack>-`). */
export const baseName = (name: string): string => name.replace(/^[^:]+:/, '').replace(/^revenantworks-[a-z]+-/, '')
/** The name a table shows: the pack prefix and the synced prefix go (the group names the source); a plugin keeps its own. */
const short = (name: string): string => name.replace(/^anthropic-skills:/, '').replace(/^revenantworks-[a-z]+-/, '').replace(/:revenantworks-[a-z]+-/, ':')

export const SOURCES = ['local', 'plugin', 'claude.ai synced', 'built-in', 'mcp'] as const
export type SkillSource = (typeof SOURCES)[number]
/** Where a skill comes from: the engine's word from the session's listing when there is one, else the name's prefix. */
export const skillSource = (name: string, hint?: string): SkillSource => {
  const h = (hint ?? '').toLowerCase()
  if (h === 'syncedskills' || h === 'synced') return 'claude.ai synced'
  if (h === 'plugin') return 'plugin'
  if (h === 'built-in' || h === 'builtin' || h === 'bundled') return 'built-in'
  if (h === 'mcp') return 'mcp'
  if (h.endsWith('settings')) return 'local'
  if (name.startsWith('anthropic-skills:')) return 'claude.ai synced'
  return name.includes(':') ? 'plugin' : 'local'
}

export type Dupe = { base: string; names: string[]; sources: SkillSource[] }
/** Skills loaded under two names or from two sources: the same base name more than once. */
export const findDupes = (rows: readonly SkillRow[], sources: Readonly<Record<string, string>> = {}): Dupe[] => {
  const by = new Map<string, string[]>()
  for (const r of rows) by.set(baseName(r.name), [...(by.get(baseName(r.name)) ?? []), r.name])
  const order = (s: SkillSource) => SOURCES.indexOf(s)
  return [...by.entries()].filter(([, names]) => new Set(names).size > 1)
    .map(([base, names]) => ({ base, names: [...new Set(names)], sources: [...new Set(names.map(n => skillSource(n, sources[n])))].sort((a, b) => order(a) - order(b)) }))
    .sort((a, b) => a.base.localeCompare(b.base))
}

const SKILL_HEAD = ['skill', 'fires', 'slash', 'auto', 'fail', 'misr', 'tok 7d', '$ 7d'] as const
const NAME_W = 24
const dot = '·'
const skillCells = (s: SkillRow): string[] => {
  const name = fit(short(s.name), NAME_W)
  if (s.fires30 === 0 && s.failures30 + s.misroutes30 === 0) return [name, dot]
  return [name, String(s.fires30), String(s.slash30), String(s.auto30), String(s.failures30), String(s.misroutes30), s.tokens7 ? k(s.tokens7) : dot, s.cost7 === null ? dot : usd(s.cost7)]
}
const skillTone = (s: SkillRow): Tone | undefined => (s.failures30 + s.misroutes30 > 0 ? 'warning' : s.fires30 === 0 ? 'dim' : undefined)
const RIGHT = [1, 2, 3, 4, 5, 6, 7]

/** A skills table: a dim header row, then one row per skill; a row with failures or misroutes is a warning. */
export const skillTable = (rows: readonly SkillRow[]): Line[] => {
  const text = columns([[...SKILL_HEAD], ...rows.map(skillCells)], RIGHT)
  return text.map((t, i) => (i === 0 ? { text: t, tone: 'dim' as const } : { text: t, ...(skillTone(rows[i - 1]!) ? { tone: skillTone(rows[i - 1]!) } : {}) }))
}

/** The same table split under one label per source, columns aligned across the groups. */
const groupedTable = (rows: readonly SkillRow[], sources: Readonly<Record<string, string>>): Line[] => {
  const groups = SOURCES.map(src => ({ src, rows: rows.filter(r => skillSource(r.name, sources[r.name]) === src) })).filter(g => g.rows.length)
  const flat = groups.flatMap(g => g.rows)
  const text = columns([[...SKILL_HEAD], ...flat.map(skillCells)], RIGHT, '    ')
  const out: Line[] = [{ text: text[0]!, tone: 'dim' }]
  let i = 1
  for (const g of groups) {
    out.push({ text: `  ${g.src}`, tone: 'bold' })
    for (const r of g.rows) {
      const tone = skillTone(r)
      out.push({ text: text[i++]!, ...(tone ? { tone } : {}) })
    }
  }
  return out
}

const pluginLines = (t: Theme, h: Health): Line[] => {
  const names = Object.keys(h.plugins)
  if (names.length === 0) return [{ text: '  No heartbeat yet.', tone: 'dim' }]
  const rows = names.map(n => {
    const p = h.plugins[n]!
    return [p.loaded ? t.glyphs.ok : t.glyphs.warn, n, p.loaded ? `loaded${p.version ? ` ${p.version}` : ''}` : 'not loaded in this session', p.caught ? `${plural(p.caught, 'hook failure')} caught` : '']
  })
  return columns(rows).map((text, i) => {
    const p = h.plugins[names[i]!]!
    return { text, tone: p.loaded && !p.caught ? ('ok' as const) : ('warning' as const) }
  })
}

/** The overview: meters, the week's totals, the busiest skills, health, open suggestions. */
export const overviewLines = (args: { live: Live | null; feed: Feed; now: number; tasksLine: string | null; panels: string[]; theme?: Theme }): Line[] => {
  const t = args.theme ?? NEUTRAL
  const { feed } = args
  const out: Line[] = [head(t, 'dash'), { text: `  ${statusText(args.live, args.now, t.glyphs.sep)}`, tone: 'bold' }]
  out.push({ text: `  week  ${[plural(feed.sessions7, 'session'), `${k(feed.tokens7)} tokens`, usd(feed.cost7)].join(t.glyphs.sep)}`, tone: 'dim' })
  if (!feed.recording) out.push({ text: '  Counts stay in this session. /dash records on keeps them.', tone: 'dim' })
  if (args.tasksLine) out.push({ text: `  ${args.tasksLine}`, tone: 'accent' })
  const top = feed.skills.filter(s => s.fires30 > 0).slice(0, 5)
  out.push(blank, head(t, 'Skills, last 30 days'))
  if (top.length === 0) out.push({ text: '  No skill has fired yet.', tone: 'dim' })
  else out.push(...skillTable(top))
  out.push(blank, head(t, 'Health'), ...pluginLines(t, feed.health), { text: `  ${healthSummary(feed.health, t)}`, tone: 'dim' })
  if (feed.suggestionsNew > 0) out.push(blank, { text: `  ${t.glyphs.warn} ${plural(feed.suggestionsNew, 'new suggestion')}: /dash suggest`, tone: 'warning' })
  if (args.panels.length) out.push(blank, head(t, 'Panels'), ...args.panels.map(p => ({ text: `  ${p}`, tone: 'dim' as const })))
  out.push(blank, footer(t, ['skills', 'meters', 'health', 'tasks', 'suggest', 'theme', 'help']))
  return out
}

/**
 * `/dash skills`: the skills that fired (or failed) in 30 days, grouped by source, then one line for
 * the rest and one for duplicates. `all` lists every skill; `sources` is the session listing's
 * source per name (the counts file keeps names only).
 */
export const skillsLines = (feed: Feed, theme: Theme = NEUTRAL, opts: { all?: boolean; sources?: Readonly<Record<string, string>> } = {}): Line[] => {
  const t = theme
  const sources = opts.sources ?? {}
  const active = (s: SkillRow) => s.fires30 > 0 || s.failures30 + s.misroutes30 > 0
  const out: Line[] = [head(t, opts.all ? 'Skills, all' : 'Skills, last 30 days')]
  out.push({ text: `  ${feed.skills.filter(s => s.listed).length} enabled${t.glyphs.sep}${feed.skills.filter(s => s.fires30 > 0).length} fired in the last 30 days`, tone: 'bold' })
  const shown = [...feed.skills].filter(s => opts.all || active(s)).sort((a, b) => b.fires30 - a.fires30 || a.name.localeCompare(b.name))
  if (feed.skills.length === 0) out.push(blank, { text: '  No skills listed or fired yet.', tone: 'dim' })
  else if (shown.length === 0) out.push(blank, { text: '  No skill fired in the last 30 days.', tone: 'dim' })
  else out.push(blank, ...groupedTable(shown, sources))
  const quiet = feed.skills.filter(s => s.listed && !active(s)).length
  const notes: Line[] = []
  if (!opts.all && quiet) notes.push({ text: `  ${quiet} enabled, never fired${t.glyphs.sep}/dash skills all`, tone: 'dim' })
  const dupes = findDupes(feed.skills, sources)
  if (dupes.length) notes.push({ text: `  ${t.glyphs.warn} ${plural(dupes.length, 'skill')} loaded twice (${[...new Set(dupes.flatMap(d => d.sources))].join(' + ')}): /dash skills dupes`, tone: 'warning' })
  if (shown.length) notes.push({ text: '  misr: another skill fired within 2 minutes, or its edit was reverted.', tone: 'dim' })
  if (notes.length) out.push(blank, ...notes)
  return out
}

/** `/dash skills dupes`: each skill loaded twice, with the sources it comes from. */
export const dupesLines = (feed: Feed, theme: Theme = NEUTRAL, sources: Readonly<Record<string, string>> = {}): Line[] => {
  const t = theme
  const dupes = findDupes(feed.skills, sources)
  const out: Line[] = [head(t, 'Skills loaded twice')]
  if (dupes.length === 0) return [...out, { text: '  No skill is loaded twice.', tone: 'ok' }]
  out.push({ text: '  Each copy takes listing room and splits the fire counts.', tone: 'dim' }, blank)
  const rows = columns([['skill', 'sources'], ...dupes.map(d => [fit(d.base, NAME_W), d.sources.join(', ')])])
  out.push({ text: rows[0]!, tone: 'dim' })
  dupes.forEach((d, i) => out.push({ text: rows[i + 1]!, tone: 'warning' }, ...d.names.map(n => ({ text: `      ${fit(n, MAX_COLS - 6)}`, tone: 'dim' as const }))))
  out.push(blank, { text: '  Keep one copy: remove the local folder or the synced skill.', tone: 'dim' })
  return out
}

const pct = (n: number): string => `${Math.round(n)}%`.padStart(4)
const level = (n: number): Tone => (n >= 90 ? 'error' : n >= 75 ? 'warning' : 'ok')

export const metersLines = (live: Live | null, feed: Feed, now: number, theme: Theme = NEUTRAL): Line[] => {
  const t = theme
  const out: Line[] = [head(t, 'Meters'), { text: `  ${statusText(live, now, t.glyphs.sep)}`, tone: 'dim' }, blank]
  const row = (label: string, value: string, tone?: Tone): Line => ({ text: `  ${label.padEnd(9)}${value}`, ...(tone ? { tone } : {}) })
  if (live?.five != null) out.push(row('5-hour', `${pct(live.five)}  ${bar(t, live.five)}`, level(live.five)))
  if (live?.week != null) out.push(row('weekly', `${pct(live.week)}  ${bar(t, live.week)}${live.weekResetMs !== null ? `  resets ${new Date(live.weekResetMs).toISOString().slice(0, 16).replace('T', ' ')} UTC` : ''}`, level(live.week)))
  if (live?.ctx != null) out.push(row('context', `${pct(live.ctx)}  ${bar(t, live.ctx)}`, live.ctx >= 80 ? 'error' : live.ctx >= 60 ? 'warning' : 'ok'))
  if (live?.cacheHit != null) out.push(row('cache', `${pct(live.cacheHit * 100)}  of the last turn's input`))
  if (live?.costUsd != null) out.push(row('session', usd(live.costUsd)))
  if (out.length === 3) out.push({ text: '  No meter reading yet: it arrives with the first answer.', tone: 'dim' })
  out.push(blank, { text: `  Context passed 80% on ${plural(feed.ctx80Days7, 'day')} this week.`, tone: 'dim' })
  return out
}

/** Health past the mod rows the overview already shows: drift, gatewarden, pins. */
export const healthSummary = (h: Health, theme: Theme = NEUTRAL): string => {
  const drift = h.drift.filter(d => d.state === 'differs').length
  const gw = h.gatewarden ? `gatewarden ${plural(h.gatewarden.total7, 'event')} in 7 days` : 'no gatewarden log'
  return [`${plural(drift, 'hook')} drifted`, gw, ...(h.pinsChanged ? [`${plural(h.pinsChanged, 'instruction file')} changed`] : [])].join(theme.glyphs.sep)
}

export const healthLines = (h: Health, theme: Theme = NEUTRAL, dupes = 0): Line[] => {
  const t = theme
  const out: Line[] = [head(t, 'Health'), { text: '  Mods loaded in this session', tone: 'bold' }, ...pluginLines(t, h)]
  if (dupes) out.push(blank, { text: `  ${t.glyphs.warn} ${plural(dupes, 'skill')} loaded twice: /dash skills dupes`, tone: 'warning' })
  out.push(blank, { text: '  Hooks: this repo against ~/.claude/hooks', tone: 'bold' })
  if (h.drift.length === 0) out.push({ text: '  Nothing to compare here.', tone: 'dim' })
  else {
    const rows = columns(h.drift.map(d => [d.state === 'differs' ? t.glyphs.warn : d.state === 'same' ? t.glyphs.ok : t.glyphs.off, d.hook, d.state]))
    out.push(...rows.map((text, i) => ({ text, tone: h.drift[i]!.state === 'differs' ? ('warning' as const) : h.drift[i]!.state === 'same' ? ('ok' as const) : ('dim' as const) })))
  }
  out.push(blank, { text: '  gatewarden, last 7 days', tone: 'bold' })
  const g = h.gatewarden
  if (!g) out.push({ text: '  No event log (~/.claude/gatewarden/events.jsonl).', tone: 'dim' })
  else {
    const list = (o: Record<string, number>) => Object.entries(o).map(([m, n]) => `${m} ${n}`).join(', ') || 'none'
    const rows = [['events', String(g.total7)], ['modes', list(g.byMode)], ['outcomes', list(g.byOutcome)], ...(g.topRules.length ? [['busiest', g.topRules.map(r => `${r.rule} ${r.n}`).join(', ')]] : [])]
    out.push(...columns(rows).map(text => ({ text })))
  }
  if (h.pinsChanged) out.push(blank, { text: `  ${t.glyphs.warn} ${plural(h.pinsChanged, 'instruction file')} changed since last loaded`, tone: 'warning' })
  return out
}

export const suggestLines = (rows: readonly Suggestion[], theme: Theme = NEUTRAL): Line[] => {
  const t = theme
  const out: Line[] = [head(t, 'Suggestions'), { text: '  Never built. Accepting gives you a line for NEXT.md.', tone: 'dim' }, blank]
  const ordered = listed(rows)
  if (ordered.length === 0) out.push({ text: '  None yet. They come from what the collector counts (/dash records on).', tone: 'dim' })
  ordered.forEach((r, i) => {
    out.push({ text: fit(`  ${String(i + 1).padStart(2)}. [${r.state}] ${r.title}`, MAX_COLS), tone: r.state === 'new' ? 'warning' : r.state === 'shown' ? 'accent' : r.state === 'accepted' ? 'ok' : 'dim' })
    out.push({ text: fit(`      why: ${r.evidence}`, MAX_COLS), tone: 'dim' })
  })
  out.push(blank, { text: '  /dash suggest accept|dismiss|snooze <n>', tone: 'dim' })
  return out
}

/** A panel's own lines under its header, indented. */
export const panelLines = (t: Theme, title: string, lines: readonly string[]): Line[] => [head(t, title), ...lines.map(text => ({ text: text.startsWith('  ') ? text : `  ${text}` }))]

/** The widest a text line may run: an 80-column console with a margin. */
export const MAX_COLS = 78
const fit = (s: string, n: number): string => (s.length <= n ? s : `${s.slice(0, Math.max(1, n - 1))}…`)

/** What a theme carries, in two words. */
export const variantsText = (th: Theme): string => {
  const v = th.variants
  if (v?.dark && v?.light) return 'dark + light'
  if (v?.dark || v?.light) return `${v.dark ? 'dark' : 'light'} only`
  if (Object.values(th.colors).every(c => !c.startsWith('#'))) return 'follows yours'
  return `made for ${madeFor(th.background)}`
}

/** Which palette this console gets, as a phrase: "the light variant", "its one palette". */
const getsText = (th: Theme, con: ConsoleInfo): string => {
  const r = resolveVariant(th, con.bg)
  if (r.variant) return `the ${r.variant} variant`
  if (variantsText(th) === 'follows yours') return 'your Claude Code theme colours'
  return `its one palette (made for ${madeFor(th.background)})`
}
const consoleLines = (th: Theme, con: ConsoleInfo): Line[] => con.sure
  ? [{ text: `  This console is ${con.bg}: it gets ${getsText(th, con)}.` }, { text: `  (from ${con.source})`, tone: 'dim' }]
  : [{ text: `  This console looks ${con.bg}: it gets ${getsText(th, con)}.` }, { text: '  (A guess: set DASH_THEME_BACKGROUND=light or dark to say.)', tone: 'dim' }]

export const themeLines = (themes: Record<string, ThemeEntry>, active: string, theme: Theme, errors: readonly string[], con?: ConsoleInfo): Line[] => {
  const t = theme
  const here = con ?? { bg: madeFor(theme.background), sure: false, source: '' }
  const names = Object.keys(themes).sort((a, b) => (a === 'neutral' ? -1 : b === 'neutral' ? 1 : a.localeCompare(b)))
  // Each theme on two lines: the mark, name and source; then its description and what it carries.
  const rows = columns(names.map(n => {
    const e = themes[n]!
    return [`${n === active ? t.glyphs.on : t.glyphs.off} ${n}`, e.source === 'user' ? (e.overrides ? 'yours, over bundled' : 'yours') : n === 'neutral' ? 'bundled, default' : 'bundled']
  }))
  const out: Line[] = [head(t, 'Themes')]
  names.forEach((n, i) => {
    const e = themes[n]!
    out.push(
      { text: rows[i]!, tone: n === active ? 'accent' : undefined },
      { text: `      ${fit([e.theme.description, variantsText(e.theme)].filter(Boolean).join(t.glyphs.sep), MAX_COLS - 6)}`, tone: 'dim' },
    )
  })
  const inUse = resolveVariant(themes[active]?.theme ?? theme, here.bg)
  out.push(blank, { text: `  In use: ${active}, ${inUse.variant ? `${inUse.variant} variant` : variantsText(inUse.theme) === 'follows yours' ? 'your theme colours' : 'one palette'} (this console ${here.sure ? 'is' : 'looks'} ${here.bg}).` })
  const weak = roleChecks(theme.colors, here.bg).filter(c => c.grade === 'fail' || c.grade === 'borderline')
  if (weak.length) out.push({ text: `  ${t.glyphs.warn} On this console:`, tone: 'warning' }, ...weakLines(weak))
  if (errors.length) out.push(blank, { text: `  ${t.glyphs.bad} Theme files skipped`, tone: 'error' }, ...errors.map(e => ({ text: `    ${fit(e, MAX_COLS - 4)}`, tone: 'error' as const })))
  const help = columns([
    ['/dash theme <name>', 'apply a theme'],
    ['/dash theme show [name]', 'preview: contrast and a verdict; changes nothing'],
    ['/dash theme new', 'make your own: answers, a file or a design system'],
  ])
  out.push(blank, ...help.map(text => ({ text, tone: 'dim' as const })))
  return out
}

const JOBS: Record<Role, string> = { accent: 'headers, active row', ok: 'loaded, passed', warn: 'drifted, a look', bad: 'failed, over a line', dim: 'notes and hints', rule: 'dividers' }
const ratio = (c: RoleCheck): string => (c.ratio === null ? '' : `${c.ratio.toFixed(2)}:1`)
const TONE: Record<Role, Tone> = { accent: 'accent', ok: 'ok', warn: 'warning', bad: 'error', dim: 'dim', rule: 'rule' }

/** The roles under or near their floor, one aligned row each. */
const weakLines = (weak: readonly RoleCheck[]): Line[] => columns(weak.map(c => [c.role, c.color, ratio(c), c.grade === 'fail' ? `under ${c.floor}:1` : `just over ${c.floor}:1`]), [2], '    ')
  .map((text, i) => ({ text, tone: weak[i]!.grade === 'fail' ? ('error' as const) : ('warning' as const) }))

/** One palette's table: every role as a swatch, its hex, its contrast on the console, its floor and grade. */
const paletteTable = (t: Theme, colors: Record<Role, string>, bg: ConsoleBg): Line[] => {
  const checks = roleChecks(colors, bg)
  const head1 = ['role', 'colour', 'ratio', 'floor', 'check', 'job']
  const rows = checks.map(c => [c.role, `${c.ratio === null ? t.glyphs.off.repeat(2) : t.glyphs.full.repeat(2)} ${c.color}`, ratio(c), String(c.floor), c.grade, JOBS[c.role]])
  return columns([head1, ...rows], [2, 3], '    ').map((text, i) => {
    if (i === 0) return { text, tone: 'dim' as const }
    const c = checks[i - 1]!
    return HEXCOLOR.test(c.color) ? { text, color: c.color } : { text, tone: TONE[c.role] }
  })
}
const HEXCOLOR = /^#[0-9a-fA-F]{3,6}$/

/** `/dash theme show [name]`: a preview that changes nothing. `chrome` is the active theme, which draws the headers. */
export const themePreview = (p: Theme, chrome: Theme, con: ConsoleInfo): Line[] => {
  const t = chrome
  const v = themeVerdict(p)
  const out: Line[] = [head(t, `Theme ${p.name}`), { text: `  ${fit(p.description || 'No description.', MAX_COLS - 2)}`, tone: 'dim' }]
  const kinds = variantsText(p)
  out.push({ text: `  ${kinds === 'dark + light' ? 'Two variants, dark and light.' : kinds === 'follows yours' ? 'Every colour is a key of your Claude Code theme.' : kinds.endsWith('only') ? `One variant: ${kinds}.` : `One palette, made for ${madeFor(p.background)} consoles.`}` })
  out.push(...consoleLines(p, con))
  const sections: Array<[string, Record<Role, string>, ConsoleBg]> = p.variants
    ? (['dark', 'light'] as const).filter(b => p.variants![b]).map(b => [`${b === 'dark' ? 'Dark' : 'Light'} variant, on a ${b} console (${BACKGROUNDS[b]})`, p.variants![b]!.colors, b])
    : [[`Palette, on a ${madeFor(p.background)} console (${BACKGROUNDS[madeFor(p.background)]})`, p.colors, madeFor(p.background)]]
  for (const [title, colors, bg] of sections) out.push(blank, { text: `  ${title}`, tone: 'bold' }, ...paletteTable(t, colors, bg))
  out.push(blank, { text: `  glyphs  ${[p.glyphs.ok, p.glyphs.warn, p.glyphs.bad, p.glyphs.on, p.glyphs.off, p.glyphs.mark].join(' ')}   ${bar(p, 60)}   header: ${p.header}`, tone: 'dim' })
  const verdictRow = (label: string, cv: ConsoleVerdict): Line[] => [
    { text: `    ${label.padEnd(15)} ${cv.summary}`, tone: cv.works ? (cv.roles ? 'warning' : 'ok') : 'error' },
    ...(cv.roles ? [{ text: `    ${''.padEnd(15)} ${fit(cv.roles, MAX_COLS - 20)}`, tone: cv.works ? ('warning' as const) : ('error' as const) }] : []),
  ]
  out.push(blank, { text: '  Verdict', tone: 'bold' }, ...verdictRow('Dark consoles', v.dark), ...verdictRow('Light consoles', v.light))
  out.push(blank, { text: '  Recommendation', tone: 'bold' }, { text: `    ${v.recommendation}` })
  out.push(blank, { text: `  Preview only — nothing changed. Apply with /dash theme ${p.name}.`, tone: 'dim' })
  return out
}

/** `/dash theme <name>` after it is saved: one line, the weak roles on this console, the undo. Never the preview. */
export const themeApplied = (p: Theme, chrome: Theme, con: ConsoleInfo, envName: string | null): Line[] => {
  const t = chrome
  const r = resolveVariant(p, con.bg)
  const what = r.variant ? `${r.variant} variant` : variantsText(p) === 'follows yours' ? 'your theme colours' : `one palette, made for ${madeFor(p.background)} consoles`
  const out: Line[] = [{ text: `Applied: ${p.name} (${what} — your console ${con.sure ? 'is' : 'looks'} ${con.bg}).`, tone: 'ok' }]
  const weak = roleChecks(r.theme.colors, con.bg).filter(c => c.grade === 'fail' || c.grade === 'borderline')
  if (weak.length) out.push({ text: `  ${t.glyphs.warn} ${weak.some(c => c.grade === 'fail') ? 'Hard to read' : 'Thin'} on this console:`, tone: 'warning' }, ...weakLines(weak))
  const other: ConsoleBg = con.bg === 'dark' ? 'light' : 'dark'
  const ov = consoleVerdict(p, other)
  if (!ov.works) out.push({ text: `  On ${other} consoles: ${ov.summary}. /dash theme show ${p.name}`, tone: 'dim' })
  if (!con.sure) out.push({ text: '  Console background is a guess: set DASH_THEME_BACKGROUND=light or dark.', tone: 'dim' })
  if (envName) out.push({ text: `  DASH_THEME=${envName} is set and wins over this choice until you unset it.`, tone: 'warning' })
  out.push({ text: 'Undo: /dash theme neutral', tone: 'dim' })
  return out
}

export const HELP: readonly string[] = columns([
  ['/dash', 'meters, skills, health, suggestions'],
  ['/dash skills [all | dupes]', 'fired skills; all; loaded twice'],
  ['/dash meters | health', 'one view'],
  ['/dash tasks | context', 'background tasks; context use'],
  ['/dash suggest', 'the suggestion queue'],
  ['/dash suggest accept|dismiss|snooze <n>', 'act on one suggestion'],
  ['/dash theme [<name> | show | new]', 'list, apply, preview or make'],
  ['/dash theme import <link> [name]', 'a theme from a design system'],
  ['/dash publish', 'a snapshot for a private page'],
  ['/dash gpu | palette [brand] | godot | prs', 'the optional panels'],
  ['/dash switches | on|off <name> | off', 'features; bare off = kill switch'],
  ['/dash records on|off | network on|off', 'keep counts; allow network reads'],
  ['/dash doctor | purge', 'check the install; delete counts'],
], [], '')

/** What dash_read hands Claude: one view as plain text, so a surface that cannot draw still reads it. */
export const linesText = (lines: readonly Line[]): string => lines.map(l => l.text).join('\n')
