// Tests carried over from the retired plugins for the logic dash keeps.
import { describe, expect, test } from 'claude-code/testing'

import { CATALOG, RETIRED, byId, featuresOf } from '../hooks/lib/catalog'
import { applySwitchCommand } from '../hooks/lib/commands'
import { defaultSwitches, isFeatureOn, isNetworkOn, isRecordingOn, parseSwitches, serializeSwitches } from '../hooks/lib/switches'
import { liveFromMeterFile, meterFile, pacewrightPace, shouldWriteMeterFile, statusText } from '../hooks/meters-logic'
import {
  RESEARCH_SKILL, bandLine, ciFacts, comfyFrom, countsAsProof, floorDrop, godotRun, gutCounts, judge, junitCounts, leaseLines,
  leasePath, lmsFrom, ollamaFrom, paletteTokens, parseLease, parseRoster, pinChanges, resolveBrand, versionAtLeast,
} from '../hooks/panels-logic'
import {
  changesPrs, estimateFor, lastLineOf, parseEstWall, parsePrList, prChanges, prLine, recordDuration, statusWord,
  sanitizeTaskHistory, summariseLedger, taskSignature, taskStatusLines, tasksHeadline,
} from '../hooks/tasks-logic'

const DAY = 24 * 3600_000
const NL = String.fromCharCode(10)
const NOW = Date.UTC(2026, 9, 8, 12)
const ISO = new Date(NOW).toISOString()

describe('switches (C2, one on/off file)', () => {
  test('features run from install; records and network wait for their own yes; the kill switch beats all', () => {
    const sw = parseSwitches('{not json')
    expect(isFeatureOn(sw, 'D2')).toBe(true)
    expect(isFeatureOn(sw, 'W3')).toBe(true)
    expect(isFeatureOn(sw, 'D1')).toBe(false)
    expect(isRecordingOn(sw, 'D1')).toBe(false)
    expect(isNetworkOn(sw, 'D12')).toBe(false)
    expect(isFeatureOn({ ...sw, off: true }, 'W3')).toBe(false)
    expect(isRecordingOn({ ...sw, off: true, features: { D1: true } }, 'D1')).toBe(false)
  })
  test('round-trips; retired fields (types, reminders, theme) are dropped', () => {
    const sw = { ...defaultSwitches(), features: { D1: true } }
    expect(parseSwitches(serializeSwitches(sw))).toEqual(sw)
    expect(parseSwitches('{"types":{"lens":false},"reminders":{"all":false},"theme":{"choice":"mine"}}')).toEqual(defaultSwitches())
  })
  test('on and off by name or id, the kill switch, records and network; only the person', () => {
    let r = applySwitchCommand(defaultSwitches(), 'off secret-redact', true, ISO)
    expect(r.sw.features.W3).toBe(false)
    r = applySwitchCommand(r.sw, 'on W3 gpu-panel', true, ISO)
    expect(r.sw.features.W3 && r.sw.features.D10).toBe(true)
    r = applySwitchCommand(r.sw, 'off', true, ISO)
    expect(r.sw.off).toBe(true)
    r = applySwitchCommand(r.sw, 'on', true, ISO)
    expect(r.sw.off).toBe(false)
    r = applySwitchCommand(r.sw, 'records on', true, ISO)
    for (const x of CATALOG.filter(c => c.records)) expect(isRecordingOn(r.sw, x.id)).toBe(true)
    r = applySwitchCommand(r.sw, 'network on', true, ISO)
    expect(isNetworkOn(r.sw, 'D12')).toBe(true)
    expect(applySwitchCommand(defaultSwitches(), 'off', false, ISO).changed).toBe(false)
    expect(applySwitchCommand(defaultSwitches(), 'on nothing-like-this', true, ISO).changed).toBe(false)
    expect(applySwitchCommand(defaultSwitches(), 'switches', false, ISO).text).toMatch(/collector/)
  })
})

