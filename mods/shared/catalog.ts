// Every Revenantworks mod feature (owner 2026-10-08: two plugins, vigil and shroud).
// /rw-vigil switches lists these, /rw-vigil on|off <name> accepts their names, and mods/README.md is
// checked against them. `absorbs` names the 2026-10-06 features each one replaced.
import { KEEPS_RECORDS, NETWORK, OPT_IN, type ModType } from './switches'

export type Plugin = 'vigil' | 'shroud'

export type Feature = {
  id: string
  /** The readable name `/rw-vigil on|off` accepts. */
  slug: string
  plugin: Plugin
  type: ModType
  name: string
  /** The retired feature ids this one carries on. */
  absorbs: readonly string[]
  /** How a person uses it: the command, or where it appears. */
  how: string
  default: 'on' | 'opt-in'
  records: boolean
  network: boolean
}

const f = (id: string, slug: string, plugin: Plugin, type: ModType, name: string, absorbs: string[], how: string): Feature => ({
  id, slug, plugin, type, name, absorbs, how,
  default: OPT_IN.has(id) ? 'opt-in' : 'on',
  records: KEEPS_RECORDS.has(id),
  network: NETWORK.has(id),
})

export const CATALOG: readonly Feature[] = [
  // ---- vigil: one dashboard ----
  f('D1', 'collector', 'vigil', 'feed', 'Counts-only event file and feed.json', ['F5', 'F2', 'C4'], '/rw-vigil records on; writes ~/.claude/revenantworks/vigil/ (counts, hashes and shapes; never text).'),
  f('D2', 'status-line', 'vigil', 'lens', 'Status-line meters: 5-hour, weekly, PACE, context, cache', ['F1', 'F2'], 'The status line, automatic.'),
  f('D3', 'pane', 'vigil', 'lens', '/rw-vigil pane and its text views', ['F1', 'F2', 'F3', 'F3f', 'F5', 'C4', 'C5', 'C11'], '/rw-vigil, /rw-vigil skills, /rw-vigil health, /rw-vigil tasks, /rw-vigil doctor.'),
  f('D4', 'read-tool', 'vigil', 'assist', 'vigil_read: Claude reads the feed on demand', ['C17'], 'Claude calls vigil_read when you ask; nothing is injected otherwise.'),
  f('D5', 'suggestions', 'vigil', 'assist', 'Suggestion queue (never builds anything)', ['C1'], '/rw-vigil suggest; accept, dismiss or snooze <n>. At most one note a session.'),
  f('D6', 'meter-writer', 'vigil', 'feed', 'Meter-file fallback writer for pacewright', ['F1b'], '/rw-vigil on meter-writer'),
  f('D7', 'ledger-costs', 'vigil', 'feed', 'Ledger cost sidecar for dispatchwright', ['F3e'], '/rw-vigil on ledger-costs'),
  f('D8', 'instruction-pins', 'vigil', 'lens', 'Instruction-file pins', ['C14'], '/rw-vigil on instruction-pins; changes show in /rw-vigil health.'),
  f('D9', 'research-panel', 'vigil', 'lens', 'Research spend and palette panel', ['S4'], 'Shows while researchscribe runs; /rw-vigil palette [brand].'),
  f('D10', 'gpu-panel', 'vigil', 'lens', 'GPU lease and local model panel', ['L1'], '/rw-vigil gpu (reads 127.0.0.1 only, when you ask).'),
  f('D11', 'godot-panel', 'vigil', 'lens', 'Godot proof panel and import warning', ['G1'], 'Shows in a Godot repo; /rw-vigil godot.'),
  f('D12', 'pr-state', 'vigil', 'lens', 'Your open PRs: checks, review, conflicts', ['X5'], '/rw-vigil network on (reads GitHub through your gh login, only when you act); /rw-vigil prs.'),
  f('D13', 'publish', 'vigil', 'assist', 'Snapshot for a private mobile page', [], '/rw-vigil publish writes snapshot.json; ask Claude to publish it as a private Artifact.'),
  f('D14', 'short-commands', 'vigil', 'assist', 'Short skill commands: /rw-<skill> and /rw <skill>', [], 'On at install. /rw lists them; /rw-vigil off short-commands brings back the long names.'),
  // ---- shroud: safety that never depends on the dashboard ----
  f('W3', 'secret-redact', 'shroud', 'privacy', 'Secret masking before Claude reads, and restore', ['W3'], 'Automatic; /rw-vigil off secret-redact stops it.'),
  f('W3b', 'rotate-alert', 'shroud', 'privacy', 'Rotate tripwire', ['W3b'], 'Automatic, when keywarden lists fingerprints in rotate.txt.'),
  f('L2b', 'stream-mask', 'shroud', 'privacy', 'Stream-secret masking', ['L2b'], 'Automatic.'),
  f('C12', 'untrusted-marker', 'shroud', 'privacy', 'Untrusted-content marker', ['C12'], 'Automatic on web, MCP and mail results.'),
  f('C12b', 'received-marker', 'shroud', 'privacy', 'Received-message marker', ['C12b'], 'Automatic on messages from routines and other sessions.'),
]

/** Features retired 2026-10-08, with nothing carrying them on. */
export const RETIRED: readonly string[] = [
  'C6', 'C10', 'C13', 'F2b', 'F4', 'F4b', 'F4c', 'F6', 'F6b', 'F7', 'X1', 'X2', 'X4', 'W2c', 'W6b', 'W7', 'W8', 'S2b', 'L4',
]

/** A feature by id (`D1`) or readable name (`collector`). */
export const byId = (id: string): Feature | undefined => {
  const t = id.toLowerCase()
  return CATALOG.find(x => x.id.toLowerCase() === t || x.slug === t)
}

export const featuresOf = (plugin: Plugin): Feature[] => CATALOG.filter(x => x.plugin === plugin)
