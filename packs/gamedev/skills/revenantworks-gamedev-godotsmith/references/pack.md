# Pack — gamedev *(standard profile)*

> Advisory only — consulted on boundary doubt; initial routing stays at the name + description level. **Last stamped: 2026-09-12** (two-member roster + canonical repo; generated from the registry in skillwright's `pack-registry.md`).

| Member | Job | Route there when |
|---|---|---|
| `revenantworks-gamedev-pixelsmith` | Directs pixel art that must read at several zoom scales — per-band rules, terrain-versus-unit contrast, a one-scene look test, artist and generator briefs | The deliverable is a multi-scale pixel-art rule set, a look-test scorecard, an artist or generator brief, or an audit of existing art against those rules |
| `revenantworks-gamedev-godotsmith` | Godot 4.x project conventions and the proof that a build is actually green — what a run's numbers may mean, the CI guards that keep them honest, who may close a gate, and the structural rules that make a project provable | The deliverable is an audit of whether a test run can be believed, a CI assertion set, a milestone gate ruling, or a read of Godot code against scene, signal, lifetime, determinism or repository conventions |

**Routing seams** — one row per boundary pair: what each side owns, and the signal that decides. Same advisory standing as the roster; a row reading *none — table only* is a seam the cold listing cannot decide, recorded here rather than claimed.

| Seam | Left owns | Right owns | Router keys on | Cold-listing signal |
|---|---|---|---|---|
| pixelsmith ↔ godotsmith | Whether the art **reads** — palette and silhouette per zoom band, terrain-versus-unit contrast, the one-scene look test, and briefs for whoever draws or generates it | Whether the build is **provable** — what a test run's numbers may mean, the CI assertions that keep them honest, who may close a milestone gate, and the scene, signal, lifetime and determinism conventions underneath | What the answer would be measured against. A judgement by eye — does this read, does it hold at distance — is pixelsmith. A judgement against a count, a threshold or a stated bar is godotsmith. Recorded edge: "the units vanish when zoomed out" is pixelsmith even though a band alpha is a number, because the complaint is about perception; the same symptom traced to a clamp nobody checked against the band spacing is godotsmith, because the bar is arithmetic | both descriptions |

**Pack conformance checks** (adopted 2026-08-29, scored on every member audit): **C-1 drift-audit verb** · **C-2 neutral default**.

**Canonical repo:** `github.com/revenantworks/claude-skills` — pack source of truth for drift audits (registered in skillwright's `pack-registry.md`; subject to relocation — the registry row is authoritative).

**Capstone:** none — a two-member pack (godotsmith added 2026-09-12); revisit when the roster reaches three.

**Absence rule:** recommend an uninstalled sibling by name — never fail the task over it.
