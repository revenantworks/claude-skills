'use strict'
// Pure logic for the Revenantworks dash extension (no `vscode`, no fs, no network): the status bar
// item, its readout and the panel's HTML. extension.js reads the files and hands their text here,
// so node:test covers every rule. The panel is static HTML with no script.

const HOUR_MS = 3_600_000
const WEEK_MS = 7 * 24 * HOUR_MS
/** A meter file older than this is stale (the same 15 minutes the dash plugin uses). */
const STALE_MS = 15 * 60_000
/** Weekly percent at which the pace item turns amber, then red. */
const AMBER_AT = 80
const RED_AT = 90

/**
 * pacewright's PACE, exactly as the dash plugin computes it (hooks/collector-logic.ts, paceOf):
 * PACE = 95 x the fraction of the 7-day window elapsed; gap = weekly % - PACE.
 * A test reads that TypeScript source so the two cannot drift apart.
 */
function pacewrightPace(weeklyPct, resetsAtMs, now) {
  const start = resetsAtMs - WEEK_MS
  const fraction = Math.min(1, Math.max(0, (now - start) / WEEK_MS))
  const pace = Math.round(95 * fraction * 10) / 10
  return { weekly: weeklyPct, pace, gap: Math.round((weeklyPct - pace) * 10) / 10 }
}

function parseJson(text) {
  if (typeof text !== 'string' || text.trim() === '') return null
  try {
    const v = JSON.parse(text)
    return v && typeof v === 'object' && !Array.isArray(v) ? v : null
  } catch {
    return null
  }
}

