import { describe, expect, test } from 'claude-code/testing'

import { DAY, rollup, sessionKey, type DashEvent } from '../hooks/collector-logic'
import { parseRuleFile, ruleCheck, ruleSummary, settingsPaths, type Rule } from '../hooks/rules-logic'
import { candidates, mergeSuggestions } from '../hooks/suggest-logic'
import { linesText, suggestLines } from '../hooks/view-logic'

const file = (perms: Record<string, unknown>, extra: Record<string, unknown> = {}) => JSON.stringify({ ...extra, permissions: perms })
const rules = (scope: Parameters<typeof parseRuleFile>[1], perms: Record<string, unknown>) => parseRuleFile(file(perms), scope)

describe('the settings reader keeps rules only', () => {
  test('allow, deny and ask strings come through with their scope; env and every other field are dropped', () => {
    const text = file({ allow: ['Bash(git push:*)', 7, 'Read'], deny: ['Bash(rm:*)'], ask: ['WebFetch'], defaultMode: 'auto' }, { env: { API_TOKEN: 'sk-live-0123456789abcdef' }, apiKeyHelper: 'secret-helper' })
    const got = parseRuleFile(text, 'user')
    expect(got.map(r => [r.list, r.tool, r.pattern, r.scope])).toEqual([
      ['allow', 'bash', 'git push:*', 'user'], ['allow', 'read', null, 'user'], ['deny', 'bash', 'rm:*', 'user'], ['ask', 'webfetch', null, 'user'],
    ])
    expect(JSON.stringify(got)).not.toContain('sk-live')
    expect(JSON.stringify(got)).not.toContain('secret-helper')
  })
  test('junk, a missing file and a file with no permissions read as no rules', () => {
    expect(parseRuleFile(null, 'project')).toEqual([])
    expect(parseRuleFile('{not json', 'project')).toEqual([])
    expect(parseRuleFile('{"env":{"X":"1"}}', 'project')).toEqual([])
    expect(parseRuleFile('{"permissions":{"allow":"Bash"}}', 'project')).toEqual([])
  })
  test('the four files: user, user-local, project, local; the project pair only with a root', () => {
    expect(settingsPaths('/h', '/r')).toEqual([['user', '/h/.claude/settings.json'], ['user-local', '/h/.claude/settings.local.json'], ['project', '/r/.claude/settings.json'], ['local', '/r/.claude/settings.local.json']])
    expect(settingsPaths('/h', '').map(([s]) => s)).toEqual(['user', 'user-local'])
  })
})

describe('matching a shape against the rules', () => {
  const rs: Rule[] = [
    ...rules('user', { allow: ['Bash(git push:*)', 'Bash(git add *)', 'mcp__srv', 'Agent', 'PowerShell(python:*)', 'Bash(git rm:*)'], deny: ['Bash(git push --force:*)'] }),
    ...rules('local', { allow: ['Bash(npm run build)', 'Write(./docs/**)', 'Bash(git commit -m *)'], ask: ['Bash(docker compose:*)'], deny: ['Bash(git rm:*)'] }),
  ]
  test('a prefix rule covers every command of its shape; a bare tool covers the tool', () => {
    expect(ruleCheck('prompt:bash git push', rs)).toMatchObject({ verdict: 'allowed', segments: [{ seg: 'git push', list: 'allow', sure: true, scope: 'user' }] })
    expect(ruleCheck('prompt:agent', rs)).toMatchObject({ verdict: 'allowed' })
    expect(ruleCheck('prompt:mcp__srv__read', rs)).toMatchObject({ verdict: 'allowed' })
    expect(ruleCheck('prompt:mcp__other__read', rs).verdict).toBe('none')
    expect(ruleCheck('prompt:powershell python *.py', rs).verdict).toBe('allowed')
  })
  test('deny beats allow, ask beats allow', () => {
    expect(ruleCheck('prompt:bash git rm', rs)).toMatchObject({ verdict: 'denied', segments: [{ list: 'deny', scope: 'local' }] })
    // A deny that can only maybe match still outranks a sure allow: the check never over-promises.
    expect(ruleCheck('prompt:bash git push --force', rs)).toMatchObject({ verdict: 'maybe', segments: [{ list: 'deny', sure: false }] })
    expect(ruleCheck('prompt:bash docker compose', rs).verdict).toBe('ask')
  })
  test('a compound shape is allowed only when every segment is', () => {
    expect(ruleCheck('prompt:bash git add ; git push', rs).verdict).toBe('allowed')
    const part = ruleCheck('prompt:bash cd ; git push', rs)
    expect(part.verdict).toBe('partial')
    expect(part.segments.map(s => [s.seg, s.list])).toEqual([['cd', null], ['git push', 'allow']])
  })
  test('a rule naming words the shape dropped can only maybe match', () => {
    expect(ruleCheck('prompt:bash npm run', rs)).toMatchObject({ verdict: 'maybe', segments: [{ list: 'allow', sure: false }] })
    expect(ruleCheck('prompt:bash git commit -m', rs).verdict).toBe('maybe')
    expect(ruleCheck('prompt:write *.md', rs).verdict).toBe('maybe')
    expect(ruleCheck('prompt:bash git commit', rs).verdict).toBe('none')
  })
  test('a command row checks both shells', () => {
    expect(ruleCheck('command:git push', rs).verdict).toBe('allowed')
    expect(ruleCheck('command:python *.py', rs).verdict).toBe('allowed')
  })
  test('rows that are not tool shapes have no rule check', () => {
    expect(ruleCheck('unused:quiet', rs)).toBe(null)
    expect(ruleCheck('slim:context', rs)).toBe(null)
  })
  test('the summary names the rule by its safe words only, never a quoted value', () => {
    const leak = rules('project', { allow: ['Bash(curl -H "Authorization: Bearer abc123SECRETxyz" https://x:*)'] })
    const line = ruleSummary(ruleCheck('prompt:bash curl -H', leak)!)
    expect(line).toMatch(/maybe/)
    expect(line).not.toContain('SECRET')
    expect(line).not.toContain('Bearer')
    expect(ruleSummary(ruleCheck('prompt:bash git push', rs)!)).toBe('rule: allowed by Bash(git push:*) [user]')
    expect(ruleSummary(ruleCheck('prompt:bash cd ; git push', rs)!)).toBe('rule: cd none; git push allow Bash(git push:*) [user]')
    expect(ruleSummary(ruleCheck('prompt:bash make test', rs)!)).toBe('rule: none in user, project or local settings')
  })
})

describe('the drill-in shows the rule check', () => {
  const NOW = Date.UTC(2026, 9, 16, 12)
  const perm = (shape: string, n: number): DashEvent[] => Array.from({ length: n }, (_, i) => ({ t: NOW - DAY - i, s: sessionKey(`s${i % 3}`), k: 'prompt', shape }) as DashEvent)
  const evs = [...perm('bash git push', 9), ...perm('bash git fetch', 4)]
  const rows = mergeSuggestions([], candidates(evs, rollup(evs, { now: NOW, recording: true }), NOW), NOW)
  const rs = rules('user', { allow: ['Bash(git push:*)'] })
  test('each shape carries its rule line; an already-allowed shape says so instead of asking for a rule', () => {
    const drill = linesText(suggestLines(rows, undefined, 'git', rs))
    expect(drill).toContain('rule: allowed by Bash(git push:*) [user]')
    expect(drill).toContain('rule: none in user, project or local settings')
    expect(drill).toMatch(/already allowed/)
  })
  test('with no rules passed the view is unchanged', () => {
    expect(linesText(suggestLines(rows, undefined, 'git'))).not.toContain('rule:')
  })
})
