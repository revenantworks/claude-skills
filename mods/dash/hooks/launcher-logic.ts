// The short commands (owner 2026-10-23, build plan phase 1): every Revenantworks skill answers to
// /rw-<short> and /rw <short>, and its long /<pack>:revenantworks-<pack>-<short> leaves the typeahead.
// The long name stays valid when typed in full, for scripts and for anyone without this mod.
// Tested on the PC 2026-10-23: the hand-off has to leave the command hook first (a $.command.run
// inside the hook the turn waits on is refused), so the hook schedules it on the clock.
import { RW_SKILLS, type RwSkill } from './rw-skills'

export const RW = 'rw'
export const RW_PREFIX = 'rw-'
/** How long the hand-off waits after the /rw- hook returns. */
export const HANDOFF_MS = 50

/** A skill by short name (`agentwright`) or member name (`revenantworks-foundation-agentwright`). */
export const bySkill = (name: string): RwSkill | undefined => {
  const t = name.trim().toLowerCase().replace(/^\/+/, '').replace(/^rw-/, '')
  return RW_SKILLS.find(s => s.short === t || s.member === t)
}

/**
 * The long command to hand off to, from the commands installed now: the pack plugin first, then
 * the featured one-skill plugin, then a bare user-scope skill, then any plugin that carries it.
 */
export const resolveTarget = (s: RwSkill, names: readonly string[]): string | null => {
  const have = new Set(names)
  for (const c of [`${s.pack}:${s.member}`, `${s.short}:${s.member}`, s.member]) if (have.has(c)) return c
  return names.find(n => n.endsWith(`:${s.member}`)) ?? null
}

/** A long Revenantworks skill command, which the typeahead hides while the short ones are on. */
export const isLongName = (command: string): boolean => {
  const m = /(?:^|:)(revenantworks-[a-z]+-[a-z]+)$/.exec(command)
  return m !== null && RW_SKILLS.some(s => s.member === m[1])
}

/** `/rw <skill> <args>`: the first word names the skill, the rest passes through as typed. */
export const parseRw = (args: string): { skill: string; rest: string } => {
  const t = args.trim()
  const i = t.search(/\s/)
  return i < 0 ? { skill: t, rest: '' } : { skill: t.slice(0, i), rest: t.slice(i).trim() }
}

/** Every short command, grouped by pack, for a bare `/rw`. */
export const rwListLines = (): string[] => {
  const out: string[] = ['Revenantworks skills: type /rw-<name>, or /rw <name>, then what you want.']
  let pack = ''
  for (const s of RW_SKILLS) {
    if (s.pack !== pack) {
      pack = s.pack
      out.push('', `  ${pack}`)
    }
    out.push(`    /rw-${s.short.padEnd(15)} ${s.about}`)
  }
  return out
}

/** The one line the typeahead shows for /rw-<short>. */
export const rwDescription = (s: RwSkill): string => `${s.short}: ${s.about}`