function num(v) {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

/** A time as epoch ms: epoch seconds (the meter file), epoch ms, or an ISO string. */
function toMs(v) {
  if (typeof v === 'number' && Number.isFinite(v)) return v > 1e12 ? v : v * 1000
  if (typeof v === 'string' && v.trim() !== '') {
    const ms = Date.parse(v)
    return Number.isFinite(ms) ? ms : null
  }
  return null
}

function windowOf(v) {
  if (!v || typeof v !== 'object') return null
  const pct = num(v.used_percentage)
  if (pct === null) return null
  return { pct, resetsAt: toMs(v.resets_at) }
}

/**
 * Parses ~/.claude/usage-windows.json. Returns { error } when the file is missing or malformed,
 * otherwise the two windows, context, PACE (when the weekly reset is known) and staleness.
 */
function parseUsage(text, now) {
  if (text === null || text === undefined) return { error: 'missing' }
  const o = parseJson(text)
  if (!o) return { error: 'malformed' }
  const fiveHour = windowOf(o.five_hour)
  const sevenDay = windowOf(o.seven_day)
  if (!fiveHour && !sevenDay) return { error: 'malformed' }
  const writtenAt = toMs(o.written_at)
  const stale = writtenAt === null || now - writtenAt > STALE_MS
  const pace = sevenDay && sevenDay.resetsAt !== null ? pacewrightPace(sevenDay.pct, sevenDay.resetsAt, now) : null
  return { fiveHour, sevenDay, context: num(o.context_used_percentage), writtenAt, stale, pace }
}

/** 'red' at 90% weekly, 'amber' at 80%, else null. */
function tone(weeklyPct) {
  if (typeof weeklyPct !== 'number' || !Number.isFinite(weeklyPct)) return null
  if (weeklyPct >= RED_AT) return 'red'
  if (weeklyPct >= AMBER_AT) return 'amber'
  return null
}

function signed(n) {
  const r = Math.round(n)
  return `${r >= 0 ? '+' : ''}${r}`
}

/** "W 69% · PACE 79 · gap -10 · 5h 0%"; "stale" is appended when the file is old. */
function paceText(u) {
  if (!u || u.error) return u && u.error === 'malformed' ? 'W ? · meter file unreadable' : 'W ? · no meter file'
  const parts = []
  if (u.sevenDay) parts.push(`W ${Math.round(u.sevenDay.pct)}%`)
  if (u.pace) parts.push(`PACE ${Math.round(u.pace.pace)}`, `gap ${signed(u.pace.gap)}`)
  if (u.fiveHour) parts.push(`5h ${Math.round(u.fiveHour.pct)}%`)
  if (u.stale) parts.push('stale')
  return parts.join(' · ')
}

/** How the pace item looks: 'stale' greys it and wins over amber and red. */
function paceLook(u) {
  if (!u || u.error) return 'stale'
  if (u.stale) return 'stale'
  return tone(u.sevenDay ? u.sevenDay.pct : null)
}

/**
 * Parses ~/.dispatch/budget-decision.json (dispatchwright's budget decision):
 * null when unreadable, without a mode, or past expires_at.
 */
function parseBudget(text, now) {
  const o = parseJson(text)
  if (!o) return null
  const expiresAt = typeof o.expires_at === 'string' ? toMs(o.expires_at) : null
  if (expiresAt === null || expiresAt <= now) return null
  if (typeof o.mode !== 'string' || o.mode === '') return null
  const bands = o.stop_bands && typeof o.stop_bands === 'object' ? o.stop_bands : {}
  return {
    mode: o.mode.slice(0, 40),
    parallelCeiling: num(o.parallel_ceiling),
    expiresAt,
    writtenAt: typeof o.written_at === 'string' ? toMs(o.written_at) : null,
    stopSlow: num(bands.slow),
    stopStop: num(bands.stop),
    topTierOpen: typeof o.top_tier_open === 'boolean' ? o.top_tier_open : null,
    hostedCiAllowed: typeof o.hosted_ci_allowed === 'boolean' ? o.hosted_ci_allowed : null,
  }
}

function budgetText(b) {
  if (!b) return null
  return b.parallelCeiling === null ? `MODE ${b.mode}` : `MODE ${b.mode} · x${b.parallelCeiling}`
}

function boolMap(v) {
  const out = {}
  if (!v || typeof v !== 'object' || Array.isArray(v)) return out
  for (const [k, x] of Object.entries(v)) if (typeof x === 'boolean') out[k] = x
  return out
}

/** The mods switch file (~/.claude/revenantworks/switches.json); malformed reads as shipped defaults. */
function parseSwitches(text) {
  const o = parseJson(text)
  if (!o) return { present: typeof text === 'string', off: false, features: {} }
  return { present: true, off: o.off === true, features: boolMap(o.features) }
}

function localTime(ms) {
  if (ms === null || ms === undefined) return 'unknown'
  const d = new Date(ms)
  const pad = n => String(n).padStart(2, '0')
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  return `${days[d.getDay()]} ${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function countdown(ms) {
  if (!Number.isFinite(ms) || ms <= 0) return 'now'
  const mins = Math.floor(ms / 60_000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ${String(mins % 60).padStart(2, '0')}m`
  return `${Math.floor(hours / 24)}d ${hours % 24}h`
}

/** Every line of the full readout, plain text (the quick-pick and the hover both use it). */
function readoutLines(args) {
  const { usage: u, budget: b, switches: s, now } = args
  const out = []
  if (!u || u.error) {
    out.push(u && u.error === 'malformed' ? 'Meter file: unreadable' : 'Meter file: absent (the status line writes it)')
  } else {
    out.push(`Pace: ${paceText(u)}`)
    for (const [label, w] of [['Weekly (7d)', u.sevenDay], ['5-hour', u.fiveHour]]) {
      if (!w) continue
      const reset = w.resetsAt === null ? 'reset unknown' : `resets ${localTime(w.resetsAt)} (in ${countdown(w.resetsAt - now)})`
      out.push(`${label}: ${Math.round(w.pct)}% used, ${reset}`)
    }
    if (u.pace) out.push(`PACE ${u.pace.pace.toFixed(1)}, gap ${u.pace.gap >= 0 ? '+' : ''}${u.pace.gap.toFixed(1)} (weekly minus PACE)`)
    out.push(`Context: ${u.context === null ? 'unknown' : `${Math.round(u.context)}%`}`)
    out.push(`Meter file written ${u.writtenAt === null ? 'at an unknown time' : `${localTime(u.writtenAt)} (${countdown(now - u.writtenAt)} ago)`}${u.stale ? ', stale' : ''}`)
  }
  if (b) {
    out.push(`Budget mode: ${b.mode}${b.parallelCeiling === null ? '' : `, parallel ceiling ${b.parallelCeiling}`}, expires ${localTime(b.expiresAt)}`)
    if (b.stopSlow !== null || b.stopStop !== null) out.push(`Stop bands: slow ${b.stopSlow ?? '-'}%, stop ${b.stopStop ?? '-'}%`)
    if (b.topTierOpen !== null) out.push(`Top tier: ${b.topTierOpen ? 'open' : 'closed'}`)
    if (b.hostedCiAllowed !== null) out.push(`Hosted CI: ${b.hostedCiAllowed ? 'allowed' : 'not allowed'}`)
  } else {
    out.push('Budget mode: no current decision file')
  }
  const f = args.feed
  if (f && !f.error) {
    out.push(`dash: ${feedText(f)}`)
    const flagged = f.skills.filter(x => x.failures30 + x.misroutes30 > 0).slice(0, 5)
    for (const x of flagged) out.push(`  ${x.name.replace(/^revenantworks-[a-z]+-/, '')}: ${x.failures30} failed, ${x.misroutes30} likely misroute(s) in 30 days`)
  } else {
    out.push(f && f.error === 'malformed' ? 'dash feed: unreadable' : 'dash feed: absent (/dash records on in Claude Code writes it)')
  }
  if (s) {
    out.push(`Mods kill switch: ${s.off ? 'ON (every feature stopped; /dash on restores)' : 'off'}`)
    const on = Object.entries(s.features).filter(([, v]) => v).map(([k]) => k).sort()
    const off = Object.entries(s.features).filter(([, v]) => !v).map(([k]) => k).sort()
    out.push(`Features switched on: ${on.length ? on.join(', ') : 'none beyond the shipped defaults'}`)
    if (off.length) out.push(`Features switched off: ${off.join(', ')}`)
    if (!s.present) out.push('Switch file: not written yet (shipped defaults)')
  }
  return out
}

// ---------- the dash feed (~/.claude/revenantworks/dash/feed.json) ----------

/** A feed older than this is shown as stale (the plugin rolls it up every 5 minutes while it runs). */
const FEED_STALE_MS = 30 * 60_000

function str(v, max = 80) {
  return typeof v === 'string' ? v.slice(0, max) : ''
}

/**
 * Parses feed.json, keeping only the fields the panel shows, each checked for type. Returns
 * { error } when absent or malformed. The feed holds counts only; nothing here is text from a session.
 */
function parseFeed(text, now) {
  if (text === null || text === undefined) return { error: 'missing' }
  const o = parseJson(text)
  if (!o || o.version !== 1 || !Array.isArray(o.skills)) return { error: 'malformed' }
  const skills = o.skills.slice(0, 200).filter(s => s && typeof s === 'object' && typeof s.name === 'string').map(s => ({
    name: str(s.name),
    listed: s.listed === true,
    fires7: num(s.fires7) ?? 0,
    fires30: num(s.fires30) ?? 0,
    slash30: num(s.slash30) ?? 0,
    auto30: num(s.auto30) ?? 0,
    failures30: num(s.failures30) ?? 0,
    misroutes30: num(s.misroutes30) ?? 0,
    tokens7: num(s.tokens7) ?? 0,
    cost7: num(s.cost7),
  }))
  const h = o.health && typeof o.health === 'object' ? o.health : {}
  const plugins = h.plugins && typeof h.plugins === 'object' ? Object.entries(h.plugins).slice(0, 10).map(([name, p]) => ({ name: str(name, 30), loaded: !!(p && p.loaded === true) })) : []
  const drift = Array.isArray(h.drift) ? h.drift.filter(d => d && d.state === 'differs').length : 0
  const gw = h.gatewarden && typeof h.gatewarden === 'object' ? { total7: num(h.gatewarden.total7) ?? 0, byMode: boolOrNumMap(h.gatewarden.byMode) } : null
  const generatedAt = num(o.generatedAt)
  return {
    generatedAt,
    stale: generatedAt === null || now - generatedAt > FEED_STALE_MS,
    recording: o.recording === true,
    sessions7: num(o.sessions7) ?? 0,
    tokens7: num(o.tokens7) ?? 0,
    cost7: num(o.cost7),
    suggestionsNew: num(o.suggestionsNew) ?? 0,
    skills,
    health: { plugins, drift, gatewarden: gw },
  }
}

function boolOrNumMap(v) {
  const out = {}
  if (!v || typeof v !== 'object' || Array.isArray(v)) return out
  for (const [k, x] of Object.entries(v).slice(0, 20)) if (typeof x === 'number' && Number.isFinite(x)) out[str(k, 30)] = x
  return out
}

function kTokens(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 10_000) return `${Math.round(n / 1000)}k`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(Math.round(n))
}

