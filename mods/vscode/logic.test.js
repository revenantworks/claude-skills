'use strict'
const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const L = require('./logic')

const HOUR = 3_600_000
const DAY = 24 * HOUR
const NOW = Date.UTC(2026, 9, 6, 12)
const sec = ms => Math.floor(ms / 1000)

const meter = (over = {}) => JSON.stringify({
  written_at: sec(NOW - 60_000),
  five_hour: { used_percentage: 0, resets_at: sec(NOW + 2 * HOUR) },
  seven_day: { used_percentage: 69, resets_at: sec(NOW + 1.47 * DAY) },
  context_used_percentage: 38,
  ...over,
})

const feed = (over = {}) => JSON.stringify({
  version: 1,
  generatedAt: NOW - 60_000,
  recording: true,
  sessions7: 3,
  tokens7: 123456,
  cost7: 4.5,
  suggestionsNew: 1,
  skills: [
    { name: 'revenantworks-foundation-alpha', listed: true, fires7: 4, fires30: 9, slash30: 2, auto30: 7, failures30: 1, misroutes30: 2, tokens7: 50000, cost7: 1.2 },
    { name: 'beta', listed: true, fires7: 1, fires30: 1, slash30: 1, auto30: 0, failures30: 0, misroutes30: 0, tokens7: 10, cost7: null },
  ],
  health: { plugins: { dash: { loaded: true }, privacy: { loaded: false } }, drift: [{ hook: 'x.py', state: 'differs' }], gatewarden: { total7: 7, byMode: { watch: 6, guard: 1 } } },
  ...over,
})

test('PACE is 95 times the fraction of the week elapsed; gap is weekly minus PACE', () => {
  const half = L.pacewrightPace(50, NOW + 3.5 * DAY, NOW)
  assert.equal(half.pace, 47.5)
  assert.equal(half.gap, 2.5)
  assert.equal(L.pacewrightPace(10, NOW + 7 * DAY, NOW).pace, 0)
  assert.equal(L.pacewrightPace(10, NOW - DAY, NOW).pace, 95)
})

test('the PACE formula matches the dash plugin, so the two never disagree', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'dash', 'hooks', 'collector-logic.ts'), 'utf8')
  assert.match(src, /export const DAY = 86_400_000/)
  assert.match(src, /const fraction = Math\.min\(1, Math\.max\(0, \(now - \(resetMs - 7 \* DAY\)\) \/ \(7 \* DAY\)\)\)/)
  assert.match(src, /const pace = Math\.round\(95 \* fraction \* 10\) \/ 10/)
  assert.match(src, /gap: Math\.round\(\(week - pace\) \* 10\) \/ 10/)
  assert.equal(L.WEEK_MS, 7 * DAY)
  assert.equal(L.STALE_MS, 15 * 60_000)
})

test('the status text leads with weekly, PACE, gap and the 5-hour window', () => {
  const u = L.parseUsage(meter(), NOW)
  assert.equal(u.stale, false)
  assert.equal(u.context, 38)
  assert.equal(u.pace.pace, 75.1)
  assert.equal(L.paceText(u), 'W 69% · PACE 75 · gap -6 · 5h 0%')
  assert.equal(L.paceLook(u), null)
})

test('resets_at may be epoch seconds, epoch ms or ISO', () => {
  const iso = new Date(NOW + 3.5 * DAY).toISOString()
  for (const r of [sec(NOW + 3.5 * DAY), NOW + 3.5 * DAY, iso]) {
    const u = L.parseUsage(meter({ seven_day: { used_percentage: 50, resets_at: r } }), NOW)
    assert.equal(u.pace.pace, 47.5)
  }
})

test('thresholds: amber at 80% weekly, red at 90%', () => {
  assert.equal(L.tone(79.9), null)
  assert.equal(L.tone(80), 'amber')
  assert.equal(L.tone(89.9), 'amber')
  assert.equal(L.tone(90), 'red')
  assert.equal(L.tone(null), null)
  const u = L.parseUsage(meter({ seven_day: { used_percentage: 91, resets_at: sec(NOW + DAY) } }), NOW)
  assert.equal(L.paceLook(u), 'red')
})

test('a file older than 15 minutes is stale, and stale wins over red', () => {
  const fresh = L.parseUsage(meter({ written_at: sec(NOW - 14 * 60_000) }), NOW)
  assert.equal(fresh.stale, false)
  const old = L.parseUsage(meter({ written_at: sec(NOW - 16 * 60_000), seven_day: { used_percentage: 95, resets_at: sec(NOW + DAY) } }), NOW)
  assert.equal(old.stale, true)
  assert.equal(L.paceLook(old), 'stale')
  assert.match(L.paceText(old), /stale$/)
  assert.equal(L.parseUsage(meter({ written_at: undefined }), NOW).stale, true)
})