describe('catalog', () => {
  test('two plugins; every feature has a unique readable name; retired ids are gone', () => {
    expect([...new Set(CATALOG.map(x => x.plugin))].sort()).toEqual(['dash', 'privacy'])
    const slugs = CATALOG.map(x => x.slug)
    expect(new Set(slugs).size).toBe(slugs.length)
    for (const x of CATALOG) {
      expect(byId(x.slug)).toBe(x)
      expect(byId(x.id)).toBe(x)
    }
    for (const id of RETIRED) expect(byId(id)).toBe(undefined)
    expect(CATALOG.filter(x => x.network).map(x => x.id)).toEqual(['D12'])
    expect(CATALOG.filter(x => x.records).map(x => x.id)).toEqual(['D1', 'D6', 'D7', 'D8'])
  })
  test('dash carries on every feature the user folded into it', () => {
    const absorbed = new Set(featuresOf('dash').flatMap(x => x.absorbs))
    for (const id of ['F1', 'F1b', 'F2', 'F3', 'F3e', 'F3f', 'F5', 'C1', 'C4', 'C5', 'C11', 'C14', 'C17', 'S4', 'L1', 'G1', 'X5']) expect(absorbed.has(id)).toBe(true)
  })
})

describe('meters (F1, F1b)', () => {
  test('PACE is 95 times the fraction of the week elapsed', () => {
    const half = pacewrightPace(50, NOW + 3.5 * DAY, NOW)
    expect(half.pace).toBe(47.5)
    expect(half.gap).toBe(2.5)
    expect(pacewrightPace(10, NOW + 7 * DAY, NOW).pace).toBe(0)
  })
  test('the fallback meter writer yields to a fresh foreign writer', () => {
    expect(shouldWriteMeterFile(null, null, NOW)).toBe(true)
    expect(shouldWriteMeterFile(NOW - 60_000, null, NOW)).toBe(false)
    expect(shouldWriteMeterFile(NOW - 60_000, NOW - 60_000, NOW)).toBe(true)
    expect(shouldWriteMeterFile(NOW - 20 * 60_000, null, NOW)).toBe(true)
  })
  test('the meter file is the fallback reading where no measure event arrives', () => {
    const text = JSON.stringify({ written_at: Math.floor((NOW - 60_000) / 1000), five_hour: { used_percentage: 4, resets_at: 1 }, seven_day: { used_percentage: 50, resets_at: Math.floor((NOW + 3.5 * DAY) / 1000) }, context_used_percentage: 38 })
    const live = liveFromMeterFile(text)
    expect(statusText(live, NOW)).toBe('5h 4% · wk 50% · pace 48 +3 · ctx 38% · from meter file')
    expect(statusText(live, NOW + 20 * 60_000)).toMatch(/^meters stale/)
    expect(liveFromMeterFile(null)).toBe(null)
    expect(liveFromMeterFile('{bad')).toBe(null)
    expect(liveFromMeterFile('{"context_used_percentage": 3}')).toBe(null)
  })
  test('the meter file pacewright reads', () => {
    const f = meterFile([{ kind: 'seven_day', percentUsed: 41, resetsAt: new Date(NOW + DAY).toISOString() }], 30, 'm', NOW)
    expect(f?.seven_day).toEqual({ used_percentage: 41, resets_at: Math.floor((NOW + DAY) / 1000) })
    expect(meterFile([], null, null, NOW)).toBe(null)
  })
})

