# Store and launch copy: the channel set

> **Last restamped: 2026-10-13** *(event-driven: restamped when a storefront's form or rules visibly change, never on a clock. Field names below are the ones itch.io's project form shows; they were written from that form's known layout and are not re-read live in this build, so check the form in front of you and let it win.)* Declared in `volatile.json`.

Load this file for a store page, a launch or update post, or listing copy (title, short description, tags). It sits under H1 to H9, the fact freeze and the precedence order in the SKILL body, like every profile in `channel-profiles.md`. Store text is public-bound: pre-publish hygiene runs on every draft.

## Contents

- Rules for every store draft
- Field limits: check, never assume
- Store page skeleton
- itch.io first
- Other storefronts
- Launch or update post
- Listing copy: title, short description, tags
- Seams
- Check additions

## Rules for every store draft

1. **Reader first.** The reader is a buyer deciding in seconds. Lead with what the thing is and who it is for, then what they get. The maker's story comes after, if at all.
2. **Facts never move.** Price, contents, counts, formats, versions, licence, platforms and support route come from the facts block. A missing fact goes back as a question. A plausible specific (a tile count, a tested version, a refund policy) is fabrication.
3. **Voice comes from brandscribe.** When a brand exists, read its voice guide (`VOICE.md` or an export) as a voice file. commscribe never invents a brand voice and never edits the guide. No brand: the neutral default.
4. **Honest claims only.** Every feature named is in the build. "Tested on" names what was tested; "works with" needs the requester's word. No "best", "#1", "most popular" or ranking without a source the requester points at. No invented reviews, quotes, ratings, download counts or press lines.
5. **No dark patterns.** No fake urgency (a sale end, countdown or "today only" that is not real), no fake scarcity, no hidden cost moved below the fold, no pre-ticked upsell wording, no confirmshaming ("No thanks, I like ugly games"), no tag stuffing. A request for one gets the honest version and one line saying what changed. A real, dated sale is a fact and stays.

## Field limits: check, never assume

Storefronts change their limits, and many differ per field. **Never state or hard-code a character or tag limit.** Use the limit the requester gives, or one read from the storefront's own form or docs in this session, and treat it as a ceiling. With neither, write short, and flag each limited field in the handback: "check the storefront's current limit for <field>". Never pad up to a limit.

## Store page skeleton

The order a buyer reads. Map each block to the storefront's fields; where the store has no slot, it goes in the page body in this order.

1. **Hook.** One or two sentences: what it is, for whom, and the payoff. A fact, not a tease.
2. **What it is.** The kind of product and what it does, in the product's own terms. One short paragraph.
3. **What you get.** A list of contents with counts, file formats and versions, exactly as the facts block gives them.
4. **Licence and terms.** The licence by its exact name, what a buyer may and may not do in the licence's own words (quote, don't paraphrase legal text), and a link to the full licence. Price model and refund terms only as stated.
5. **Compatibility.** Engines, tools, platforms and versions tested, and requirements. Untested is said, never implied.
6. **Support.** Where to ask, and the update policy only if the requester states one.

Screenshot captions and image alt text follow the same facts: say what the image shows.

## itch.io first

The itch.io project form separates the **title**, a **short description or tagline**, the page **description** (the skeleton above goes here), **genre**, **tags**, pricing and the uploaded **files**. Name each upload plainly by what it contains and its format. Updates go out as **devlog** posts (see Launch or update post). Pricing choices (paid, free, a minimum price, pay what you want) are the requester's facts; commscribe words them, never picks them.

## Other storefronts

Treat any other store generically: list its fields from its form or the requester, map the skeleton onto them, and follow its own content rules, which win over this skeleton's order. Name the store's rules as the requester's to confirm when they are not in front of you. No store-specific limit or rule is assumed.

## Launch or update post

A devlog, store update, or the announcement that carries the release to a channel. The transport profile (Discord, social, email) sets register and mentions; this sets content; the tighter ceiling wins.

- **Headline:** the name and version, plus what shipped, in plain words ("Mossgrove Tiles 1.1: autotile rules added").
- **First paragraph:** what changed for the reader and why it matters to them.
- **Changes:** for an update, Added, Changed, Fixed, breaking changes first and marked, as for release notes.
- **Where and how much:** one link; price or sale only as stated, with its real end date.
- **Known issues** when the facts list them. Never "huge update" or "game-changing" inflation.
- One call to action at most.

## Listing copy: title, short description, tags

- **Title:** the product's name, plus the plain category word a buyer would search when the name does not say it ("Mossgrove Tiles: 16x16 forest tileset"). No keyword stacking.
- **Short description:** one sentence that makes sense alone in a search result or card: what it is and the one fact that sets it apart.
- **Tags:** only true, load-bearing tags, from the storefront's own tag list when it has one, most specific first. No competitor names, no unrelated trending tags.
- **Keywords** come from the requester or a researchscribe result. commscribe never invents search volume or ranking claims.

## Seams

- **brandscribe** owns the brand voice, palette and marks, and a pass or fail of the page against the brand. commscribe writes the words in that voice. Cover and banner art is outside commscribe's scope: it writes no visuals.
- **researchscribe** owns market and competitor research: what similar products charge, which tags sell, whether to launch now. commscribe writes the page from its result.
- The decision on price, licence or launch date is the requester's.

## Check additions

On top of the SKILL body's Check: (1) every claim on the page traces to the facts block; (2) every limited field is within a known limit or flagged "check the current limit"; (3) no line hits rule 5; (4) the hygiene sweep ran and its one-line report is in the handback.
