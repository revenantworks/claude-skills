// vigil views: pure logic (no $). The lines the /rw-vigil pane draws, the same lines as text where no
// pane draws, and what vigil_read hands Claude. Every view reads the feed; none reads text.
// Layout rules: one header per section in the theme's style, columns aligned, one separator
// glyph, lines kept under about 72 characters. Colour is a tone the pane paints; text stays plain.
import type { AutoMode, TileId } from './board-logic'
import type { BuildSource } from './tiles-logic'
import type { Feed, Health, SkillRow } from './collector-logic'
import { statusText, type Live } from './meters-logic'
import {
  NEUTRAL, bar, columns, headerText, madeFor, orderThemes, resolveVariant, roleChecks,
  type ConsoleBg, type ConsoleInfo, type RoleCheck, type Theme, type ThemeEntry, type Tone,
} from './theme-logic'

/** One drawn line: a tone the active theme paints, or (the theme picker) the exact colour it shows. */
export type Line = { text: string; tone?: Tone; color?: string; buttons?: readonly LineButton[] }

/** What a pane press does. Text output ignores it. */
export type Press =
  | { kind: 'view'; view: View }
  /** A tile's three controls (collapse, pin, move) and its open. */
  | { kind: 'tile'; op: 'collapse' | 'pin' | 'up' | 'down' | 'open'; id: TileId }
  /** A suggestion card's buttons, and Undo after Not now. */
  | { kind: 'card'; op: 'do' | 'notnow' | 'never' | 'undo'; id: string }
  /** Your tile's own button: drafts its prompt in chat. */
  | { kind: 'tile-act'; id: TileId }
  /** A theme picked in the pane, or what the console is drawn on. */
  | { kind: 'theme'; name: string }
  | { kind: 'background'; bg: ConsoleBg | 'auto' }
  /** One of the three switches: the shared switch command it stands for. */
  | { kind: 'switch'; command: string }
  /** A spend-mode toggle: may pacewright enter this mode by itself. */
  | { kind: 'auto'; mode: AutoMode; on: boolean }
  /** The tile builder: pick a source, or hand Claude the read-only scan of it. */
  | { kind: 'build'; op: 'pick' | 'scan'; source: BuildSource }
  /** Rotate it on the Privacy tile: shroud drafts a keywarden rotation in chat. */
  | { kind: 'rotate' }
export type LineButton = { label: string; press: Press }

export const VIEWS = ['board', 'detail', 'cards', 'settings', 'tiles', 'overview', 'skills', 'skills-all', 'dupes', 'meters', 'health', 'tasks', 'context', 'theme'] as const
export type View = (typeof VIEWS)[number]

/** The pane's view bar: the views worth a button. The rest stay typed (/rw-vigil help). */
const NAV: readonly (readonly [View, string])[][] = [
  [['board', 'Board'], ['cards', 'Inbox'], ['skills', 'Skills'], ['tasks', 'Tasks'], ['health', 'Health'], ['tiles', 'Tiles'], ['theme', 'Theme'], ['settings', 'Settings']],
]
/** The view a pane view belongs to on the bar: skills' all and dupes lists sit under Skills. */
const navOf = (v: View): View => (v === 'skills-all' || v === 'dupes' ? 'skills' : v === 'detail' ? 'board' : v)

/** The pane's view bar: a press opens that view in place, so no /rw-vigil <verb> is typed. The open view is bracketed. */
export const navLines = (current: View): Line[] => {
  const on = navOf(current)
  return NAV.map((row, i) => ({
    text: i === 0 ? '  view' : '      ',
    tone: 'dim' as const,
    buttons: row.map(([view, label]) => ({ label: view === on ? `[${label}]` : label, press: { kind: 'view' as const, view } })),
  }))
}