describe('tasks (F3, F3f) and PRs (X5)', () => {
  test('the headline leads with what runs', () => {
    const t = (id: string, state: 'running' | 'failed') => ({ id, state, kind: 'agent', label: id, startedAt: NOW }) as never
    expect(tasksHeadline([t('a', 'running'), t('b', 'failed')], 'run r: 1 done')).toBe('Tasks: 1 running · 1 failed · run r: 1 done')
    expect(tasksHeadline([], null)).toBe('Tasks: 0 running')
  })
  test('the same task across runs shares a signature; est_wall forms; estimates', () => {
    expect(taskSignature('bash', 'npm test -- --shard 1/4')).toBe(taskSignature('bash', 'npm test -- --shard 3/4'))
    expect(parseEstWall('1h30m')).toBe(5_400_000)
    expect(parseEstWall('soon')).toBe(null)
    let h = {}
    for (const ms of [60_000, 120_000, 90_000]) h = recordDuration(h, 'bash:x', ms)
    expect(estimateFor('bash:x', h, 300_000, 600_000)).toEqual({ ms: 300_000, source: 'ledger' })
    expect(estimateFor('bash:x', h, null, 600_000)).toEqual({ ms: 90_000, source: 'history' })
    expect(estimateFor('bash:y', h, null, undefined)).toBe(null)
  })
  test('taskHistory keys carry no command text (counts only, never text)', () => {
    const cmd = 'curl -H Authorization ghpLeakyTokenWord deploy prod'
    const sig = taskSignature('bash', cmd)
    expect(sig).toMatch(/^bash:[0-9a-f]{8}$/)
    for (const w of ['curl', 'authorization', 'ghpleakytokenword', 'deploy', 'prod']) expect(sig.toLowerCase()).not.toContain(w)
    expect(taskSignature('agent', 'Review the private notes')).toMatch(/^agent:[0-9a-f]{8}$/)
    let h = recordDuration({}, sig, 60_000)
    for (const key of Object.keys(h)) expect(key).toMatch(/^[a-z]+:[0-9a-f]{8}$/)
    // A store written by an older build may hold text keys: read drops them and keeps hash keys.
    const legacy = { 'bash:curl -h authorization ghpleakytokenword': [1000, 2000], [sig]: [3000, 'x'], junk: 5 } as unknown
    h = sanitizeTaskHistory(legacy)
    expect(Object.keys(h)).toEqual([sig])
    expect(h[sig]).toEqual([3000])
    expect(sanitizeTaskHistory(null)).toEqual({})
    expect(JSON.stringify(h)).not.toMatch(/curl|authorization|leaky/i)
  })
  test('taskHistory holds at most 200 keys, most recent kept', () => {
    let h = {}
    for (let i = 0; i < 205; i++) h = recordDuration(h, taskSignature('bash', `job${'x'.repeat(i)}`), 1000)
    const keys = Object.keys(h)
    expect(keys.length).toBe(200)
    expect(keys[keys.length - 1]).toBe(taskSignature('bash', `job${'x'.repeat(204)}`))
    expect(keys).not.toContain(taskSignature('bash', 'job'))
  })
  test('status lines say what, how long, what is left, and a quiet stretch', () => {
    const t = { id: 'b1', kind: 'bash', label: 'run the suite', group: 'main', startedAt: NOW - 10 * 60_000, state: 'running', detail: 'npm test' }
    const text = taskStatusLines(t, NOW, { ms: 15 * 60_000, source: 'history' }, { lastLine: 'PASS a.test.ts', idleMs: 6 * 60_000, bytes: 10 }).join(NL)
    expect(text).toMatch(/about 5m left of 15m \(from earlier runs\)/)
    expect(text).toMatch(/no new output for 6m/)
    expect(lastLineOf('a\nb\n\n')).toBe('b')
  })
  test('ledger statuses count under their leading word', () => {
    expect(statusWord('complete — findings folded in')).toBe('complete')
    expect(summariseLedger('r1', [{ unit: 'U1', status: 'pushed' }, { unit: 'U2', status: 'complete — a' }] as never).line).toBe('run r1: 1 pushed · 1 complete')
  })
  test('PRs refresh on a push or a gh pr action, and parse checks, review and conflict', () => {
    expect(changesPrs('git push -u origin main')).toBe(true)
    expect(changesPrs('gh pr list')).toBe(false)
    const rows = parsePrList(JSON.stringify([{ number: 7, title: 't', state: 'OPEN', statusCheckRollup: [{ conclusion: 'FAILURE' }], reviewDecision: 'REVIEW_REQUIRED', mergeStateStatus: 'DIRTY' }]))
    expect(prLine(rows)).toBe('#7 red, review required, conflict')
    expect(prChanges(rows, rows.map(r => ({ ...r, checks: 'green' })))).toEqual(['#7 checks red → green'])
  })
})

