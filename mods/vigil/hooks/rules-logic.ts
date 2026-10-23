// vigil rule check: pure logic (no $). Read-only. It reads the permission rules out of the settings
// files (permissions.allow, deny and ask; every other field, env included, is dropped on read) and
// tells a suggestion whether a rule already covers its shape. vigil never writes a settings file.
import { progName } from './lib/shell'

export type RuleList = 'allow' | 'deny' | 'ask'
export type RuleScope = 'user' | 'user-local' | 'project' | 'local'

/** One rule as kept: the tool lower-cased, and the text inside its parentheses (null for a bare tool). */
export type Rule = { list: RuleList; tool: string; pattern: string | null; scope: RuleScope }

const LISTS: readonly RuleList[] = ['allow', 'deny', 'ask']
/** A settings file holds at most this many rules per list that vigil keeps; the rest are ignored. */
const MAX_RULES = 500
const SHELL_TOOLS = new Set(['bash', 'powershell'])

/** The settings files Claude Code merges, in the order vigil names them. The project pair needs a root. */
export const settingsPaths = (home: string, root: string): Array<[RuleScope, string]> => [
  ['user', `${home}/.claude/settings.json`],
  ['user-local', `${home}/.claude/settings.local.json`],
  ...(root ? ([['project', `${root}/.claude/settings.json`], ['local', `${root}/.claude/settings.local.json`]] as Array<[RuleScope, string]>) : []),
]

/** `Tool` or `Tool(pattern)`; null for anything else. */
const parseRule = (raw: string): { tool: string; pattern: string | null } | null => {
  const m = /^([A-Za-z][\w-]{0,80})(?:\((.*)\))?$/s.exec(raw.trim())
  return m ? { tool: m[1]!.toLowerCase(), pattern: m[2] === undefined ? null : m[2] } : null
}

/** The rules in one settings file's text. A missing or broken file is no rules. */
export const parseRuleFile = (text: string | null, scope: RuleScope): Rule[] => {
  if (!text) return []
  let perms: unknown
  try {
    perms = (JSON.parse(text) as { permissions?: unknown })?.permissions
  } catch {
    return []
  }
  if (!perms || typeof perms !== 'object') return []
  const out: Rule[] = []
  for (const list of LISTS) {
    const xs = (perms as Record<string, unknown>)[list]
    if (!Array.isArray(xs)) continue
    for (const x of xs.slice(0, MAX_RULES)) {
      if (typeof x !== 'string' || x.length > 400) continue
      const r = parseRule(x)
      if (r) out.push({ list, ...r, scope })
    }
  }
  return out
}

/** A shell rule's pattern split into its literal words and the wildcard that ends it. */
const splitPattern = (pattern: string): { words: string[]; tail: string } => {
  const p = pattern.trim()
  const tail = p.endsWith(':*') ? ':*' : p === '*' ? '*' : p.endsWith(' *') ? ' *' : p.endsWith('*') ? '*' : ''
  const body = tail === '*' && p !== '*' ? p.slice(0, -1) : p.slice(0, p.length - tail.length)
  return { words: body.trim() ? body.trim().split(/\s+/) : [], tail }
}

const isFlag = (w: string) => /^--?[A-Za-z][\w-]*$/.test(w)

/** One rule against one shape segment: sure, maybe, or no match; `shown` is the words it matched on. */
const matchSegment = (seg: string, pattern: string): { hit: 'sure' | 'maybe' | null; shown: string[]; whole: boolean } => {
  const { words, tail } = splitPattern(pattern)
  const wild = tail !== ''
  if (words.length === 0) return { hit: wild ? 'sure' : null, shown: [], whole: true }
  const w = seg.split(' ')
  const prog = w[0] ?? ''
  if (progName(words[0]!) !== prog) return { hit: null, shown: [], whole: false }
  // The shape keeps the program, a subcommand or module word, a script suffix, then sorted flags.
  const kept = w.slice(1).filter(x => !isFlag(x))
  const flags = new Set(w.slice(1).filter(isFlag))
  const shown = [prog]
  let sure = true
  let k = 0
  for (const word of words.slice(1)) {
    if (word.includes('*')) {
      sure = false
      break
    }
    if (isFlag(word)) {
      if (!flags.has(word)) return { hit: null, shown, whole: false }
      sure = false   // the flag is there, but the shape lost where it stood
      shown.push(word)
      continue
    }
    const want = kept[k]
    if (want === undefined || want.startsWith('*.')) {
      sure = false   // a word the shape dropped (a path, a value): only a maybe
      break
    }
    if (want !== word) return { hit: null, shown, whole: false }
    shown.push(word)
    k += 1
  }
  const whole = shown.length === words.length
  return { hit: sure && wild && whole ? 'sure' : 'maybe', shown, whole }
}

export type SegmentCheck = { seg: string; list: RuleList | null; sure: boolean; scope?: RuleScope; rule?: string }
export type Verdict = 'allowed' | 'denied' | 'ask' | 'maybe' | 'partial' | 'none'
export type RuleCheck = { verdict: Verdict; segments: SegmentCheck[] }

