// dash views: pure logic (no $). The lines the /dash pane draws, the same lines as text where no
// pane draws, and what dash_read hands Claude. Every view reads the feed; none reads text.
import type { Feed, Health, SkillRow } from './collector-logic'
import { statusText, type Live } from './meters-logic'
import { suggestionLines, type Suggestion } from './suggest-logic'

export type Line = { text: string; tone?: 'warning' | 'error' | 'dim' | 'bold' }

export const VIEWS = ['overview', 'skills', 'meters', 'health', 'tasks', 'suggest', 'context', 'gpu', 'palette', 'godot', 'prs'] as const
export type View = (typeof VIEWS)[number]

/** `/dash <verb> <rest>`: the verb lower-cased, the rest as typed. */
export const parseDashArgs = (args: string): { verb: string; rest: string } => {
  const t = args.trim()
  const m = /^(\S+)\s*([\s\S]*)$/.exec(t)
  return m ? { verb: m[1]!.toLowerCase(), rest: m[2]!.trim() } : { verb: '', rest: '' }
}

const k = (n: number): string => (n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 10_000 ? `${Math.round(n / 1000)}k` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(Math.round(n)))
const usd = (n: number | null): string => (n === null ? '-' : `$${n.toFixed(2)}`)

/** The overview: meters, the week's totals, the busiest skills, health in one line, open suggestions. */
export const overviewLines = (args: { live: Live | null; feed: Feed; now: number; tasksLine: string | null; panels: string[] }): Line[] => {
  const { feed, now } = args
  const out: Line[] = [{ text: statusText(args.live, now), tone: 'bold' }]
  out.push({ text: `Week: ${feed.sessions7} session(s) · ${k(feed.tokens7)} tokens · ${usd(feed.cost7)}${feed.recording ? '' : ' · this session only (/dash records on keeps counts across sessions)'}`, tone: 'dim' })
  if (args.tasksLine) out.push({ text: args.tasksLine })
  const top = feed.skills.filter(s => s.fires30 > 0).slice(0, 5)
  out.push({ text: '' }, { text: 'Skills (30 days)', tone: 'bold' })
  if (top.length === 0) out.push({ text: 'No skill has fired yet.', tone: 'dim' })
  for (const s of top) out.push(skillLine(s))
  out.push({ text: '' }, { text: `Health: ${healthSummary(feed.health)}`, tone: healthTone(feed.health) })
  if (feed.suggestionsNew > 0) out.push({ text: `${feed.suggestionsNew} new suggestion(s): /dash suggest`, tone: 'warning' })
  for (const p of args.panels) out.push({ text: p, tone: 'dim' })
  out.push({ text: '/dash skills · meters · health · tasks · suggest · publish · switches · help', tone: 'dim' })
  return out
}

export const skillLine = (s: SkillRow): Line => {
  const bits = [`${s.fires30} fire(s)`, `${s.slash30} slash / ${s.auto30} auto`]
  if (s.failures30) bits.push(`${s.failures30} failed`)
  if (s.misroutes30) bits.push(`${s.misroutes30} likely misroute(s)`)
  if (s.tokens7) bits.push(`${k(s.tokens7)} tok 7d${s.cost7 !== null ? ` ${usd(s.cost7)}` : ''}`)
  return { text: `  ${s.name.replace(/^revenantworks-[a-z]+-/, '')}: ${bits.join(' · ')}`, tone: s.failures30 + s.misroutes30 > 0 ? 'warning' : undefined }
}

export const skillsLines = (feed: Feed): Line[] => {
  const out: Line[] = [{ text: `Skills: ${feed.skills.filter(s => s.listed).length} enabled (listed), ${feed.skills.filter(s => s.fires30 > 0).length} fired in 30 days`, tone: 'bold' }]
  out.push({ text: 'A likely misroute: a different skill fired within 2 minutes of an automatic fire, or an edit it led to was reverted.', tone: 'dim' })
  for (const s of feed.skills) out.push(s.fires30 > 0 ? skillLine(s) : { text: `  ${s.name.replace(/^revenantworks-[a-z]+-/, '')}: listed, no fire in 30 days`, tone: 'dim' })
  if (feed.skills.length === 0) out.push({ text: 'No skills listed or fired yet.', tone: 'dim' })
  return out
}

