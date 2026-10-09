// The switch commands, `/dash on|off|records|network|switches` (owner 2026-10-08: C2 shrunk to one
// on/off file). Only the person changes switches: a change asked by anything else is refused.
import { CATALOG, byId } from './catalog'
import { isFeatureOn, isNetworkOn, isRecordingOn, type Switches } from './switches'

export type SwitchResult = { sw: Switches; changed: boolean; text: string }

const stamp = (sw: Switches, now: string): Switches => ({ ...sw, updated: now })

/** Every feature, its plugin and its state, one per line. */
export const switchLines = (sw: Switches): string[] => [
  sw.off ? 'Kill switch ON: every feature is off. /dash on restores your switches.' : 'Revenantworks mods: dash and privacy',
  ...CATALOG.map(x => {
    const state = isFeatureOn(sw, x.id) ? 'on ' : 'off'
    const extra = x.records ? (isRecordingOn(sw, x.id) ? ' (records on)' : ' (records wait for a yes)') : x.network ? (isNetworkOn(sw, x.id) ? ' (network on)' : ' (network waits for a yes)') : ''
    return `  ${x.slug.padEnd(17)} ${state}  ${x.plugin.padEnd(7)} ${x.name}${extra}`
  }),
  'Switch: /dash on|off <name> · kill switch: /dash off · records: /dash records on|off · network: /dash network on|off',
]

/**
 * `args` is what follows `on` or `off` etc. Verbs: `switches`, `on [names]`, `off [names]`,
 * `records on|off`, `network on|off`. Bare `off` is the kill switch; bare `on` lifts it.
 */
export const applySwitchCommand = (sw: Switches, args: string, isOwner: boolean, now: string): SwitchResult => {
  const words = args.trim().split(/\s+/).filter(Boolean)
  const verb = (words[0] ?? 'switches').toLowerCase()
  const rest = words.slice(1).map(w => w.toLowerCase())
  const keep = (text: string): SwitchResult => ({ sw, changed: false, text })
  if (verb === 'switches' || verb === 'list') return keep(switchLines(sw).join('\n'))
  if (!isOwner) return keep('Only you can change a switch, by typing the /dash command yourself.')
  if (verb === 'records' || verb === 'network') {
    const want = rest[0]
    if (want !== 'on' && want !== 'off') return keep(`Usage: /dash ${verb} on|off`)
    const features = { ...sw.features }
    for (const x of CATALOG.filter(c => (verb === 'records' ? c.records : c.network))) features[x.id] = want === 'on'
    const names = CATALOG.filter(c => (verb === 'records' ? c.records : c.network)).map(c => c.slug).join(', ')
    return { sw: stamp({ ...sw, features }, now), changed: true, text: `${verb === 'records' ? 'Local records' : 'Network reads'} ${want}: ${names}.${want === 'off' && verb === 'records' ? ' Files already written stay until /dash purge.' : ''}` }
  }
  if (verb !== 'on' && verb !== 'off') return keep(`Unknown switch command "${verb}". /dash switches lists every feature.`)
  if (rest.length === 0) return { sw: stamp({ ...sw, off: verb === 'off' }, now), changed: true, text: verb === 'off' ? 'Kill switch on: every Revenantworks mod feature is off.' : 'Kill switch off: your switches apply again.' }
  const features = { ...sw.features }
  const done: string[] = []
  const unknown: string[] = []
  for (const name of rest) {
    const x = byId(name)
    if (!x) unknown.push(name)
    else {
      features[x.id] = verb === 'on'
      done.push(x.slug)
    }
  }
  if (done.length === 0) return keep(`No feature named ${unknown.join(', ')}. /dash switches lists them.`)
  return { sw: stamp({ ...sw, features }, now), changed: true, text: `Done: ${done.join(', ')} ${verb}.${unknown.length ? ` Unknown: ${unknown.join(', ')}.` : ''}` }
}