const RANK: Record<RuleList, number> = { deny: 0, ask: 1, allow: 2 }

/** A rule as vigil prints it: only the words it matched on the shape, never the rest of its text. */
const display = (tool: string, shown: string[], whole: boolean, tail: string): string => {
  const name = tool === 'powershell' ? 'PowerShell' : tool.startsWith('mcp__') ? tool : tool.charAt(0).toUpperCase() + tool.slice(1)
  if (shown.length === 0 && whole && tail === '') return name
  return `${name}(${[...shown, ...(whole ? [] : ['…'])].join(' ')}${whole ? tail : ''})`
}

/** The best rule for one segment: deny over ask over allow, a sure match over a maybe in the same list. */
const checkSegment = (seg: string, tools: ReadonlySet<string>, rules: readonly Rule[], mcp: string | null): SegmentCheck => {
  let best: SegmentCheck = { seg, list: null, sure: false }
  const better = (c: SegmentCheck) =>
    best.list === null || RANK[c.list!] < RANK[best.list] || (RANK[c.list!] === RANK[best.list] && c.sure && !best.sure)
  for (const r of rules) {
    let hit: 'sure' | 'maybe' | null = null
    let rule = ''
    if (mcp !== null) {
      // mcp__srv covers the server; mcp__srv__* too; mcp__srv__tool one tool.
      const t = r.tool
      if (r.pattern === null && (t === mcp || mcp.startsWith(`${t}__`) || (t.endsWith('__') && mcp.startsWith(t)))) hit = 'sure'
      if (r.pattern === '*' && mcp.startsWith(`${t}__`)) hit = 'sure'
      rule = /^mcp__[\w-]+$/.test(t) ? t : 'mcp…'
    } else if (tools.has(r.tool)) {
      if (r.pattern === null) {
        hit = 'sure'
        rule = display(r.tool, [], true, '')
      } else if (SHELL_TOOLS.has(r.tool)) {
        const m = matchSegment(seg, r.pattern)
        hit = m.hit
        rule = display(r.tool, m.shown, m.whole, splitPattern(r.pattern).tail)
      } else {
        hit = r.pattern.trim() === '*' || r.pattern.trim() === '**' ? 'sure' : 'maybe'
        rule = display(r.tool, [], false, '')
      }
    }
    if (!hit) continue
    const c: SegmentCheck = { seg, list: r.list, sure: hit === 'sure', scope: r.scope, rule }
    if (better(c)) best = c
  }
  return best
}

/**
 * Whether a rule already covers a suggestion's shape. Null for rows that are not tool shapes
 * (skills, context). A run row (`command:`) is checked against both shell tools.
 */
export const ruleCheck = (key: string, rules: readonly Rule[]): RuleCheck | null => {
  const i = key.indexOf(':')
  const kind = key.slice(0, i)
  const rest = key.slice(i + 1)
  let tools: Set<string>
  let shape: string
  let mcp: string | null = null
  if (kind === 'command') {
    tools = new Set(SHELL_TOOLS)
    shape = rest
  } else if (kind === 'prompt' || kind === 'allow') {
    const [tool, ...words] = rest.split(' ')
    const t = tool ?? ''
    if (SHELL_TOOLS.has(t) && words.length > 0) {
      tools = new Set([t])
      shape = words.join(' ')
    } else if (t.startsWith('mcp__')) {
      tools = new Set()
      mcp = t
      shape = t
    } else {
      tools = new Set([t])
      shape = rest
    }
  } else return null
  const shellish = mcp === null && [...tools].every(t => SHELL_TOOLS.has(t))
  const segs = shellish ? shape.split(' ; ') : [shape]
  const segments = segs.map(seg => checkSegment(seg.trim(), tools, rules, mcp))
  const sureIn = (l: RuleList) => segments.some(s => s.list === l && s.sure)
  let verdict: Verdict
  if (sureIn('deny')) verdict = 'denied'
  else if (sureIn('ask')) verdict = 'ask'
  else if (segments.every(s => s.list === null)) verdict = 'none'
  else if (segments.some(s => s.list === null)) verdict = 'partial'
  else if (segments.every(s => s.list === 'allow' && s.sure)) verdict = 'allowed'
  else verdict = 'maybe'
  return { verdict, segments }
}

/** One line for the drill-in. It names a rule by the words it matched, never its full text. */
export const ruleSummary = (c: RuleCheck): string => {
  if (c.verdict === 'none') return 'rule: none in user, project or local settings'
  const named = (s: SegmentCheck) => `${s.rule} [${s.scope}]`
  if (c.verdict === 'allowed') return `rule: allowed by ${[...new Set(c.segments.map(named))].join('; ')}`
  if (c.segments.length === 1 && c.segments[0]!.sure) {
    const s = c.segments[0]!
    return `rule: ${s.list === 'deny' ? 'denied' : 'asks'} by ${named(s)}`
  }
  return `rule: ${c.segments.map(s => (s.list === null ? `${s.seg} none` : `${s.seg} ${s.sure ? '' : 'maybe '}${s.list} ${named(s)}`)).join('; ')}`
}
