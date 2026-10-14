# revenantworks-gamedev-soundsmith

Game audio direction with a measured check. It writes the sound palette, the SFX list per game system, music and voice briefs, and the Godot 4 import line for every file; it briefs whatever makes the sound; and it measures what comes back with its own stdlib script, whatever made the file. What separates it from the audio skills around it: **every generator brief passes a model licence gate** (non-commercial weights are refused for a commercial game), **loops are cut to Godot's rules** (Ogg Vorbis and MP3 keep a loop offset but no loop end), and **loudness targets are applied the way the game-audio recommendation says** — the platform figure to the whole mix, consistency to the single file. It never generates or processes audio. The third member of the `gamedev` pack.

**Workflow:** Palette → Rundown → Brief → Measure → Listen → Findings

## Package contents

```
revenantworks-gamedev-soundsmith/
├── SKILL.md                    # five laws, category defaults, four entries, restraint, seams
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md
├── references/
│   ├── palette-and-lists.md    # palette, SFX list per system, rundown line, music and voice briefs
│   ├── model-briefs.md         # licence gate, model families and limits, brief scaffolds (60-day stamp)
│   ├── godot-import.md         # Godot 4 import options, the begin-only trap, loop arithmetic (90-day stamp)
│   ├── loudness.md             # whole-mix targets, single-file rules, the per-file correction
│   ├── measure.md              # audio_post.py commands, checks, thresholds, fix table
│   ├── listen-test.md          # the one-scene listen test
│   ├── install-walkthrough.md  # owner-run steps for Python and the optional ffmpeg
│   └── pack.md                 # gamedev advisory manifest (generated from the registry)
├── scripts/
│   ├── audio_post.py           # run, not read: measure and mix (stdlib only, read-only)
│   └── test_audio_post.py      # 30 tests; every fixture generated in code
└── evals/                      # hand-run suites + native `claude plugin eval` cases
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Install the `gamedev` pack from the marketplace in Claude Code, drop the folder into a skills directory, or upload it in claude.ai settings. Profile `standard`: Python 3 runs the one declared script, standard library only, as the gamedev pack allows; ffmpeg is an optional, declared helper and only decodes non-WAV files. Without a shell, the skill hands back the command and marks the checks NOT-RUN.

## Entry points

| Entry | Say | Delivers |
|---|---|---|
| Direct | "sound design for my game", "SFX list for the combat system" | Palette, per-system SFX list, rundown (one line per file) |
| Brief | `soundsmith brief`, "prompt for the music model", "generate a jump sound" | A licence-gated brief for a model family, handed to the runner or the user |
| Audit | `soundsmith audit`, "check these WAVs", "my loop clicks" | Measured report per file, findings ordered by cheapest fix |
| Test | `soundsmith test`, "listen test" | The one-scene listen procedure and a scored checklist |

## Commands and switches

| Invocation | Effect |
|---|---|
| `soundsmith` | Bare invocation: the four entries in one line and a question |
| `python scripts/audio_post.py measure <files> --category <c> [--loop]` | Per-file checks; three or more files also get the category spread check |
| `python scripts/audio_post.py mix <capture> --platform console\|portable` | A whole-mix capture against the platform target, plus the loudness range (EBU Tech 3342) and the low-end share below 150 Hz as INFO lines |
| "apply all" / "just write it" | Skips the one gate |

## Boundaries

`revenantworks-localops-comfyrunner` renders a brief on a local model. soundsmith decides each file's import line and hands it over in the importer's own key names (`godot-import.md`); `revenantworks-gamedev-godotsmith` writes it into the project (its `intake` entry), with the bus layout and the player code. `revenantworks-localops-whisperrunner` transcribes speech. `revenantworks-scribe-lorescribe` owns names, motifs and pronunciations. Each is named and never required. Engine DSP (time-stretch, pitch-shift) is out of scope: direction, not DSP.

## Staying current

`references/model-briefs.md` (60 days) and `references/godot-import.md` (90 days) carry Last-verified stamps; `SOURCES.md` holds the dated parity register (90 days); `references/loudness.md` is event-driven (re-checked when a published loudness recommendation changes). `skillwright upkeep` reads them from `volatile.json`.

## Evals

`evals/trigger-evals.md` (20 queries, 10 should / 10 should not), `evals/test-cases.md` (13 assertion cases, each with a `Without:` line), and five native `claude plugin eval` cases under `evals/<case>/`. Run records in `evals/RESULTS.md`: the trigger table was re-judged by hand on 2026-10-01; the native and tier runs are pending, so no pass rate is quoted. The script's own tests: `python -m unittest discover -s scripts -p "test_*.py"`.

History in [CHANGELOG.md](CHANGELOG.md).
