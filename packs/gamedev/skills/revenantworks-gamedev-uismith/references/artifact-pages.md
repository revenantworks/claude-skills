# Artifact pages: the theme and phone pass

Load when the surface is a published artifact page (a claude.ai page, often rebuilt by a routine) and the job is themes, phone fit or a polish pass. Built from a 2026-11-11 pass over 17 live pages. Everything here sits under the five laws; nothing here defines a palette.

## Order of work

1. Purpose first. One sentence: what the page is for, who reads it, when, on what device. Research the best practice for that kind of page (briefing, scoring sheet, review page, dashboard). Cut layout and data that do not serve that use before styling anything. A page that already fits its use gets no cuts; say so.
2. Find the source. A routine-built page is fixed in its renderer, template or prompt in the repo, never only in the published copy: the next run overwrites it. A page with no source in any repo (published straight from a session, or a Claude Docs document) is reported, not restyled. A page rendered by someone else's skill is out of reach; say whose.
3. Diff the live page against the repo before republishing. The host wraps the page in its own skeleton (doctype, charset, viewport, a reset style); strip those lines before comparing. A live page that differs from the repo's previous version is a finding to resolve before publishing over it.

## Themes

- Palettes come only from the page's own brand definition (light, dark, high-contrast and its light twin where documented). A palette from another brand fails that brand's colour test and any hex scan of rendered pages; where such a gate exists, offer fewer palettes rather than relax it.
- One kit, never a hand-rolled switch. Where the user keeps a shared kit (one canonical copy, a byte-identical copy in each repo that builds pages), every page uses it: palettes are data in the page's own token names (a `ck-spec` block, or `render()` in a generator), `cardkit.py build` fills marker blocks, `cardkit.py check` fails CI on a stale page, and a test pins the copy's sha256. Five hand-rolled systems across 17 pages were replaced by it on 2026-11-11.
- The kit owns its own attributes (`data-ck-mode`, `data-ck-pal`) and never writes the host's `data-theme`; plain CSS resolves Auto (host, else device), and forced modes carry `:not(#ck)` so they outrank every Auto rule. No watcher exists to loop.
- A brand-owned default stays native: its Auto look stays in the brand CSS its tests measure, and the kit adds only the forced rules.
- Token-ise before theming. Colour constants baked into CSS, SVG attributes (fill and stroke accept var()) and inline styles become var(--token) first; tests that counted hex values move to counting tokens, never get deleted.
- Auto, Light, Dark. Auto follows the host's data-theme when it sets one, else prefers-color-scheme. A forced mode holds when the host rewrites the attribute.
- With no kit at hand, never write the host's attribute. If a page must, its watcher ignores its own writes: MutationObserver records arrive after any synchronous flag is reset, so a "self" flag loops forever under a forced mode. Keep the value last written (want); a record whose value equals it is your own.
- A page that must do more than recolour (swap a brand font) listens for the kit's `ck:change` event instead of growing its own switch.
- New controls get their own class. Existing handlers on shared classes (".seg button" read as a taster pick) capture new buttons silently; the probe catches this only if it checks the page's own state after clicking.
- Pages that must stay script-free (a shared or public variant with a no-script test) keep their static form; the theme switch goes on the private page only. Narrow a no-script test to "no script except the theme panel's" only when the test's purpose was something else (pure-CSS tabs), and say so in the commit.
- Red words on cards. A signal colour that clears 4.5:1 only on the page ground sits on a ground-coloured chip or row when it appears on a card.

## Probe additions

The probe in probe.md covers fit. For a theme pass, also measure, per palette and mode:

- every visible text element against its nearest opaque ancestor (alpha above 0.5): 4.5:1 for text; symbols that act as graphics hold 3:1;
- every button, select, summary, text input and form label at least 44 px tall; inline links and terms inside running text are exempt;
- the theme switch: a forced mode holds after a host write; Auto returns to the host value; the stored value survives a reload.

## Probe traps

- Transitions. A colour read right after a theme switch can be mid-transition and fail falsely. Inject a style that turns transitions off on every element before measuring, or re-read.
- Hidden pane. A hidden browser pane throttles timers; a probe that awaits setTimeout hangs. Use microtask awaits or synchronous reads.
- Local copies. A saved artifact page previewed locally needs the host skeleton (charset and viewport meta), or it renders at desktop width with mojibake.
- Side effects. A renderer's build() may write the committed report as well as return HTML; revert that file and let the routine regenerate it.
- Shell traps. PowerShell variable names are case-insensitive ($S overwrites $s); stray __pycache__ folders from compileall can break manifest tests.
- Load-sensitive tests. A timing test that fails while another suite loads the machine is re-run on an idle machine; a second failure there is red.

## Researched adds and rejects (2026-11-11)

Vetted against MDN, web.dev, WAI-ARIA APG, GOV.UK and Nielsen Norman Group for tiny, phone-first, single-file pages.

Adopt:
- In the kit: `text-wrap: balance` on headings; a `forced-colors` outline (`Highlight`) on the selected mode and tab; `scroll-margin-top` so hash jumps clear a sticky bar; tabs print every section and take arrow, Home and End keys.
- Per page: a `role="status"` live region present at load (change only its text); a freshness stamp (`<time>` plus `Intl.RelativeTimeFormat`, marked stale past the page's cadence); `Intl.NumberFormat` with `signDisplay: "exceptZero"` for money and P/L; `lang` and one `<main>`; no loading indicator for loads under about 1 s (delay it 800 ms).
- Downloads inside claude.ai go through the `downloads` capability; a plain `<a download>` or blob link does nothing there.

Reject:
- `content-visibility: auto` (pages too small; hidden tabs already skip paint); `prefers-reduced-data` (no browser support); web-font loading tricks (use system or embedded fonts); `100dvh` layouts (lags the toolbar; use `svh` or none); a separate design for forced colours (let the user's palette win); `role="alert"` for routine updates (interrupts; use `status`); more than five bottom tabs; service workers (host iframe, no origin control).
- Tabs that switch panels in one page may stay buttons in a `nav` with `aria-current`; if a tab ever loads another page, it must be a link.