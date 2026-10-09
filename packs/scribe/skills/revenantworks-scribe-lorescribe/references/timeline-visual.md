# Timeline visual — the self-contained chart

Read in `brief` mode when the user wants the timeline drawn. lorescribe writes one HTML file by hand from canon. No script runs to make it, the file loads nothing from the network, and it uses no external library, font or stylesheet. It opens offline in any browser and diffs cleanly in git.

## Contents

- Inputs
- Layout rules
- Template
- Validate before handing it over
- Where it goes

## Inputs

- The rows of `timeline.md` in the user's range (all rows when no range is given).
- The `state` lists of the entities those rows name (`entity-schema.md`), for the lanes.
- Each row's level. A `rumour` row is drawn dashed and labelled "rumour". A `retired` row is left out unless the user asks. A row with a `branch:` key carries the branch id in its label and its table row; trunk rows carry none. Asked for one path, draw trunk rows plus that path's rows only (`canon-levels.md` — Branches).

Nothing that is not in canon is drawn: no inferred dates, no filler events, no generated text.

## Layout rules

- **Axis:** timeline ids in canon order. When the ids carry numbers (`T-0412`), space markers by the number; otherwise space them evenly in row order and say so in the caption.
- **Events:** one marker per row, its label the event text, its `<title>` the row id and the source line.
- **Lanes (optional):** one lane per entity in range, drawn as segments from each `state` change to the next: solid for alive or whole, a short end-cap at death or destruction, nothing after it.
- **Table:** the same rows as a plain HTML table under the drawing. The table is the accessible record and the part a diff reads.
- **Width:** the SVG uses a `viewBox` and `width="100%"`; a long range scrolls sideways inside its own box, never the page.
- **Colour:** neutral greys and one accent, defined once as CSS variables, with a dark-mode set under `prefers-color-scheme`. No brand palette.

## Template

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><world> timeline</title>
<style>
  :root { --bg:#ffffff; --ink:#1f1f1f; --muted:#6b6b6b; --line:#c8c8c8; --accent:#2f6f8f; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#161616; --ink:#ececec; --muted:#a0a0a0; --line:#3a3a3a; --accent:#7fb7d4; }
  }
  body { margin:0; padding:16px; background:var(--bg); color:var(--ink);
         font:15px/1.5 system-ui, sans-serif; }
  .scroll { overflow-x:auto; }
  svg text { fill:var(--ink); font-size:12px; }
  .axis { stroke:var(--line); stroke-width:2; }
  .event { fill:var(--accent); }
  .rumour { fill:none; stroke:var(--accent); stroke-dasharray:3 3; }
  .lane { stroke:var(--muted); stroke-width:4; }
  table { border-collapse:collapse; margin-top:16px; width:100%; }
  th, td { border-bottom:1px solid var(--line); padding:4px 8px; text-align:left; }
</style>
</head>
<body>
<h1><world> timeline</h1>
<p>Canon <version>, rows <first id> to <last id>. Drawn from timeline.md; <spacing note>.</p>
<div class="scroll">
<svg viewBox="0 0 <w> <h>" width="100%" role="img" aria-labelledby="cap">
  <title id="cap"><world> timeline, <n> events</title>
  <line class="axis" x1="<x0>" y1="<y>" x2="<x1>" y2="<y>"/>
  <g><circle class="event" cx="<x>" cy="<y>" r="6"><title><row id> · <source></title></circle>
     <text x="<x>" y="<y - 14>" text-anchor="middle"><row id> <event></text></g>
  <!-- one <g> per row; rumour rows use class="rumour" -->
  <!-- optional lanes: <line class="lane" x1=.. x2=.. y1=.. y2=..><title><entity id> · <state></title></line> -->
</svg>
</div>
<table>
  <thead><tr><th>at</th><th>event</th><th>entities</th><th>level</th></tr></thead>
  <tbody>
    <tr><td><row id></td><td><event></td><td><ids></td><td><level></td></tr>
  </tbody>
</table>
</body>
</html>
```

Fill every angle bracket from canon. Keep the template's structure; add rows, not features.

## Validate before handing it over

1. Every row in range appears exactly once in the table and once in the drawing; count both and state the counts.
2. The file contains no `http`, no `src=`, no `<script` and no `@import`: nothing loads from outside, and nothing runs. Report this check in those plain words; never quote the banned tokens in the reply, so a text scan of the whole reply stays clean.
3. Every label matches its canon row word for word.

A failed check is fixed and re-run before the file is offered.

## Where it goes

The chart is an output, not canon. It is offered as a PROPOSAL for a path the user names, by default `generated/timeline-<range>.html` beside the bible, never inside a canon kind folder and never in a folder handed over read-only. On the user's yes it is written and read back. Without file tools, the whole file goes back in chat as one fenced block.