test('a missing or malformed meter file says so and greys the item', () => {
  assert.deepEqual(L.parseUsage(null, NOW), { error: 'missing' })
  assert.deepEqual(L.parseUsage('{not json', NOW), { error: 'malformed' })
  assert.deepEqual(L.parseUsage('[]', NOW), { error: 'malformed' })
  assert.deepEqual(L.parseUsage('{"five_hour":{"used_percentage":"x"}}', NOW), { error: 'malformed' })
  assert.equal(L.paceText(L.parseUsage(null, NOW)), 'W ? · no meter file')
  assert.equal(L.paceText(L.parseUsage('nope', NOW)), 'W ? · meter file unreadable')
  assert.equal(L.paceLook({ error: 'missing' }), 'stale')
})

test('a weekly window without a reset still shows, without PACE', () => {
  const u = L.parseUsage(meter({ seven_day: { used_percentage: 40, resets_at: null } }), NOW)
  assert.equal(u.pace, null)
  assert.equal(L.paceText(u), 'W 40% · 5h 0%')
})

test('budget decision: mode and ceiling while unexpired; null when absent, expired or malformed', () => {
  const ok = JSON.stringify({ mode: 'pace', parallel_ceiling: 3, expires_at: new Date(NOW + HOUR).toISOString(), stop_bands: { slow: 80, stop: 90 } })
  const b = L.parseBudget(ok, NOW)
  assert.equal(b.mode, 'pace')
  assert.equal(b.parallelCeiling, 3)
  assert.equal(L.budgetText(b), 'MODE pace · x3')
  assert.equal(L.parseBudget(JSON.stringify({ mode: 'pace', expires_at: new Date(NOW - 1).toISOString() }), NOW), null)
  assert.equal(L.parseBudget(JSON.stringify({ expires_at: new Date(NOW + HOUR).toISOString() }), NOW), null)
  assert.equal(L.parseBudget(null, NOW), null)
  assert.equal(L.parseBudget('{', NOW), null)
  assert.equal(L.budgetText(null), null)
  assert.equal(L.budgetText({ ...b, parallelCeiling: null }), 'MODE pace')
})

test('switch file: the kill switch and switched features; malformed reads as defaults', () => {
  const s = L.parseSwitches(JSON.stringify({ version: 1, off: true, types: { feed: false }, features: { D1: true, D12: false, junk: 'x' } }))
  assert.equal(s.off, true)
  assert.deepEqual(s.features, { D1: true, D12: false })
  assert.equal(s.types, undefined)
  assert.deepEqual(L.parseSwitches('{bad'), { present: true, off: false, features: {} })
  assert.equal(L.parseSwitches(null).present, false)
  assert.equal(L.parseSwitches(JSON.stringify({ off: 'yes' })).off, false)
})

test('the readout names both windows with resets, context, budget and switches', () => {
  const lines = L.readoutLines({
    now: NOW,
    usage: L.parseUsage(meter(), NOW),
    budget: L.parseBudget(JSON.stringify({ mode: 'pace', parallel_ceiling: 2, expires_at: new Date(NOW + HOUR).toISOString(), top_tier_open: false }), NOW),
    switches: L.parseSwitches(JSON.stringify({ off: true, features: { D1: true } })),
    feed: L.parseFeed(feed(), NOW),
  }).join('\n')
  assert.match(lines, /Weekly \(7d\): 69% used, resets .* \(in 1d 11h\)/)
  assert.match(lines, /5-hour: 0% used, resets .* \(in 2h 00m\)/)
  assert.match(lines, /Context: 38%/)
  assert.match(lines, /Budget mode: pace, parallel ceiling 2/)
  assert.match(lines, /Top tier: closed/)
  assert.match(lines, /Mods kill switch: ON/)
  assert.match(lines, /Features switched on: D1/)
  assert.match(lines, /dash: dash 5 fires 7d · 3 flags · 1 new/)
  assert.match(lines, /alpha: 1 failed, 2 likely misroute/)
  const bare = L.readoutLines({ now: NOW, usage: { error: 'missing' }, budget: null, switches: L.parseSwitches(null), feed: L.parseFeed(null, NOW) }).join('\n')
  assert.match(bare, /Meter file: absent/)
  assert.match(bare, /no current decision file/)
  assert.match(bare, /not written yet/)
  assert.match(bare, /dash feed: absent/)
})

test('the extension and installer stay offline and write nothing outside install', () => {
  const ext = fs.readFileSync(path.join(__dirname, 'extension.js'), 'utf8')
  assert.doesNotMatch(ext, /require\(['"](node:)?(https?|net|tls|dgram|child_process)['"]\)|fetch\(|writeFile|appendFile|rmSync|unlink/)
  const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json'), 'utf8'))
  assert.equal(pkg.engines.vscode, '^1.90.0')
  assert.deepEqual(pkg.activationEvents, ['onStartupFinished'])
  assert.equal(pkg.dependencies, undefined)
  const dash = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'dash', '.claude-plugin', 'plugin.json'), 'utf8'))
  assert.equal(pkg.version, dash.version, 'the extension carries the dash plugin version')
  assert.match(ext, /enableScripts: false/)
})

