// dash views: pure logic (no $). The lines the /dash pane draws, the same lines as text where no
// pane draws, and what dash_read hands Claude. Every view reads the feed; none reads text.
// Layout rules: one header per section in the theme's style, columns aligned, one separator
// glyph, lines kept under about 72 characters. Colour is a tone the pane paints; text stays plain.
import type { Feed, Health, SkillRow } from './collector-logic'
import { statusText, type Live } from './meters-logic'
import { listed, type Suggestion } from './suggest-logic'
import { NEUTRAL, bar, columns, contrastWarnings, headerText, type Theme, type ThemeEntry, type Tone } from './theme-logic'

export type Line = { text: string; tone?: Tone }

export const VIEWS = ['overview', 'skills', 'meters', 'health', 'tasks', 'suggest', 'context', 'gpu', 'palette', 'godot', 'prs', 'theme'] as const
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
const footer = (t: Theme, verbs: readonly string[]): Line => ({ text: `/dash ${verbs.join(t.glyphs.sep)}`, tone: 'dim' })
const short = (name: string): string => name.replace(/^revenantworks-[a-z]+-/, '')

const SKILL_HEAD = ['skill', 'fires', 'slash', 'auto', 'failed', 'misroute', 'tok 7d', 'cost 7d'] as const
const skillCells = (s: SkillRow): string[] => s.fires30 > 0
  ? [short(s.name), String(s.fires30), String(s.slash30), String(s.auto30), String(s.failures30), String(s.misroutes30), s.tokens7 ? k(s.tokens7) : '-', usd(s.cost7)]
  : [short(s.name), '-', '-', '-', '-', '-', '-', '-']

/** A skills table: a dim header row, then one row per skill; a row with failures or misroutes is a warning. */
export const skillTable = (rows: readonly SkillRow[]): Line[] => {
  const text = columns([[...SKILL_HEAD], ...rows.map(skillCells)], [1, 2, 3, 4, 5, 6, 7])
  return text.map((t, i) => {
    if (i === 0) return { text: t, tone: 'dim' as const }
    const s = rows[i - 1]!
    return { text: t, tone: s.failures30 + s.misroutes30 > 0 ? ('warning' as const) : s.fires30 === 0 ? ('dim' as const) : undefined }
  })
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

export const skillsLines = (feed: Feed, theme: Theme = NEUTRAL): Line[] => {
  const t = theme
  const out: Line[] = [head(t, 'Skills')]
  out.push({ text: `  ${feed.skills.filter(s => s.listed).length} enabled${t.glyphs.sep}${feed.skills.filter(s => s.fires30 > 0).length} fired in the last 30 days`, tone: 'bold' })
  if (feed.skills.length === 0) out.push({ text: '  No skills listed or fired yet.', tone: 'dim' })
  else out.push(blank, ...skillTable([...feed.skills].sort((a, b) => b.fires30 - a.fires30 || a.name.localeCompare(b.name))))
  out.push(blank, { text: '  misroute: another skill fired within 2 minutes of an automatic', tone: 'dim' }, { text: '  fire, or an edit it led to was reverted.', tone: 'dim' })
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

export const healthLines = (h: Health, theme: Theme = NEUTRAL): Line[] => {
  const t = theme
  const out: Line[] = [head(t, 'Health'), { text: '  Mods loaded in this session', tone: 'bold' }, ...pluginLines(t, h)]
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
    out.push({ text: `  ${String(i + 1).padStart(2)}. [${r.state}] ${r.title}`, tone: r.state === 'new' ? 'warning' : r.state === 'shown' ? 'accent' : r.state === 'accepted' ? 'ok' : 'dim' })
    out.push({ text: `      why: ${r.evidence}`, tone: 'dim' })
  })
  out.push(blank, { text: '/dash suggest accept|dismiss|snooze <n>', tone: 'dim' })
  return out
}

/** A panel's own lines under its header, indented. */
export const panelLines = (t: Theme, title: string, lines: readonly string[]): Line[] => [head(t, title), ...lines.map(text => ({ text: text.startsWith('  ') ? text : `  ${text}` }))]

