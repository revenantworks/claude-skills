// vigil drawings: pure logic (no $). Each picture the board shows, two ways: an SVG document for a
// surface that draws `Svg` (desktop, VS Code, phone) and a glyph string for the terminal. One
// renderer feeds every surface, so a tile reads the same everywhere. Colours are hex: a theme
// colour that names a Claude Code theme key is swapped for the neutral hex of the console's ground.
import type { ConsoleBg, Role, Theme } from './theme-logic'

/** Neutral's hex by ground (the house Neutral definition), for a theme key an SVG cannot name. */
export const NEUTRAL_HEX: Record<ConsoleBg, Record<Role | 'text' | 'track', string>> = {
  dark: { accent: '#D97757', ok: '#A3B585', warn: '#D9A441', bad: '#E07A6F', dim: '#B0AEA5', rule: '#33322F', text: '#FAF9F5', track: '#262624' },
  light: { accent: '#A9472A', ok: '#55673B', warn: '#8A5A12', bad: '#B23A30', dim: '#5E5D59', rule: '#E0DDD2', text: '#141413', track: '#E8E6DC' },
}

const HEX = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/

export type Ink = Record<Role | 'text' | 'track', string>

/** The hex every role draws in: the theme's own hex, else neutral's for this ground. */
export const inkOf = (t: Theme, bg: ConsoleBg): Ink => {
  const base = NEUTRAL_HEX[bg]
  const pick = (r: Role) => (HEX.test(t.colors[r]) ? t.colors[r] : base[r])
  return { accent: pick('accent'), ok: pick('ok'), warn: pick('warn'), bad: pick('bad'), dim: pick('dim'), rule: pick('rule'), text: base.text, track: HEX.test(t.colors.rule) ? t.colors.rule : base.track }
}

const clamp = (n: number, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, n))
const r1 = (n: number) => Math.round(n * 10) / 10
/** Text inside the markup: the drawing carries numbers and short labels only, escaped anyway. */
const esc = (s: string) => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)

/** The colour a meter takes at this reading: ok, then warn from 80%, bad from 95%. */
export const meterRole = (pct: number): Role => (pct >= 95 ? 'bad' : pct >= 80 ? 'warn' : 'ok')

/** A point on a circle, 0% at twelve o'clock, clockwise. */
const at = (c: number, r: number, pct: number): [number, number] => {
  const a = (clamp(pct) / 100) * 2 * Math.PI - Math.PI / 2
  return [r1(c + r * Math.cos(a)), r1(c + r * Math.sin(a))]
}

export type RingSpec = { pct: number | null; tick?: number | null; label: string; ink: Ink; size?: number; warnAt?: number }

/**
 * A ring: the track, the used arc in its meter colour, an optional pace tick across the ring, the
 * number in the middle and the label under it. A missing reading draws the track and a dash.
 */
export const ringSvg = (s: RingSpec): string => {
  const size = s.size ?? 64
  const c = size / 2
  const w = Math.max(4, Math.round(size / 10))
  const r = c - w / 2 - 1
  const circ = 2 * Math.PI * r
  const parts = [`<circle cx="${c}" cy="${c}" r="${r1(r)}" fill="none" stroke="${s.ink.track}" stroke-width="${w}"/>`]
  if (s.warnAt !== undefined) {
    // The warn band: a thin arc from warnAt to 100%, under the used arc.
    const len = circ * (1 - clamp(s.warnAt) / 100)
    parts.push(`<circle cx="${c}" cy="${c}" r="${r1(r)}" fill="none" stroke="${s.ink.warn}" stroke-opacity="0.35" stroke-width="${w}" stroke-dasharray="${r1(len)} ${r1(circ)}" stroke-dashoffset="${r1(-circ * (clamp(s.warnAt) / 100))}" transform="rotate(-90 ${c} ${c})"/>`)
  }
  if (s.pct !== null) {
    const p = clamp(s.pct)
    parts.push(`<circle cx="${c}" cy="${c}" r="${r1(r)}" fill="none" stroke="${s.ink[meterRole(p)]}" stroke-width="${w}" stroke-linecap="butt" stroke-dasharray="${r1((circ * p) / 100)} ${r1(circ)}" transform="rotate(-90 ${c} ${c})"/>`)
  }
  if (s.tick !== null && s.tick !== undefined) {
    const [x1, y1] = at(c, r - w, s.tick)
    const [x2, y2] = at(c, r + w / 2 + 1, s.tick)
    parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${s.ink.text}" stroke-width="2"/>`)
  }
  const big = s.pct === null ? '–' : `${Math.round(s.pct)}`
  parts.push(`<text x="${c}" y="${r1(c + size * 0.07)}" text-anchor="middle" font-family="system-ui,sans-serif" font-size="${Math.round(size * 0.24)}" fill="${s.ink.text}">${esc(big)}</text>`)
  const alt = `${s.label} ${s.pct === null ? 'no reading' : `${Math.round(s.pct)}%`}${s.tick !== null && s.tick !== undefined ? `, pace ${Math.round(s.tick)}%` : ''}`
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img"><title>${esc(alt)}</title>${parts.join('')}</svg>`
}

