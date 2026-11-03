# Sources

Last verified: 2026-10-31

## Guidance

| Area | Source | Checked |
|---|---|---|
| Skill format, 1,536-char listing cap, 500-line body | [Claude Code skills docs](https://code.claude.com/docs/en/skills) | 2026-10-31 |
| Rubric baseline | skillwright `references/rubrics.md`, last verified 2026-09-28 | 2026-10-31 |
| Fee rules | `references/fee-rules.md` sources table | 2026-10-31 |
| Claim rules | `references/claim-rules.md` sources table | 2026-10-31 |
| Connector tool names | Claude connector directory search | 2026-10-31 |
| Rebook first, cancel second; daily check until deadline | [The Solo Creators prompt](https://thesolocreators.com/prompts/rebook-hotel-when-the-price-drops.md) (idea only) | 2026-10-31 |
| Industry view of AI re-shopping and its token cost | [PhocusWire](https://www.phocuswire.com/news/technology/personal-ai-assistants-could-be-re-shopping-landmine-for-hotels) | 2026-10-31 |

## Parity register

Scan date: 2026-10-31. Sources checked: skills.sh, claudskills.com, claudemarketplaces.com, GitHub, the Claude connector directory, the MCP registry listings on claudemarket.ai, and web search for services.

### Incumbents

| Incumbent | Kind | Licence | Checked |
|---|---|---|---|
| [mtnrabi/travel-agent-skills](https://github.com/mtnrabi/travel-agent-skills) | 8 skills, paid RapidAPI data | MIT | 2026-10-31 (README only) |
| [borski/travel-hacking-toolkit](https://github.com/borski/travel-hacking-toolkit) | 42 skills, 6 MCP servers | MIT | 2026-10-31 (README only) |
| [openclaw amadeus-hotels](https://skills.sh/openclaw/skills/amadeus-hotels) | Skill, target-price tracker by cron | not checked | 2026-10-31 (listing) |
| [pricewin-deal-finder](https://claudemarketplaces.com/skills/price-win/pricewin-skills-hub/pricewin-deal-finder) | Skill, OTA price comparison | MIT-0 | 2026-10-31 (listing) |
| [MrSucik/eu261-mcp](https://claudemarket.ai/mcp/MrSucik/eu261-mcp) | MCP, EU261 eligibility | not checked | 2026-10-31 (listing) |
| [Gondola](https://www.gondola.ai/compare/automatic-hotel-rebooking-service), Repriced (Business Wire press release, 2026-04-07) | Services, rebook on drop | n/a | 2026-10-31 |

### Parity table

| Capability | Mark | Note |
|---|---|---|
| Search and price hotels and flights | met | Drives the user's connectors as tools, no API key |
| All-in stay total with taxes, resort fee, city tax, parking | **margin M1** | No incumbent lists a fee breakdown. Case C2 |
| Money-only items from reviews | **margin M2** | No incumbent reads review text for fees. Case C4 |
| Watch a booked reservation | beaten | Rebook-first, threshold, deadline stop, nothing stored. Cases C5, C6 |
| Flight drop rules by fare class | beaten | Any airline; basic economy flagged not watchable. Case C7 |
| Cancel deadline as a calendar event | beaten | Deadline gets its own event, one day early. Case C8 |
| Delay and refund claims | met | EU261, UK261, US DOT with a draft. Case C9 |
| Automatic rebooking | out of scope | Never books or cancels, by design |
| Points and miles | out of scope | Adopt travel-hacking-toolkit |

### Iterate proposals

- Add a per-source note line in `fee-rules.md` each time a source omits a part, so the skill learns which source hides what.
- Re-price watch bookings on every connected source, not only the source booked.
- Report the refundable premium beside the cheapest rate, so the user sees what flexibility costs.
- Flag a total that does not add up from its parts instead of trusting the source.

### Retire condition

Retire when a connected booking source returns itemized all-in totals (taxes, mandatory fees, city tax) and review-derived fee items itself, or when an incumbent skill matches M1 and M2 with an eval-checked case.

## Licence note

No incumbent text or code was copied. Ideas only.
