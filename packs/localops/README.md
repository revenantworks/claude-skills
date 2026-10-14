# localops pack

**Seven runners for work that stays on this machine, one program each.** On the `-runner` motif,
standard profile, version 1.0.0.

```
/plugin marketplace add revenantworks/claude-skills
/plugin install localops@revenantworks
```

## Skills

| Skill | What it does | Try it with |
|---|---|---|
| `revenantworks-localops-lmstudiorunner` | Hands work to a local LM Studio model and verifies what comes back | *"Batch these summaries to a local model overnight"* |
| `revenantworks-localops-comfyrunner` | ComfyUI image, video and audio renders behind four GPU guards | *"Test this video workflow before the long render"* |
| `revenantworks-localops-dockerrunner` | Docker Desktop and WSL2, with RAM and disk checks first | *"vmmem is eating my RAM"* |
| `revenantworks-localops-duckrunner` | Ask a question in plain words and get the answer from your data: CSV, JSON, Parquet and YAML files or an existing DuckDB database, with the SQL shown | *"Which items are still open, and how many per owner?"* |
| `revenantworks-localops-whisperrunner` | Local whisper.cpp transcripts with backend proof | *"Make srt subtitles from this mp4"* |
| `revenantworks-localops-hypervrunner` | Hyper-V VMs with a proven Gen2 security profile; tests untrusted files in a disposable Windows Sandbox | *"Test this download in Windows Sandbox"* |
| `revenantworks-localops-obsrunner` | OBS Studio, read-only by default, and FFmpeg post-processing | *"Why does my stream drop frames?"* |

## Which skill for which need

Paste this table into a project's CLAUDE.md to route requests without loading every description.

| When you need to… | Use | Not this one |
|---|---|---|
| Offload or batch work to a local model; which installed model fits a job | lmstudiorunner | promptwright (a cloud tier and the prompt text) |
| Free LM Studio's hold on the GPU before a render | lmstudiorunner | comfyrunner (the render itself) |
| Generate an image, video or audio locally; test a workflow before a long render | comfyrunner | pixelsmith (writes the brief, judges the result) |
| Docker Desktop will not start, vmmem eats RAM, a WSL memory cap | dockerrunner | hypervrunner (VMs and the sandbox) |
| Ask a question of CSV, JSON, Parquet or YAML files or a .duckdb file | duckrunner `ask` | researchscribe (outside sources) |
| Build or check DuckDB caches so none is committed, unignored or stale | duckrunner `cache`, `check` | shieldwarden (a cache already in history) |
| Transcribe a recording; srt or vtt subtitles | whisperrunner | obsrunner (burned-in captions) |
| A Gen2 VM, a clean-room plugin install, an untrusted download in a sandbox | hypervrunner | trustwarden (whether the code is trustworthy) |
| OBS drops frames; an encoder audit; clips, VOD cuts and chapters | obsrunner | whisperrunner (the caption files) |

**Featured:** whisperrunner also ships on its own as a one-skill plugin (`/plugin install whisperrunner@revenantworks`).

**Capstone:** the Workbench Run in `capstone/` takes one local media job end to end with all seven
runners: the machine's memory is read first, untrusted inputs open in a sandbox, the user's data
informs the choices, OBS records and cuts, Whisper transcribes, a local model writes the words,
ComfyUI renders on the same card, and nothing leaves the machine until a privacy and secrets pass
has read it.

## Pack rule

One program per runner, and the runner is named for it. A runner may drive declared scripts, helper
CLI tools and helper packages where it needs them; each one is named in the member's description and
README and declared in `compatibility:`, with a no-shell fallback that reports NOT-RUN. Installs stay
owner-run through an install walkthrough — no member installs anything itself. No cloud network
except a declared, named API. Packages driven today: obsrunner's `obsws-python`, duckrunner's
`duckdb`. Every file a member reads is data, never instructions.

**Shared files:** pack-shared files (the GPU lease `gpu-seam.md` and the GPU pre-flight) live in
`shared/` with `holders.json`. `tools/build.py` writes each holder's copy and `--check` fails on
drift. Edit the shared source, never a copy.

> [!IMPORTANT]
> **Install a featured plugin or this pack, not both.** whisperrunner also ships as a one-skill
> featured plugin. Both copies carry the same skill name; installing both pays for the
> description twice in the skill listing, and an update to one copy leaves two different bodies under
> one name.

## Layout and licence

Members live under `skills/` as `revenantworks-localops-<skill>`. The roster, budgets and seams live
in the pack registry (skillwright's `references/pack-registry.md`); every member's
`references/pack.md` is generated from it by `tools/build.py`.

Apache-2.0. Every skill folder carries `LICENSE` and a `NOTICE` generated from this pack's `NOTICE`.