test('the feed: counts parsed and typed; absent or malformed says so', () => {
  const f = L.parseFeed(feed(), NOW)
  assert.equal(f.stale, false)
  assert.equal(f.skills.length, 2)
  assert.equal(f.health.drift, 1)
  assert.deepEqual(f.health.plugins, [{ name: 'dash', loaded: true }, { name: 'privacy', loaded: false }])
  assert.equal(L.feedText(f), 'dash 5 fires 7d · 3 flags · 1 new')
  assert.equal(L.parseFeed(feed({ generatedAt: NOW - 31 * 60_000 }), NOW).stale, true)
  assert.deepEqual(L.parseFeed(null, NOW), { error: 'missing' })
  assert.deepEqual(L.parseFeed('{"version":2,"skills":[]}', NOW), { error: 'malformed' })
  assert.equal(L.feedText({ error: 'missing' }), null)
})

test('the panel is static, escaped HTML with a CSP and no script', () => {
  const evil = feed({ skills: [{ name: '<img src=x onerror=alert(1)>', listed: true, fires7: 1, fires30: 1, slash30: 0, auto30: 1, failures30: 0, misroutes30: 0, tokens7: 1 }] })
  const html = L.panelHtml({ now: NOW, usage: L.parseUsage(meter(), NOW), budget: null, feed: L.parseFeed(evil, NOW) })
  assert.match(html, /Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';"/)
  assert.doesNotMatch(html, /<script/i)
  assert.doesNotMatch(html, /<img/)
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/)
  assert.match(html, /gatewarden 7 event\(s\)/)
  const none = L.panelHtml({ now: NOW, usage: { error: 'missing' }, budget: null, feed: L.parseFeed(null, NOW) })
  assert.match(none, /\/dash records on/)
})

test('activate wires the status items and a script-free panel (against a stub of the vscode API)', () => {
  const os = require('node:os')
  const Module = require('node:module')
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'dash-vscode-'))
  fs.mkdirSync(path.join(home, '.claude', 'revenantworks', 'dash'), { recursive: true })
  fs.writeFileSync(path.join(home, '.claude', 'revenantworks', 'dash', 'feed.json'), feed({ generatedAt: Date.now() }))
  const items = []
  const commands = {}
  let panelOptions = null
  const panel = { webview: { html: '' }, reveal() {}, onDidDispose() {} }
  const stub = {
    StatusBarAlignment: { Left: 1 },
    ViewColumn: { Beside: -2 },
    ThemeColor: class { constructor(id) { this.id = id } },
    MarkdownString: class { constructor(v) { this.value = v } },
    RelativePattern: class {},
    Uri: { file: f => f },
    window: {
      createStatusBarItem: id => { const it = { id, show() { this.shown = true }, hide() { this.shown = false } }; items.push(it); return it },
      createWebviewPanel: (_id, _title, _col, opts) => { panelOptions = opts; return panel },
      showQuickPick: async () => undefined,
    },
    commands: { registerCommand: (id, fn) => { commands[id] = fn; return { dispose() {} } } },
    workspace: { createFileSystemWatcher: () => ({ onDidChange() {}, onDidCreate() {}, onDidDelete() {}, dispose() {} }) },
  }
  const realLoad = Module._load
  const saved = { HOME: process.env.HOME, USERPROFILE: process.env.USERPROFILE }
  Module._load = function (req, ...rest) { return req === 'vscode' ? stub : realLoad.call(this, req, ...rest) }
  process.env.HOME = home
  process.env.USERPROFILE = home
  const subs = []
  try {
    delete require.cache[require.resolve('./extension.js')]
    require('./extension.js').activate({ subscriptions: subs })
    const dash = items.find(i => i.id === 'revenantworks.dash.feed')
    assert.equal(dash.shown, true)
    assert.equal(dash.text, '$(graph) dash 5 fires 7d · 3 flags · 1 new')
    commands['revenantworksDash.openPanel']()
    assert.equal(panelOptions.enableScripts, false)
    assert.match(panel.webview.html, /<td>alpha<\/td>/)
  } finally {
    for (const s of subs) if (s && typeof s.dispose === 'function') s.dispose()
    Module._load = realLoad
    process.env.HOME = saved.HOME
    if (saved.USERPROFILE === undefined) delete process.env.USERPROFILE
    else process.env.USERPROFILE = saved.USERPROFILE
    fs.rmSync(home, { recursive: true, force: true })
  }
})