describe('panels: research (S4), GPU (L1), Godot (G1), pins (C14), doctor (C5)', () => {
  test('palette: named, then scoped, then ask', () => {
    const rows = parseRoster('| slug | scope |\n|---|---|\n| acme | site-repo, docs/ |\n| beta | other-repo |\n')
    expect(resolveBrand(rows, 'beta', 'x', '')).toEqual({ slug: 'beta', how: 'named' })
    expect(resolveBrand(rows, null, 'site-repo', '')).toEqual({ slug: 'acme', how: 'scoped' })
    expect(resolveBrand(rows, null, 'nowhere', '')).toEqual({ slug: null, how: 'ask' })
    expect(paletteTokens('| `primary` | #112233 |\n| text | none |')).toEqual([{ token: 'primary', hex: '#112233' }])
    expect(RESEARCH_SKILL.test('revenantworks-scribe-researchscribe')).toBe(true)
  })
  test('lease path, parse and lines', () => {
    expect(leasePath(false, { HOME: '/h' })).toBe('/h/.local/state/localops/gpu-lease.json')
    const lease = parseLease(JSON.stringify({ holder: 'lmstudiorunner', purpose: 'draft', expires: new Date(NOW + 3 * 60_000).toISOString(), instance_ids: ['a'] }))
    const r = { comfy: comfyFrom('{"devices":[{"vram_free":1073741824,"vram_total":8589934592}]}', '{"queue_running":[1],"queue_pending":[]}'), lms: lmsFrom('{"data":[{"id":"m","loaded_instances":[{"id":"m:1"}]}]}'), ollama: ollamaFrom('{"models":[]}'), at: NOW - 5000 }
    const lines = leaseLines(lease, r, NOW).join(NL)
    expect(lines).toMatch(/lmstudiorunner · draft · 3 min left/)
    expect(lines).toMatch(/two consumers on one card/)
    expect(parseLease('{')).toBe('unreadable')
  })
  test('Godot: passed only when measured, whole and above the floor; the floor only rises', () => {
    const WORKFLOW = ['        run: |', '          set -o pipefail', '          godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit 2>&1 | tee gut.log', "          grep -E '^\\s*Scripts\\s+43\\s*$' gut.log", '          TESTS_FLOOR=411', ''].join(NL)
    const LOG = ['Scripts 43', 'Tests 415', 'Passing Tests 415', 'Failing Tests 0'].map(l => `  ${l}`).join(NL)
    const ci = ciFacts(WORKFLOW)
    expect(ci.floor).toBe(411)
    expect(godotRun('godot --headless -s addons/gut/gut_cmdln.gd -gselect=test_a.gd', 'sh').whole).toBe(false)
    expect(countsAsProof('godot -s x || true')).toBe(false)
    expect(judge(true, true, true, gutCounts(LOG), ci, 0).status).toBe('Passed')
    expect(judge(true, true, true, gutCounts('done'), ci, 0).status).toBe('Unknown')
    expect(judge(true, true, true, gutCounts(LOG.replace('415', '400')), ci, 0).status).toBe('Failed')
    expect(junitCounts('<testsuite name="a" tests="3" failures="1" errors="0" skipped="0"></testsuite>')?.failing).toBe(1)
    expect(bandLine(null, 0)).toBe('Godot proof: Not run')
    expect(floorDrop('TESTS_FLOOR=411', 'TESTS_FLOOR=400')).toMatch(/drops from 411 to 400/)
  })
  test('pins and versions', () => {
    expect(pinChanges({ a: '1' }, { a: '2', b: '3' })).toEqual({ changed: ['a'], added: ['b'] })
    expect(versionAtLeast('2.1.290', '2.1.287')).toBe(true)
    expect(versionAtLeast('2.1.250', '2.1.287')).toBe(false)
  })
})
