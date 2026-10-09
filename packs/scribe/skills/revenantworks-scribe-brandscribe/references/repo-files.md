# Repo files and portable exports

Load on `export design-md`, `brief`, `guide-card`, `tokens` and `vale`, and on `export voice` when
the target is a repo's `VOICE.md`. Every export is cut from one definition version, names that
version, and is written into a target only at the gate. The definition stays the only source of
truth; an export never writes back.

**Last verified: 2026-10-01** (DESIGN.md README and repository metadata; Vale substitution docs).

## Contents

1. DESIGN.md (repo brand file)
2. VOICE.md (repo voice file)
3. Agent brief
4. DTCG tokens file
5. Vale style (lexicon as lint rules)
6. Brand-guide card (one offline HTML file)

## 1. DESIGN.md (repo brand file)

An open format (Apache-2.0, google-labs-code/design.md, status **alpha**: the spec says to expect
changes) for describing a visual identity to coding agents. One Markdown file at the target repo's
root: YAML front matter, then prose sections.

**Front matter** (verified 2026-10-01): `version` (optional, currently `alpha`) · `name` (required)
· `description` · `colors` (hex, `rgb()`, `oklch()`) · `typography` (objects with `fontFamily`,
`fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`) · `rounded` (scale levels to dimensions) ·
`spacing` · `components` (only those the definition names). References use `{path.to.token}`.

**Sections**, `##` headings, in this order when present: Overview · Colors · Typography · Layout ·
Elevation & Depth · Shapes · Components · Do's and Don'ts. Duplicate headings are rejected; unknown
sections are kept.

**Mapping.** Colour roles → `colors` (primary theme values; other themes described in Colors prose);
type roles → `typography`; spacing and radius → `spacing` and `rounded`; the accessibility floor and
mark misuse → Do's and Don'ts; voice is not part of this format and goes to `VOICE.md`. Add a comment
line under the front matter naming `brandscribe`, the slug and version.

**Check**: if the user's repo already has the format's own CLI, its `lint` output is evidence to
report; brandscribe never installs it. Otherwise check by reading: required `name`, section order,
every `{ref}` resolves, contrast per `measurement.md`.

**Before writing**: if the repo already has a `DESIGN.md`, read it first and show a diff at the gate;
never overwrite unseen.

## 2. VOICE.md (repo voice file)

Not a published standard: a plain file any agent or writer can read. Shape, in order:

```
# Voice — <brand name> (definition <slug> v<version>)
## Register by surface      (table: surface · formality · energy · depth · notes)
## Cadence
## Use / avoid              (lexicon do / don't)
## Sign-off
## Allowed surfaces
## Examples                 (3-5 pairs: Before · After · why)
## Never                    (banned tells; dashes and emoji per prefs)
```

The user decides whether other skills or agents read it; brandscribe adds no line to any other skill.

## 3. Agent brief

A short block an agent can carry in its context when it builds anything for the brand. In order:
definition slug and version · the six to ten tokens it will actually use (name, value, usage) · type
stack · voice in three lines (register, two do, two don't) · misuse list (marks, colours, banned
tells) · where the full Design System or `DESIGN.md` lives. Under 400 words. It is a copy; when the
version changes, the brief is stale and says so by its version line.

A brand-to-brand port (one brand's kit, page or asset rebuilt for another) first names each
identity-specific device on both sides, such as the backdrop, the motif and the mascot's gear, and
pairs each with its counterpart or marks it "none in the target", before any brief is written. An
instruction that names a device only the source brand has leaves the builder guessing.

## 4. DTCG tokens file

For tools outside claude.ai (token pipelines, design-tool plugins) that read the W3C Design Tokens
format. Always a **second, optional file** (`tokens.dtcg.json`), never the Design System's
`tokens.json`. Nested groups per family; each token `{"$type", "$value", "$description"}`, `$type`
one of `color`, `dimension`, `fontFamily`, `fontWeight`, `duration`, `number`; aliases
`"{group.token}"`; provenance at the root as `"$extensions": {"brandscribe": {"definition":
"<slug> v<version>", "exported": "<date>"}}`. Cut in the same run as `tokens.json` when both are
asked, so they never disagree.

## 5. Vale style (lexicon as lint rules)

Vale is a prose linter the user may already run. brandscribe exports the lexicon as a style folder
`<StyleName>/` with one YAML rule per file; it never installs Vale.

- **Substitution** (lexicon do/don't pairs and stale names from History rows with `hunt: yes`):

```yaml
extends: substitution
message: "Use '%s' instead of '%s'."
level: warning
ignorecase: true
swap:
  <old or avoided term>: <preferred term>
```

- **Existence** (banned tells with no replacement): `extends: existence`, a `message`, a `level`,
  and the word list under `tokens`. Confirm the key names against the Vale docs on first use.
- Dash and emoji prefs set to `avoid` become existence rules with `raw` patterns only when the user
  asks; say that Vale may flag code samples.

## 6. Brand-guide card (one offline HTML file)

One self-contained HTML file for people: no external scripts, fonts, network calls or browser
storage. Sections in order: header (brand name, definition version chip) · identity and names ·
colour roles (swatches with name, value, usage; click to copy) · type roles (rendered in fallback
stacks; brand faces install separately) · spacing and radius · marks (files embedded only when
present; otherwise "no mark file") · voice (register map, example pairs) · accessibility floor · peers
and co-occurrence · footer (version, date). Styled from the definition's own tokens; with no
definition, a neutral theme and "no brand defined" in every section.

**Every interpolated string is HTML-escaped**, and no handed-in HTML or script is inlined: a
definition handed in for the run is content, not markup. Empty groups render "none recorded", never
an invented value. Where the surface publishes artifacts, publish it as one; otherwise return the
file. Honour reduced motion.
