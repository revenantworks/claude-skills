# Trigger evals — revenantworks-localops-comfyrunner

Provenance: authored against SKILL.md at the v1.0.0 build (2026-09-28), by the unit that wrote the description. Judged from **name + description only**, as a cold router would. Not a cold judge — the reader wrote the clauses. **Cold re-judge done 2026-10-01 (unit J1):** 28 rows judged, 0 misroutes; one tie found on the shared GPU (J1 M8, C3). **FX4, 2026-10-01:** the description took J1 edits E6 ("a game-sound brief soundsmith's") and E9 ("before a render while LM Studio holds the GPU" replaces "when ComfyUI and LM Studio share one GPU"), says it "checks the local LLM is off the GPU" rather than "unloads" it, and names the pixel post-process as pixelsmith's. Re-judged by hand from name + description: rows 1-28 do not move (row 10 still fires on the pre-render clause; audio rows 3 and 16 both say local and still fire). Rows #29 and #30 and pair B7 are new; pair B2 was re-keyed because freeing LM Studio's hold is lmstudiorunner's. **Re-anchored to v1.0.0, 2026-10-01:** provenance only, nothing executed here: `gpu-seam.md` names comfyrunner where it said the planned media runner (D5); the description and body are unchanged.

Balance: 16 should-fire · 14 should-not · 7 boundary pairs (14 more queries) — 44 queries in all. Unit: one query = one numbered row, or one side of a boundary pair.

**Re-anchored to the K6b description cut, 2026-10-08 (commit b338715):** every row re-read against the cut text; row wording only, no row added, removed or flipped; a row whose routing words left the description says so in its reason. A reader re-read, not a cold judge: the `tools/blind_queries.py` cold re-judge is still owed.

## Should fire

| # | Request | Why it lands here |
|---|---|---|
| 1 | "generate an image with ComfyUI" | Names the server and the image media |
| 2 | "make a five-second video clip locally with Wan" | Local video generation, the core claim |
| 3 | "generate some background music on my machine" | Local audio or music |
| 4 | "run this ComfyUI workflow" | The run claim |
| 5 | "check this workflow before I leave it rendering overnight" | Check before a long render |
| 6 | "do a quick test render of this video workflow first" | The test claim |
| 7 | "my PC blue-screened in the middle of a video render" | Named symptom: a video render crashed the machine |
| 8 | "ComfyUI ran out of memory on the decode" | Named symptom: out of memory in the VAE decode |
| 9 | "the render sat at VAE Decode for ten minutes" | Named symptom: hung in VAE decode |
| 10 | "LM Studio is loaded — can I still render in ComfyUI?" | Both on one GPU |
| 11 | "run pixelsmith's generator brief on my local SDXL" | Executes a pixelsmith brief on a local model |
| 12 | "comfyrunner audit" | Named entry point |
| 13 | "comfyrunner status" | Named entry point |
| 14 | "is 1024 by 1024 at 121 frames too big for my card?" | The resolution × frames budget, asked plainly |
| 15 | "queue a batch of ten renders tonight" | Queue + unattended render |
| 16 | "make me a sound effect with Stable Audio locally" | Local audio, a model the description does not name |

## Should not fire

| # | Request | Where it belongs | Why not here |
|---|---|---|---|
| 17 | "write the art brief for a grass tile" | pixelsmith | Briefs are ceded by name |
| 18 | "does this sprite read at 1x?" | pixelsmith | Judging the result is ceded |
| 19 | "pick the palette for the desert biome" | pixelsmith | Art direction |
| 20 | "offload this summary to my local model" | lmstudiorunner | Offloading to a local model is lmstudiorunner's claim; this description names LM Studio only as busy or to free |
| 21 | "which of my installed LLMs should do this?" | lmstudiorunner | LLM model fit |
| 22 | "add a kill switch to the nightly render job" | agentwright | A schedule's kill switch; schedules are ceded to agentwright |
| 23 | "how often should the render routine fire?" | agentwright | A schedule's cadence; schedules are ceded to agentwright |
| 24 | "write a prompt for Midjourney" | promptwright or none | A cloud generator's prompt text; nothing local runs |
| 25 | "generate an image" in a session with no local server in play | none (the host's own image tool) | Nothing in the request says local or ComfyUI; a soft edge, see below |
| 26 | "my GPU fan is loud" | none | Hardware health, not a render |
| 27 | "install ComfyUI for me" | none | Installing or launching the server is not claimed; the skill never starts it |
| 28 | "build me a skill that drives ComfyUI" | skillwright | A skill package |
| 29 | "Generate a jump sound for my platformer." | soundsmith | A game sound starts with soundsmith's brief (J1 M7, E6); nothing here says local or ComfyUI |
| 30 | "free the GPU from LM Studio before I render in ComfyUI" | lmstudiorunner | Freeing LM Studio's hold is lmstudiorunner's (J1 M8, E9); this skill only checks the card is clear before its render |

## Boundary pairs

Each pair shares vocabulary and splits on the deciding key.

| # | A (fires) | B (does not) | The key |
|---|---|---|---|
| B1 | "run this pixel-art brief in ComfyUI" | "write a pixel-art brief for ComfyUI" | Running the generator vs writing the brief. The description cedes the brief to pixelsmith by name |
| B2 | "LM Studio is still loaded — check this workflow can render now" | "unload LM Studio so ComfyUI can render" | The ComfyUI pre-render check vs freeing LM Studio's hold, which is lmstudiorunner's (J1 E9) |
| B3 | "the video render crashed my PC" | "Claude Code crashed my PC" | A render named in the symptom |
| B4 | "check this ComfyUI workflow before the long run" | "check this skill before release" | The object: a workflow bound for the GPU vs a skill package (skillwright) |
| B5 | "queue ten renders for tonight" | "schedule the render job every Sunday with retries" | Running the renders vs designing the schedule around them (agentwright) |
| B6 | "is this sprite sheet ready to generate?" asked with a spec block in hand | "is this sprite sheet good?" about a finished sheet | Executing a brief vs judging a result (pixelsmith test) |
| B7 | "render this sound brief locally in ComfyUI" | "what should the jump sound be like?" | Rendering on the local server vs writing the game-sound brief (soundsmith) |

## Known soft edges

- **#25** — "generate an image" with no word for local. The description's
  trigger reads "generate ... locally"; a cold router in a session where
  ComfyUI is the only image path may still pick this skill, and that is not
  wrong. Recorded, not claimed closed.
- **B6** — "ready to generate" and "good" both touch pixelsmith's vocabulary.
  The split is whether a render is about to happen; a cold router could send
  B6-A to pixelsmith, which would then hand the run back here.
- **#24** — a prompt for a cloud generator mentions generation and images;
  only "locally" or "ComfyUI" pulls it here, and neither is present.