/** The status bar item's text: "dash 41 fires · 2 new"; null hides it when no feed exists. */
function feedText(f) {
  if (!f || f.error) return null
  const fires = f.skills.reduce((n, s) => n + s.fires7, 0)
  const flags = f.skills.reduce((n, s) => n + s.failures30 + s.misroutes30, 0)
  const parts = [`dash ${fires} fire${fires === 1 ? '' : 's'} 7d`]
  if (flags) parts.push(`${flags} flag${flags === 1 ? '' : 's'}`)
  if (f.suggestionsNew) parts.push(`${f.suggestionsNew} new`)
  if (f.stale) parts.push('stale')
  return parts.join(' · ')
}

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
function esc(v) {
  return String(v).replace(/[&<>"']/g, c => ESC[c])
}

/**
 * The panel: one static HTML page, no script, a CSP that allows only its own inline style.
 * Every value is escaped. Colours come from the VS Code theme variables.
 */
function panelHtml(args) {
  const { feed: f, usage: u, budget: b, now } = args
  const rows = []
  rows.push(`<h1>dash</h1><p class="dim">${esc(u && !u.error ? paceText(u) : 'No meter file (the status line writes it).')}</p>`)
  if (b) rows.push(`<p class="dim">${esc(budgetText(b))}</p>`)
  if (!f || f.error) {
    rows.push(`<p>${f && f.error === 'malformed' ? 'The feed is unreadable.' : 'No feed yet.'} In Claude Code, <code>/dash records on</code> keeps counts (never text) and writes <code>~/.claude/revenantworks/dash/feed.json</code>, which this panel reads.</p>`)
  } else {
    rows.push(`<p>Week: ${esc(f.sessions7)} session(s) · ${esc(kTokens(f.tokens7))} tokens${f.cost7 === null ? '' : ` · $${esc(f.cost7.toFixed(2))}`} · rolled up ${esc(f.generatedAt === null ? 'at an unknown time' : `${countdown(now - f.generatedAt)} ago`)}${f.stale ? ' <span class="warn">(stale)</span>' : ''}</p>`)
    if (f.suggestionsNew) rows.push(`<p class="warn">${esc(f.suggestionsNew)} new suggestion(s): <code>/dash suggest</code> in Claude Code.</p>`)
    rows.push('<h2>Skills</h2><table><tr><th>skill</th><th>listed</th><th>7d</th><th>30d</th><th>slash</th><th>auto</th><th>failed</th><th>misroutes</th><th>tokens 7d</th></tr>')
    for (const s of f.skills.slice(0, 60)) {
      const flag = s.failures30 + s.misroutes30 > 0 ? ' class="warn"' : s.fires30 === 0 ? ' class="dim"' : ''
      rows.push(`<tr${flag}><td>${esc(s.name.replace(/^revenantworks-[a-z]+-/, ''))}</td><td>${s.listed ? 'yes' : '-'}</td><td>${esc(s.fires7)}</td><td>${esc(s.fires30)}</td><td>${esc(s.slash30)}</td><td>${esc(s.auto30)}</td><td>${esc(s.failures30)}</td><td>${esc(s.misroutes30)}</td><td>${esc(kTokens(s.tokens7))}</td></tr>`)
    }
    rows.push('</table>')
    const plugins = f.health.plugins.map(p => `${esc(p.name)} ${p.loaded ? 'loaded' : '<span class="warn">not loaded</span>'}`).join(', ') || 'no heartbeat'
    const gw = f.health.gatewarden ? `gatewarden ${esc(f.health.gatewarden.total7)} event(s) in 7 days (${Object.entries(f.health.gatewarden.byMode).map(([m, n]) => `${esc(m)} ${esc(n)}`).join(', ') || 'none'})` : 'no gatewarden log'
    rows.push(`<h2>Health</h2><p>${plugins} · ${esc(f.health.drift)} hook(s) drifted · ${gw}</p>`)
  }
  rows.push('<p class="dim">Read-only. This panel reads local files and never writes, runs or sends anything.</p>')
  return [
    '<!doctype html><html><head><meta charset="utf-8">',
    `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">`,
    '<style>body{font-family:var(--vscode-font-family);color:var(--vscode-foreground);background:var(--vscode-editor-background);padding:0 12px}',
    'table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:2px 8px;border-bottom:1px solid var(--vscode-panel-border)}',
    '.dim{opacity:.7}.warn{color:var(--vscode-editorWarning-foreground)}code{font-family:var(--vscode-editor-font-family)}</style>',
    '</head><body>', ...rows, '</body></html>',
  ].join('\n')
}

module.exports = {
  AMBER_AT,
  FEED_STALE_MS,
  esc,
  feedText,
  panelHtml,
  parseFeed,
  RED_AT,
  STALE_MS,
  WEEK_MS,
  budgetText,
  countdown,
  localTime,
  pacewrightPace,
  paceLook,
  paceText,
  parseBudget,
  parseSwitches,
  parseUsage,
  readoutLines,
  tone,
}
