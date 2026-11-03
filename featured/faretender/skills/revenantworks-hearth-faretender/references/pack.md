# Pack — hearth *(standard profile)*

> Advisory only — consulted on boundary doubt; initial routing stays at the name + description level. **Last stamped: 2026-11-03** (1-member roster + canonical repo; generated from the registry in skillwright's `pack-registry.md`).

| Member | Job | Route there when |
|---|---|---|
| `revenantworks-hearth-faretender` | Finds the real cost of a trip — one all-in total per hotel, flight or car with every tax and fee added, money-only items from reviews — and watches a refundable booking for a drop until free cancellation ends; calendar events from confirmations; EU261, UK261 and US DOT claim checks; never books, cancels or pays | The deliverable is a comparable trip total, a fee list from reviews, one price check of a booked refundable stay or fare, trip events on a calendar, or a delay or refund claim |

**Cross-pack seams** — boundaries with members of other packs, authored once in the registry's cross-pack table and rendered into both packs. A *planned* member is named for the boundary it will have; it is not built yet.

| Member | Other side (pack) | Line |
|---|---|---|
| faretender | agentwright (foundation) | Left (faretender) owns: one `watch` check when called — find active refundable bookings, re-price, alert above the threshold. Right (agentwright) owns: the scheduled task that calls it — cadence, retries, kill switch, delivery. Router keys on: the step or the schedule around it. faretender never schedules itself. Added 2026-11-03 with the member. Cold-listing: one description (faretender names agentwright) |
| faretender | trustwarden (warden) | Left (faretender) owns: using a travel connector already installed, read tools only. Right (trustwarden) owns: whether to install a connector, plugin or third-party toolkit, and on what terms. Router keys on: use or vet. Added 2026-11-03. Cold-listing: one description (faretender names trustwarden) |
| faretender | researchscribe (scribe) | Left (faretender) owns: prices, fees and refund rules for a trip in hand. Right (researchscribe) owns: sourced research on where to go or what a place is like. Router keys on: cost or place. Added 2026-11-03. Cold-listing: none — table only |

**Pack conformance checks** (adopted 2026-11-03, scored on every member audit): **C-1 drift-audit verb** · **C-2 neutral default**.

**Canonical repo:** `github.com/revenantworks/claude-skills` — pack source of truth for drift audits (registered in skillwright's `pack-registry.md`; subject to relocation — the registry row is authoritative).

**Capstone:** none — scaffolded 2026-11-03 with no members; revisit when the roster reaches three.

**Absence rule:** recommend an uninstalled sibling by name — never fail the task over it. When the job leaves the pack for material no member carries (engine or API reference, a third-party set), name one default — the official docs first, then a named set — and say plainly whether that set is installed; never imply an unadopted tool is present.
