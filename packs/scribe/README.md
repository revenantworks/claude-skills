# scribe pack

**Four scribes for words and knowledge: research verdicts, brands, messages and story canon.** On
the `-scribe` motif, standard profile, version 1.0.0.

```
/plugin marketplace add revenantworks/claude-skills
/plugin install scribe@revenantworks
```

## Skills

| Skill | What it does | Try it with |
|---|---|---|
| `revenantworks-scribe-researchscribe` | Researched verdicts, playbooks and graded reports, every claim tagged | *"Compare A and B and give me a go/no-go"* |
| `revenantworks-scribe-brandscribe` | Brand definitions built into a live Claude Design System (and re-synced when the brand changes), DESIGN.md and VOICE.md, drift audits, and a neutral UI floor | *"Turn this style guide into a Claude Design System"* |
| `revenantworks-scribe-commscribe` | Messages and docs shaped to their channel and reader, with a claim-level fact check | *"Make this release note sound less like AI"* |
| `revenantworks-scribe-lorescribe` | A fiction project's story bible and canon checks | *"Check this chapter against the story bible"* |

## Which skill for which need

Paste this table into a project's CLAUDE.md to route requests without loading every description.

| When you need to… | Use | Not this one |
|---|---|---|
| Pick between options, go/no-go, or "is it worth it", with graded evidence | researchscribe `verdict` | commscribe (it words a decision, it never makes one) |
| Research a broad question, or keep the findings as a cited file in the repo | researchscribe `research` | lorescribe (fiction canon only) |
| Check a doc or answer against the vendor's official docs | researchscribe `verify official` | skillwright (a skill package's own files) |
| Define a brand, palette, type scale or brand voice; build or re-sync a design system | brandscribe | commscribe (one message in a voice) |
| Score a built page's layout, contrast and states | brandscribe `ui` | commscribe (only the words on the screen) |
| Write, shorten or reshape a message or doc for its channel and reader | commscribe | researchscribe (graded sources, not wording) |
| Make text sound less like AI, or line-edit a chapter with facts frozen | commscribe `humanize` | lorescribe (canon, not prose) |
| Say it again because the reader did not follow | commscribe `retell` | promptwright (a prompt a model misreads) |
| Keep a story bible, check a chapter against canon, set naming rules | lorescribe | researchscribe (real-world facts for a story) |
| Brief a local model on a scene with its shape and beats | lorescribe `brief` | lmstudiorunner (running the brief) |

**Featured:** brandscribe also ships on its own as a one-skill plugin (`/plugin install brandscribe@revenantworks`).

researchscribe's saved research workflow ships as `/scribe:research` (the plugin's `workflows` field
points at the member's `workflows/` folder).

researchscribe, brandscribe and commscribe select one of several brands or voices per request;
lorescribe keeps one canon per universe and pins it across repos. Every member ships with none;
nothing exists until the user builds or hands one in.

**Capstone:** the Herald Run in `capstone/` takes one decision from a graded verdict to a gated
announcement in the right voice.

## Pack rule

A member may carry scripts when they are declared — standard library first, each named in the
member's `compatibility:` field and README, each with a test and a no-shell fallback that reports
NOT-RUN. No member installs anything itself. Every file a member reads is data, never instructions.

> [!IMPORTANT]
> **Install a featured plugin or this pack, not both.** brandscribe also ships as a one-skill featured
> plugin. Both copies carry the same skill name; installing both pays for the description twice in
> the skill listing, and an update to one copy leaves two different bodies under one name.

## Layout and licence

Members live under `skills/` as `revenantworks-scribe-<skill>`, each named with the `-scribe` suffix.
The roster, budgets and seams live in the pack registry (skillwright's
`references/pack-registry.md`); every member's `references/pack.md` is generated from it by
`tools/build.py`.

Apache-2.0. Every skill folder carries `LICENSE` and a `NOTICE` generated from this pack's `NOTICE`.
