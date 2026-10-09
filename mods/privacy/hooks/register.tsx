// privacy: secrets are masked before Claude reads them, stream secrets too, and outside content
// and received messages are marked as data. Owner 2026-10-08: kept apart from dash so safety never
// depends on the dashboard. Every `$` use lives in this one file; pure logic sits in privacy-logic.ts.
// Nothing here blocks work: it rewrites what Claude reads, and notes it.
import type { EngineInterface, Register } from 'claude-code'

import {
  UNTRUSTED_TOOLS, contentShape, findSecrets, instructionShapedLines, isForeignOrigin, isObsCall, maskBlocks, maskStream,
  maskStrong, parseRotateList, receivedWrap, redact, restore, resultText, rotateFingerprint, untrustedContext,
  type Vault,
} from './privacy-logic'
import { featuresOf } from './lib/catalog'
import { isFeatureOn, parseSwitches, type Switches } from './lib/switches'
import { fnv1a, isWindowsEnv, mapStrings, normPath } from './lib/util'

const PLUGIN = 'privacy'
const VERSION = '1.0.0'

// Module state. A hot reload starts it over; switches come back from disk.
let pvSw: Switches = parseSwitches(null)
let pvInit: Promise<void> | null = null
let pvHome = ''
let pvCwd = ''
let pvRoot = ''
let pvSession = ''
let pvSalt = ''
// W3b compares against keywarden's rotate.txt, so it needs the salt keywarden used (SHIELD_SALT).
let pvShieldSalt = ''
let pvNonce = ''
let pvCaught = 0
let pvRotate = new Set<string>()
let pvNotes: string[] = []
const pvVault: Vault = {}
const pvReadPaths = new Map<string, string>()
const pvObsCalls = new Set<string>()
const pvCounts = { masked: 0, stream: 0, untrusted: 0, received: 0, rotate: 0 }

function pvOn(id: string): boolean {
  return isFeatureOn(pvSw, id)
}

function pvPath(name: string): string {
  return `${pvHome}/.claude/revenantworks/${name}`
}

function pvRel(path: string): string {
  const p = normPath(path)
  const root = normPath(pvRoot || pvCwd).replace(/\/$/, '')
  return p.startsWith(`${root}/`) ? p.slice(root.length + 1) : p
}

async function pvRead($: EngineInterface, path: string): Promise<string | null> {
  try {
    return await $.fs.read(path)
  } catch {
    return null
  }
}

async function pvCanDraw($: EngineInterface): Promise<boolean> {
  const s = await $.session.surfaces()
  return s.includes('terminal') || s.includes('desktop')
}

async function pvSay($: EngineInterface, text: string): Promise<void> {
  if (await pvCanDraw($)) $.ui.toast(text)
  else pvNotes.push(text)
}

/** Health for dash: loaded this session, which features are on, counts only. */
async function pvHeartbeat($: EngineInterface): Promise<void> {
  const on = featuresOf('privacy').filter(x => pvOn(x.id)).map(x => x.id)
  try {
    await $.fs.write(pvPath(`health/${PLUGIN}.json`), JSON.stringify({ plugin: PLUGIN, version: VERSION, session: fnv1a(pvSession), at: await $.clock.now(), on, caught: pvCaught, counts: pvCounts }))
  } catch {
    // Health is observe-only.
  }
}

async function pvLoad($: EngineInterface): Promise<void> {
  pvSw = parseSwitches(await pvRead($, pvPath('switches.json')))
  pvRotate = parseRotateList(await pvRead($, pvPath('rotate.txt')))
}

async function pvEnsure($: EngineInterface): Promise<void> {
  // A failed setup is retried by the next hook instead of being cached for the whole session.
  if (!pvInit) pvInit = pvSetup($).catch(err => { pvInit = null; throw err })
  await pvInit
}

async function pvSetup($: EngineInterface): Promise<void> {
  const win = isWindowsEnv(await $.env.get('OS'))
  pvHome = ((win ? (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) : (await $.env.get('HOME')) ?? (await $.env.get('USERPROFILE'))) ?? '').replace(/\\/g, '/')
  pvSession = await $.session.id()
  pvCwd = (await $.session.cwd()).replace(/\\/g, '/')
  pvRoot = (await $.session.repo())?.root.replace(/\\/g, '/') ?? ''
  pvSalt = fnv1a(`${pvSession}:${await $.clock.now()}:${Math.random()}`)
  pvNonce = fnv1a(`${pvSession}:${await $.clock.now()}`)
  pvShieldSalt = (await $.env.get('SHIELD_SALT')) ?? ''
  await pvLoad($)
  try {
    await $.command.register({ name: 'privacy', description: 'privacy: what was masked or marked this session (counts only)' })
  } catch {
    // A name the host refuses is skipped; setup goes on.
  }
  await pvHeartbeat($)
  $.clock.every(60_000, async () => {
    await pvLoad($)
    await pvHeartbeat($)
  })
}