export const metersLines = (live: Live | null, feed: Feed, now: number): Line[] => {
  const out: Line[] = [{ text: statusText(live, now), tone: 'bold' }]
  if (live?.five !== null && live?.five !== undefined) out.push({ text: `5-hour window: ${Math.round(live.five)}% used` })
  if (live?.week !== null && live?.week !== undefined) out.push({ text: `Weekly window: ${Math.round(live.week)}% used${live.weekResetMs !== null ? `, resets ${new Date(live.weekResetMs).toISOString().slice(0, 16).replace('T', ' ')} UTC` : ''}` })
  if (live?.ctx !== null && live?.ctx !== undefined) out.push({ text: `Context: ${Math.round(live.ctx)}%`, tone: live.ctx >= 80 ? 'error' : live.ctx >= 60 ? 'warning' : undefined })
  if (live?.cacheHit !== null && live?.cacheHit !== undefined) out.push({ text: `Cache: ${Math.round(live.cacheHit * 100)}% of the last turn's input read from cache` })
  if (live?.costUsd !== null && live?.costUsd !== undefined) out.push({ text: `This session: ${usd(live.costUsd)}` })
  out.push({ text: `Context past 80% twice or more on ${feed.ctx80Days7} day(s) this week.`, tone: 'dim' })
  return out
}

export const healthSummary = (h: Health): string => {
  const plugins = Object.entries(h.plugins).map(([n, p]) => `${n} ${p.loaded ? 'loaded' : 'NOT LOADED'}`).join(', ') || 'no heartbeat yet'
  const drift = h.drift.filter(d => d.state === 'differs').length
  const gw = h.gatewarden ? `gatewarden ${h.gatewarden.total7} event(s) 7d` : 'gatewarden log absent'
  return `${plugins} · ${drift} hook(s) drifted · ${gw}${h.pinsChanged ? ` · ${h.pinsChanged} instruction file(s) changed` : ''}`
}

const healthTone = (h: Health): Line['tone'] =>
  Object.values(h.plugins).some(p => !p.loaded) || h.drift.some(d => d.state === 'differs') ? 'warning' : 'dim'

export const healthLines = (h: Health): Line[] => {
  const out: Line[] = [{ text: 'Health', tone: 'bold' }]
  for (const [n, p] of Object.entries(h.plugins)) out.push({ text: `  ${n.padEnd(8)} ${p.loaded ? `loaded ${p.version ?? ''}` : 'NOT LOADED this session'}${p.caught ? ` · ${p.caught} hook failure(s) caught` : ''}`, tone: p.loaded ? undefined : 'warning' })
  if (Object.keys(h.plugins).length === 0) out.push({ text: '  No heartbeat yet.', tone: 'dim' })
  out.push({ text: 'Hooks: repo .claude/hooks against the installed ~/.claude/hooks', tone: 'bold' })
  if (h.drift.length === 0) out.push({ text: '  Nothing to compare here.', tone: 'dim' })
  for (const d of h.drift) out.push({ text: `  ${d.hook}: ${d.state}`, tone: d.state === 'differs' ? 'warning' : undefined })
  out.push({ text: 'gatewarden (last 7 days)', tone: 'bold' })
  const g = h.gatewarden
  if (!g) out.push({ text: '  No event log (~/.claude/gatewarden/events.jsonl).', tone: 'dim' })
  else {
    const modes = Object.entries(g.byMode).map(([m, n]) => `${m} ${n}`).join(', ') || 'none'
    const outcomes = Object.entries(g.byOutcome).map(([m, n]) => `${m} ${n}`).join(', ') || 'none'
    out.push({ text: `  ${g.total7} event(s) · modes: ${modes} · outcomes: ${outcomes}` })
    if (g.topRules.length) out.push({ text: `  busiest rules: ${g.topRules.map(r => `${r.rule} ${r.n}`).join(', ')}`, tone: 'dim' })
  }
  if (h.pinsChanged) out.push({ text: `Instruction files changed since they were last loaded: ${h.pinsChanged}`, tone: 'warning' })
  return out
}

export const suggestLines = (rows: readonly Suggestion[]): Line[] => [{ text: 'Suggestions (never built; accepting gives you a line for NEXT.md)', tone: 'bold' }, ...suggestionLines(rows).map(text => ({ text }))]

export const HELP: readonly string[] = [
  '/dash                    overview: meters, skills, health, suggestions',
  '/dash skills|meters|health|tasks|context   one view',
  '/dash suggest [accept|dismiss|snooze <n>]  the suggestion queue',
  '/dash publish            a rolled-up snapshot.json for a private mobile page',
  '/dash gpu · palette [brand] · godot · prs  the optional panels',
  '/dash switches · on|off <name> · off (kill switch) · on',
  '/dash records on|off · network on|off · doctor · purge',
]

/** What dash_read hands Claude: one view as plain text, so a surface that cannot draw still reads it. */
export const linesText = (lines: readonly Line[]): string => lines.map(l => l.text).join('\n')