/** `/rw-vigil <verb> <rest>`: the verb lower-cased, the rest as typed. */
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
const footer = (t: Theme, verbs: readonly string[]): Line => ({ text: `  /rw-vigil ${verbs.join(t.glyphs.sep)}`, tone: 'dim' })
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
  // Only the latest listing counts: a name seen only in older records (a skill renamed by its source,
  // such as a synced skill that gained its anthropic-skills: prefix) is not a second loaded copy.
  for (const r of rows.filter(x => x.listed)) by.set(baseName(r.name), [...(by.get(baseName(r.name)) ?? []), r.name])
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
export const overviewLines = (args: { live: Live | null; feed: Feed; now: number; tasksLine: string | null; theme?: Theme }): Line[] => {
  const t = args.theme ?? NEUTRAL
  const { feed } = args
  const out: Line[] = [head(t, 'vigil'), { text: `  ${statusText(args.live, args.now, t.glyphs.sep)}`, tone: 'bold' }]
  out.push({ text: `  week  ${[plural(feed.sessions7, 'session'), `${k(feed.tokens7)} tokens`, usd(feed.cost7)].join(t.glyphs.sep)}`, tone: 'dim' })
  if (!feed.recording) out.push({ text: '  Counts stay in this session. /rw-vigil records on keeps them.', tone: 'dim' })
  if (args.tasksLine) out.push({ text: `  ${args.tasksLine}`, tone: 'accent' })
  const top = feed.skills.filter(s => s.fires30 > 0).slice(0, 5)
  out.push(blank, head(t, 'Skills, last 30 days'))
  if (top.length === 0) out.push({ text: '  No skill has fired yet.', tone: 'dim' })
  else out.push(...skillTable(top))
  out.push(blank, head(t, 'Health'), ...pluginLines(t, feed.health), { text: `  ${healthSummary(feed.health, t)}`, tone: 'dim' })
  if (feed.suggestionsNew > 0) out.push(blank, { text: `  ${t.glyphs.warn} ${plural(feed.suggestionsNew, 'new suggestion')}: /rw-vigil suggest`, tone: 'warning' })
  out.push(blank, footer(t, ['skills', 'tasks', 'health', 'suggest', 'theme', 'help']))
  return out
}

/**
 * `/rw-vigil skills`: the skills that fired (or failed) in 30 days, grouped by source, then one line for
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
  if (!opts.all && quiet) notes.push({ text: `  ${quiet} enabled, never fired${t.glyphs.sep}/rw-vigil skills all`, tone: 'dim' })
  const dupes = findDupes(feed.skills, sources)
  if (dupes.length) notes.push({ text: `  ${t.glyphs.warn} ${plural(dupes.length, 'skill')} loaded twice (${[...new Set(dupes.flatMap(d => d.sources))].join(' + ')}): /rw-vigil skills dupes`, tone: 'warning' })
  if (shown.length) notes.push({ text: '  misr: another skill fired 30 s to 2 min later, or its edit was reverted.', tone: 'dim' }, { text: "  tok 7d: all tokens of the turns it loaded in, not the skill's own size.", tone: 'dim' })
  if (notes.length) out.push(blank, ...notes)
  return out
}

/** `/rw-vigil skills dupes`: each skill loaded twice, with the sources it comes from. */
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

/** Health past the mod rows the overview already shows: drift, gatewarden. */
export const healthSummary = (h: Health, theme: Theme = NEUTRAL): string => {
  const drift = h.drift.filter(d => d.state === 'differs').length
  const gw = h.gatewarden ? `gatewarden ${plural(h.gatewarden.total7, 'event')} in 7 days` : 'no gatewarden log'
  return [`${plural(drift, 'hook')} drifted`, gw].join(theme.glyphs.sep)
}

/**
 * The duplicate-skills health item: one plain sentence and its fix, wrapped inside 80 columns.
 * `dupes` is the pairs (their sources name the fix) or, where only a count is known, the count.
 */
export const dupesHealth = (t: Theme, dupes: number | readonly Dupe[]): Line[] => {
  const n = typeof dupes === 'number' ? dupes : dupes.length
  if (!n) return []
  const sources = typeof dupes === 'number' ? [] : [...new Set(dupes.flatMap(d => d.sources))].sort((a, b) => SOURCES.indexOf(a) - SOURCES.indexOf(b))
  const fix = sources.includes('claude.ai synced')
    ? 'Fix: turn off claude.ai skill sync, or delete the synced copies.'
    : 'Fix: delete one copy of each (/rw-vigil skills dupes lists them).'
  const what = `${plural(n, 'skill')} ${n === 1 ? 'loads' : 'load'} twice${sources.length ? ` (${sources.join(' + ')})` : ''}.`
  return [{ text: `  ${t.glyphs.warn} ${what}`, tone: 'warning' }, { text: `    ${fix}`, tone: 'warning' }]
}

