// Every Revenantworks mod feature (owner 2026-10-08: two plugins, dash and privacy).
// /dash switches lists these, /dash on|off <name> accepts their names, and mods/README.md is
// checked against them. `absorbs` names the 2026-10-06 features each one replaced.
import { KEEPS_RECORDS, NETWORK, OPT_IN, type ModType } from './switches'

export type Plugin = 'dash' | 'privacy'

export type Feature = {
  id: string
  /** The readable name `/dash on|off` accepts. */
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
  // ---- dash: one dashboard ----
  f('D1', 'collector', 'dash', 'feed', 'Counts-only event file and feed.json', ['F5', 'F2', 'C4'], '/dash records on; writes ~/.claude/revenantworks/dash/ (counts, hashes and shapes; never text).'),
  f('D2', 'status-line', 'dash', 'lens', 'Status-line meters: 5-hour, weekly, PACE, context, cache', ['F1', 'F2'], 'The status line, automatic.'),
  f('D3', 'pane', 'dash', 'lens', '/dash pane and its text views', ['F1', 'F2', 'F3', 'F3f', 'F5', 'C4', 'C5', 'C11'], '/dash, /dash skills, /dash health, /dash tasks, /dash doctor.'),
  f('D4', 'read-tool', 'dash', 'assist', 'dash_read: Claude reads the feed on demand', ['C17'], 'Claude calls dash_read when you ask; nothing is injected otherwise.'),
  f('D5', 'suggestions', 'dash', 'assist', 'Suggestion queue (never builds anything)', ['C1'], '/dash suggest; accept, dismiss or snooze <n>. At most one note a session.'),
  f('D6', 'meter-writer', 'dash', 'feed', 'Meter-file fallback writer for pacewright', ['F1b'], '/dash on meter-writer'),
  f('D7', 'ledger-costs', 'dash', 'feed', 'Ledger cost sidecar for dispatchwright', ['F3e'], '/dash on ledger-costs'),
  f('D8', 'instruction-pins', 'dash', 'lens', 'Instruction-file pins', ['C14'], '/dash on instruction-pins; changes show in /dash health.'),
  f('D9', 'research-panel', 'dash', 'lens', 'Research spend and palette panel', ['S4'], 'Shows while researchscribe runs; /dash palette [brand].'),
  f('D10', 'gpu-panel', 'dash', 'lens', 'GPU lease and local model panel', ['L1'], '/dash gpu (reads 127.0.0.1 only, when you ask).'),
  f('D11', 'godot-panel', 'dash', 'lens', 'Godot proof panel and import warning', ['G1'], 'Shows in a Godot repo; /dash godot.'),
  f('D12', 'pr-state', 'dash', 'lens', 'Your open PRs: checks, review, conflicts', ['X5'], '/dash network on (reads GitHub through your gh login, only when you act); /dash prs.'),
  f('D13', 'publish', 'dash', 'assist', 'Snapshot for a private mobile page', [], '/dash publish writes snapshot.json; ask Claude to publish it as a private Artifact.'),
  // ---- privacy: safety that never depends on the dashboard ----
  f('W3', 'secret-redact', 'privacy', 'privacy', 'Secret masking before Claude reads, and restore', ['W3'], 'Automatic; /dash off secret-redact stops it.'),
  f('W3b', 'rotate-alert', 'privacy', 'privacy', 'Rotate tripwire', ['W3b'], 'Automatic, when keywarden lists fingerprints in rotate.txt.'),
  f('L2b', 'stream-mask', 'privacy', 'privacy', 'Stream-secret masking', ['L2b'], 'Automatic.'),
  f('C12', 'untrusted-marker', 'privacy', 'privacy', 'Untrusted-content marker', ['C12'], 'Automatic on web, MCP and mail results.'),
  f('C12b', 'received-marker', 'privacy', 'privacy', 'Received-message marker', ['C12b'], 'Automatic on messages from routines and other sessions.'),
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