/** A sparkline over the values, the last point marked; flat when every value is equal. */
export const sparkSvg = (values: readonly number[], ink: Ink, w = 120, h = 32, label = 'trend'): string => {
  const xs = values.length ? values : [0]
  const max = Math.max(...xs)
  const min = Math.min(...xs)
  const span = max - min || 1
  const step = xs.length > 1 ? (w - 4) / (xs.length - 1) : 0
  const pts = xs.map((v, i) => [r1(2 + i * step), r1(h - 3 - ((v - min) / span) * (h - 6))] as const)
  const last = pts[pts.length - 1]!
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img"><title>${esc(label)}</title><polyline fill="none" stroke="${ink.accent}" stroke-width="1.5" points="${pts.map(p => p.join(',')).join(' ')}"/><circle cx="${last[0]}" cy="${last[1]}" r="2.5" fill="${ink.accent}"/></svg>`
}

export type Segment = { n: number; role: Role; label: string }

/** One stacked bar: each segment's share of the total, in its role's colour. */
export const barSvg = (segs: readonly Segment[], ink: Ink, w = 120, h = 10): string => {
  const total = segs.reduce((a, s) => a + Math.max(0, s.n), 0)
  let x = 0
  const rects = total === 0
    ? [`<rect x="0" y="0" width="${w}" height="${h}" fill="${ink.track}"/>`]
    : segs.filter(s => s.n > 0).map(s => {
      const width = r1((s.n / total) * w)
      const out = `<rect x="${r1(x)}" y="0" width="${width}" height="${h}" fill="${ink[s.role]}"/>`
      x += width
      return out
    })
  const alt = segs.map(s => `${s.label} ${s.n}`).join(', ')
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img"><title>${esc(alt)}</title>${rects.join('')}</svg>`
}

export type Dot = { ok: boolean | null; label: string }

/** A row of dots, one per check: ok, failing, or not known (hollow). */
export const dotsSvg = (dots: readonly Dot[], ink: Ink, d = 10): string => {
  const gap = 4
  const w = Math.max(d, dots.length * (d + gap) - gap)
  const r = d / 2
  const marks = dots.map((x, i) => {
    const cx = r1(i * (d + gap) + r)
    return x.ok === null
      ? `<circle cx="${cx}" cy="${r}" r="${r - 1}" fill="none" stroke="${ink.dim}" stroke-width="1.5"/>`
      : `<circle cx="${cx}" cy="${r}" r="${r}" fill="${x.ok ? ink.ok : ink.bad}"/>`
  })
  const alt = dots.map(x => `${x.label} ${x.ok === null ? 'unknown' : x.ok ? 'ok' : 'failing'}`).join(', ')
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${d}" viewBox="0 0 ${w} ${d}" role="img"><title>${esc(alt)}</title>${marks.join('')}</svg>`
}

/** A badge: a filled circle with a count, the inbox's picture. */
export const badgeSvg = (n: number, ink: Ink, d = 28): string => {
  const c = d / 2
  const fill = n > 0 ? ink.accent : ink.track
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${d}" height="${d}" viewBox="0 0 ${d} ${d}" role="img"><title>${n} waiting</title><circle cx="${c}" cy="${c}" r="${c}" fill="${fill}"/><text x="${c}" y="${r1(c + d * 0.17)}" text-anchor="middle" font-family="system-ui,sans-serif" font-size="${Math.round(d * 0.46)}" fill="${n > 0 ? '#000000' : ink.dim}">${n > 99 ? '99+' : n}</text></svg>`
}

// ---------- the terminal's glyphs ----------

export type Glyph = { full: string; empty: string }
export const BLOCKS: Glyph = { full: '▰', empty: '▱' }
export const ASCII_BLOCKS: Glyph = { full: '#', empty: '.' }

/** `▰▰▱▱`: the reading in `n` cells, rounded to the nearest cell; a missing one is all empty plus `?`. */
export const glyphMeter = (pct: number | null, n = 4, g: Glyph = BLOCKS): string => {
  if (pct === null) return `${g.empty.repeat(n)}?`
  const on = Math.round((clamp(pct) / 100) * n)
  return g.full.repeat(on) + g.empty.repeat(n - on)
}

const SPARK = '▁▂▃▄▅▆▇█'

/** `▁▃▅█`: one cell per value, scaled to the largest. */
export const glyphSpark = (values: readonly number[]): string => {
  const max = Math.max(0, ...values)
  if (max === 0) return SPARK[0]!.repeat(Math.max(1, values.length))
  return values.map(v => SPARK[Math.min(7, Math.round((Math.max(0, v) / max) * 7))]!).join('')
}

/** `●●○●`: one glyph per check. */
export const glyphDots = (dots: readonly Dot[], on = '●', off = '○', bad = '✗'): string => dots.map(d => (d.ok === null ? off : d.ok ? on : bad)).join('')