export const healthLines = (h: Health, theme: Theme = NEUTRAL, dupes: number | readonly Dupe[] = 0): Line[] => {
  const t = theme
  const out: Line[] = [head(t, 'Health'), { text: '  Mods loaded in this session', tone: 'bold' }, ...pluginLines(t, h)]
  const dh = dupesHealth(t, dupes)
  if (dh.length) out.push(blank, ...dh)
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
/**
 * The picker: each theme drawn in its own accent, with a button to use it, then the console's
 * background. A press applies it at once; typing the name does the same.
 */
export const themeLines = (themes: Record<string, ThemeEntry>, active: string, theme: Theme, errors: readonly string[], con?: ConsoleInfo, folder = '~/.claude/revenantworks/themes'): Line[] => {
  const t = theme
  const here = con ?? { bg: madeFor(theme.background), sure: false, source: '' }
  const names = orderThemes(Object.keys(themes))
  const rows = columns(names.map(n => {
    const e = themes[n]!
    return [`${n === active ? t.glyphs.on : t.glyphs.off} ${n}`, fit([e.theme.description, e.source === 'user' ? 'yours' : ''].filter(Boolean).join(t.glyphs.sep), MAX_COLS - 24)]
  }))
  const out: Line[] = [head(t, 'Themes')]
  names.forEach((n, i) => {
    const line: Line = { text: rows[i]!, color: resolveVariant(themes[n]!.theme, here.bg).theme.colors.accent }
    out.push(n === active ? line : { ...line, buttons: [{ label: 'Use', press: { kind: 'theme', name: n } }] })
  })
  const bgs = (['dark', 'light', 'auto'] as const).map(bg => ({ label: bg, press: { kind: 'background' as const, bg } }))
  out.push(blank, { text: `  This console ${here.sure ? 'is' : 'looks'} ${here.bg}:`, buttons: bgs })
  const weak = roleChecks(theme.colors, here.bg).filter(c => c.grade === 'fail' || c.grade === 'borderline')
  if (weak.length) out.push({ text: `  ${t.glyphs.warn} Hard to read on this console:`, tone: 'warning' }, ...weakLines(weak))
  if (errors.length) out.push(blank, { text: `  ${t.glyphs.bad} Theme files skipped`, tone: 'error' }, ...errors.map(e => ({ text: `    ${fit(e, MAX_COLS - 4)}`, tone: 'error' as const })))
  out.push(blank, { text: '  /rw-vigil theme <name> applies one; theme background dark|light|auto.', tone: 'dim' }, { text: `  Your own: a JSON file in ${fit(folder, MAX_COLS - 26)}.`, tone: 'dim' })
  return out
}

const ratio = (c: RoleCheck): string => (c.ratio === null ? '' : `${c.ratio.toFixed(2)}:1`)

/** The roles under or near their floor, one aligned row each. */
const weakLines = (weak: readonly RoleCheck[]): Line[] => columns(weak.map(c => [c.role, c.color, ratio(c), c.grade === 'fail' ? `under ${c.floor}:1` : `just over ${c.floor}:1`]), [2], '    ')
  .map((text, i) => ({ text, tone: weak[i]!.grade === 'fail' ? ('error' as const) : ('warning' as const) }))

/** `/rw-vigil theme <name>` after it is saved: one line, what wins over it, the undo. */
export const themeApplied = (p: Theme, con: ConsoleInfo, envName: string | null): Line[] => {
  const r = resolveVariant(p, con.bg)
  const what = r.variant ? `${r.variant} variant` : variantsText(p) === 'follows yours' ? 'your theme colours' : `one palette, made for ${madeFor(p.background)} consoles`
  const out: Line[] = [{ text: `Applied: ${p.name} (${what}; this console ${con.sure ? 'is' : 'looks'} ${con.bg}).`, tone: 'ok' }]
  if (envName) out.push({ text: `VIGIL_THEME=${envName} is set and wins over this choice until you unset it.`, tone: 'warning' })
  return [...out, { text: 'Undo: /rw-vigil theme neutral', tone: 'dim' }]
}

export const HELP: readonly string[] = columns([
  ['/rw-vigil', 'the board: usage, context, inbox, spend mode, skills, health'],
  ['/rw-vigil tile <name> open|up|down|pin|collapse', 'one tile; layout reset puts them back'],
  ['/rw-vigil suggest', 'what is worth doing, at most five cards'],
  ['/rw-vigil suggest accept|dismiss|snooze <n>', 'take, drop or hide one'],
  ['/rw-vigil skills [all | dupes]', 'fired skills; all; loaded twice'],
  ['/rw-vigil meters | context | tasks | health', 'one view'],
  ['/rw-vigil theme [<name> | background <b>]', 'list or apply; dark, light, auto'],
  ['/rw-vigil tiles [build <source>]', 'your own tiles; Claude proposes some'],
  ['/rw-vigil link <clones> <folder> | off', 'keep your tiles and themes in a private folder'],
  ['/rw-vigil spend auto <mode> on|off', 'may pacewright enter pace, overnight, reset-eve itself'],
  ['/rw-vigil settings | switches | on|off <name> | off', 'features; bare off = kill switch'],
  ['/rw-vigil records on|off', 'keep counts across sessions'],
  ['/rw-vigil doctor | purge', 'check the install; delete counts'],
  ['/rw | /rw-<skill> [what you want]', 'list or run a Revenantworks skill'],
], [], '')

/** What vigil_read hands Claude: one view as plain text, so a surface that cannot draw still reads it. */
export const linesText = (lines: readonly Line[]): string => lines.map(l => l.text).join('\n')