export const themeLines = (themes: Record<string, ThemeEntry>, active: string, theme: Theme, errors: readonly string[]): Line[] => {
  const t = theme
  const names = Object.keys(themes).sort((a, b) => (a === 'neutral' ? -1 : b === 'neutral' ? 1 : a.localeCompare(b)))
  const rows = names.map(n => {
    const e = themes[n]!
    return [n === active ? t.glyphs.on : t.glyphs.off, n, e.source === 'user' ? (e.overrides ? 'yours, over bundled' : 'yours') : n === 'neutral' ? 'bundled, default' : 'bundled', e.theme.description.slice(0, 44)]
  })
  const out: Line[] = [head(t, 'Themes'), ...columns(rows).map((text, i) => ({ text, tone: names[i] === active ? ('accent' as const) : undefined }))]
  const warn = contrastWarnings(theme)
  if (warn.length) out.push(blank, { text: `  ${t.glyphs.warn} active theme contrast`, tone: 'warning' }, ...warn.map(w => ({ text: `    ${w}`, tone: 'warning' as const })))
  if (errors.length) out.push(blank, { text: `  ${t.glyphs.bad} theme files skipped`, tone: 'error' }, ...errors.map(e => ({ text: `    ${e}`, tone: 'error' as const })))
  const help = columns([
    ['/dash theme <name>', 'switch to a theme'],
    ['/dash theme new', 'make your own: answers, a file, or a design system'],
    ['/dash theme show [name]', 'every colour role painted'],
  ], [], '')
  out.push(blank, ...help.map(text => ({ text, tone: 'dim' as const })))
  return out
}

/** Every role painted in its own colour, for `/dash theme show`. */
export const themeSample = (t: Theme): Line[] => [
  head(t, `Theme ${t.name}`),
  { text: `  ${t.description}`, tone: 'dim' },
  blank,
  { text: `  accent  ${t.colors.accent.padEnd(12)}headers, the active row`, tone: 'accent' },
  { text: `  ok      ${t.colors.ok.padEnd(12)}${t.glyphs.ok} loaded, passed`, tone: 'ok' },
  { text: `  warn    ${t.colors.warn.padEnd(12)}${t.glyphs.warn} drifted, needs a look`, tone: 'warning' },
  { text: `  bad     ${t.colors.bad.padEnd(12)}${t.glyphs.bad} failed, over the line`, tone: 'error' },
  { text: `  dim     ${t.colors.dim.padEnd(12)}notes and hints`, tone: 'dim' },
  { text: `  rule    ${t.colors.rule.padEnd(12)}${t.glyphs.rule.repeat(20)}`, tone: 'rule' },
  { text: `  glyphs  ${[t.glyphs.ok, t.glyphs.warn, t.glyphs.bad, t.glyphs.on, t.glyphs.off, t.glyphs.mark].join(' ')}  ${bar(t, 60)}  header: ${t.header}` },
  ...contrastWarnings(t).map(w => ({ text: `  ${t.glyphs.warn} ${w}`, tone: 'warning' as const })),
]

export const HELP: readonly string[] = columns([
  ['/dash', 'overview: meters, skills, health, suggestions'],
  ['/dash skills | meters | health', 'one view'],
  ['/dash tasks | context', 'background tasks; what fills the context'],
  ['/dash suggest [accept|dismiss|snooze <n>]', 'the suggestion queue'],
  ['/dash theme [<name> | new | show | import]', 'list, switch or make a theme'],
  ['/dash publish', 'a rolled-up snapshot for a private page'],
  ['/dash gpu | palette [brand] | godot | prs', 'the optional panels'],
  ['/dash switches | on|off <name> | off', 'features; bare off is the kill switch'],
  ['/dash records on|off | network on|off', 'keep counts; allow network reads'],
  ['/dash doctor | purge', 'check the install; delete the counts'],
], [], '')

/** What dash_read hands Claude: one view as plain text, so a surface that cannot draw still reads it. */
export const linesText = (lines: readonly Line[]): string => lines.map(l => l.text).join('\n')
