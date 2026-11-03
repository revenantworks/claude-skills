# revenantworks-hearth-faretender

Most travel tools find a low listed price. This one finds the price you will actually pay: it adds the taxes, resort fees, city taxes and parking each site leaves out, reads reviews for charges no site shows, and watches a refundable booking until its free cancellation ends. It never books, cancels or pays.

First member of the `hearth` pack (life and household skills, `-tender` motif).

## Package

```
revenantworks-hearth-faretender/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── SOURCES.md            # sources and the dated parity register
├── LICENSE
├── NOTICE
├── volatile.json
├── references/
│   ├── fee-rules.md      # dated, 60-day refresh
│   ├── claim-rules.md    # dated, 60-day refresh
│   ├── connectors.md     # tool names, Gmail query, never-call list
│   └── pack.md
└── evals/
    ├── trigger-evals.md
    └── test-cases.md
```

## Install

claude.ai: upload the `.skill` file, or the zip of the folder.

Claude Code, user scope. Save the zip to `~/Downloads`, then run this in a terminal:

```
unzip ~/Downloads/revenantworks-hearth-faretender-1.0.0.zip -d ~/.claude/skills/
```

## Connect first

All optional. Each missing one is named in the output.

- Travel (read only): Brek, Tripadvisor, Booking.com, Expedia.
- Gmail, to read confirmations. Google Calendar, to add events.

Do not connect booking-capable travel connectors for this skill. It never calls their booking tools, but read-only connectors keep the risk at zero. Vet any new connector with trustwarden first.

## Commands

| Say | Does |
|---|---|
| `faretender compare` | All-in totals across sources, one table |
| `faretender fees` | Money items from recent reviews |
| `faretender watch` | One price check of each active refundable booking |
| `faretender calendar` | Trip events and cancel deadlines, after your yes |
| `faretender claim` | Refund or compensation check and a claim draft |
| `faretender audit` | Score a past quote, change nothing |
| `faretender refresh` | Re-verify fee and claim rules |

## Daily watch

Add one line to your existing scheduled task: `Run faretender watch. Minimum saving USD 20 or 5%.` The skill finds bookings in Gmail on every run and stores nothing. Cadence, retries and the kill switch are agentwright's to design.

## Staying current

`faretender refresh` past 60 days. The parity register in `SOURCES.md` is re-scanned every 90 days by `skillwright upkeep`.

See CHANGELOG.md.