function pvStatus(): string {
  return [
    'privacy: masks secrets before Claude reads them and marks outside content as data.',
    ...featuresOf('privacy').map(x => `  ${x.slug.padEnd(17)} ${pvOn(x.id) ? 'on ' : 'off'}  ${x.name}`),
    `This session: ${pvCounts.masked} secret(s) masked, ${pvCounts.stream} stream secret(s) masked, ${pvCounts.untrusted} outside result(s) marked, ${pvCounts.received} received message(s) marked, ${pvCounts.rotate} rotate alert(s).`,
    ...(pvRotate.size > 0 && pvShieldSalt === '' ? ['rotate-alert is idle: rotate.txt has fingerprints but SHIELD_SALT is not set, so none can match keywarden\'s.'] : []),
    'Switch with /dash on|off <name>, or edit nothing: the one switch file changes only through /dash.',
  ].join('\n')
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await pvEnsure($)
    return next(e)
  })

  // W3: a secret typed or pasted into a message is replaced before Claude reads it.
  on('prompt.submit', async ($, e, next) => {
    await pvEnsure($)
    if ((e.origin.kind === 'composer' || e.origin.kind === 'bridge') && pvOn('W3')) {
      const r = redact(e.text, pvSalt, pvVault, null)
      if (r.count > 0) {
        pvCounts.masked += r.count
        await pvSay($, `${r.count} secret-shaped value(s) in your message were replaced before Claude read them. Rotate any that were real.`)
        return next({ ...e, text: r.text })
      }
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.call', async ($, e, next) => {
    await pvEnsure($)
    const filePath = typeof (e as { file_path?: unknown }).file_path === 'string' ? (e as { file_path: string }).file_path : null
    const command = typeof (e as { command?: unknown }).command === 'string' ? (e as { command: string }).command : null
    let input = e
    if (e.tool_use_id && isObsCall(JSON.stringify(e))) pvObsCalls.add(e.tool_use_id)
    if (command && e.tool === 'Bash' && pvOn('W3') && /\b(env|printenv)\b|\.env\b/.test(command)) {
      await pvSay($, 'To list variables without values: python -c "import os;print(sorted(os.environ))".')
    }
    // W3: a placeholder goes back to its value only in the gitignored file it was read from.
    if (filePath && pvOn('W3') && (e.tool === 'Edit' || e.tool === 'Write')) {
      const text = e.tool === 'Edit' ? e.old_string + e.new_string : e.content
      if (/\[REDACTED:/.test(text)) {
        let ignored = false
        try {
          ignored = (await $.process.run(['git', 'check-ignore', '-q', filePath], { cwd: pvCwd, timeoutMs: 8000 })).exitCode === 0
        } catch {
          ignored = false
        }
        const note = (n: number) => `${pvRel(filePath)}: ${n} redacted value(s) stay as placeholders; a secret goes back only into the gitignored file it came from.`
        if (e.tool === 'Edit') {
          const a = restore(e.old_string, pvVault, filePath, ignored)
          const b = restore(e.new_string, pvVault, filePath, ignored)
          if (b.refused.length > 0) await pvSay($, note(b.refused.length))
          input = { ...e, old_string: a.text, new_string: b.text }
        } else {
          const b = restore(e.content, pvVault, filePath, ignored)
          if (b.refused.length > 0) await pvSay($, note(b.refused.length))
          input = { ...e, content: b.text }
        }
      }
    }
    if (e.tool === 'Read' && filePath && e.tool_use_id) pvReadPaths.set(e.tool_use_id, filePath)

    const ran = await next(input)

    // C12: outside content is marked as data, with instruction-shaped lines counted.
    if (pvOn('C12') && UNTRUSTED_TOOLS.test(e.tool) && ran.deny === undefined) {
      const count = resultText(ran.result).reduce((n, t) => n + instructionShapedLines(t), 0)
      pvCounts.untrusted += 1
      if (count > 0) await pvSay($, `${e.tool}: ${count} instruction-shaped line(s) in fetched content; treated as data.`)
      return { ...ran, context: [...(ran.context ?? []), untrustedContext(pvNonce, e.tool, count)] }
    }
    return ran
  }).catch(($, e, next) => {
    pvCaught += 1
    pvNotes.push('privacy: a check failed on a tool call this turn; its result may be unmarked or a placeholder unrestored.')
    return next(e)
  })

  // W3, W3b and L2b at the transcript door: tool results, attachments and summaries reach the model masked.
  on('session.append', async ($, e, next) => {
    await pvEnsure($)
    const w3 = pvOn('W3')
    const w3b = pvOn('W3b') && pvRotate.size > 0 && pvShieldSalt !== ''
    const l2b = pvOn('L2b')
    if (!w3 && !w3b && !l2b) return next(e)
    // Content may be a block list or a plain string, by host version and row; anything else passes, said out loud.
    const shape = contentShape(e.message.content)
    if (shape.kind === 'other') {
      pvNotes.push(`privacy: a message arrived with content of an unexpected shape (${shape.type}), so it passed unmasked. Rotate anything secret it held.`)
      return next(e)
    }
    let blocks = shape.blocks
    if (w3b) {
      let hit = ''
      for (const h of findSecrets(JSON.stringify(blocks))) {
        const fp = await rotateFingerprint(pvShieldSalt, h.value)
        if (pvRotate.has(fp)) hit = fp
      }
      if (hit) {
        pvCounts.rotate += 1
        pvNotes.push(`A credential keywarden marked for rotation (fingerprint ${hit}) appeared in the session. Rotate first: keywarden leak.`)
      }
    }
    let masked = 0
    if (w3) {
      const r = maskBlocks(blocks, pvReadPaths, pvSalt, pvVault)
      blocks = r.blocks
      masked = r.count
      pvCounts.masked += r.count
      if (r.count > 0) pvNotes.push(`${r.count} secret-shaped value(s) were masked before Claude read them.`)
    }
    let stream = 0
    if (l2b) {
      // Full masking only on what OBS returned; elsewhere only shapes that are stream secrets anywhere.
      blocks = blocks.map(b => mapStrings(b, s => {
        const r = b.tool_use_id && pvObsCalls.has(b.tool_use_id) ? maskStream(s) : maskStrong(s)
        stream += r.count
        return r.text
      }) as typeof b)
      pvCounts.stream += stream
      if (stream > 0) pvNotes.push(`${stream} stream secret(s) were masked before Claude read them.`)
    }
    if (masked + stream === 0) return next(e)
    return next({ ...e, message: { ...e.message, content: blocks } as typeof e.message })
  }).catch(($, e, next) => {
    // Fail open, but say so: unmasked content may have reached Claude this turn.
    pvCaught += 1
    pvNotes.push('privacy: masking failed this turn, so a result may have reached Claude unmasked. Rotate anything secret it touched.')
    return next(e)
  })

  // C12b: a message from a routine, a sibling session or an agent reaches the model marked as data.
  on('session.receive', async ($, e, next) => {
    await pvEnsure($)
    if (!pvOn('C12b')) return next(e)
    // A wake carrying an external event (a PR comment) holds third-party text, whoever relayed it.
    if (e.event) {
      pvCounts.received += 1
      return next({ ...e, text: receivedWrap(pvNonce, 'an external event (third-party text)', e.text) })
    }
    if (!isForeignOrigin(e.origin.kind)) return next(e)
    pvCounts.received += 1
    return next({ ...e, text: receivedWrap(pvNonce, e.origin.kind, e.text) })
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'privacy' }, async $ => {
    await pvEnsure($)
    return { text: pvStatus() }
  })

  on('turn.complete', async ($, e, next) => {
    await pvEnsure($)
    const res = await next(e)
    if (e.agentId || pvNotes.length === 0) return res
    const notes = [...new Set(pvNotes.splice(0))]
    if (await pvCanDraw($)) {
      for (const n of notes.slice(0, 2)) $.ui.toast(n)
      return res
    }
    return { ...res, text: [res.text, ...notes].filter(Boolean).join('\n') }
  }).catch(($, e, next) => {
    pvCaught += 1
    return next(e)
  })
}
